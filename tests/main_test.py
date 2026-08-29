"""Unit tests for __main__.py."""

from pathlib import Path

import pytest

from typer.testing import CliRunner

from dbrownell_ResumeTools import __main__ as main_mod
from dbrownell_ResumeTools.__main__ import app
from dbrownell_ResumeTools.lib.serve import DEFAULT_HOST, DEFAULT_PORT


# ----------------------------------------------------------------------
# Note that these tests do not assert on terminal output;
# `DoneManager.CreateCommandLine` binds `sys.stdout` as a default argument value, so its content
# never reaches the runner's redirected stream. The messages themselves are verified in
# tests/lib/postprocess_markdown_test.py.
#
# `GenerateHtml` is the only command implemented by the app, so its name is not provided on the
# command line.
# ----------------------------------------------------------------------
SENTINEL = "<PostprocessMarkdown: linebreak>"

runner = CliRunner()


# ----------------------------------------------------------------------
def _CreateResumeFile(
    tmp_path: Path,
    content: str = f"basics:\n  name: Sam Taylor\n  summary: |\n    Line 1{SENTINEL}\n    Line 2\n",
) -> Path:
    filename = tmp_path / "resume.yaml"
    filename.write_text(content, encoding="utf-8")

    return filename


# ----------------------------------------------------------------------
def _CreateCssFile(tmp_path: Path, content: str = "body { color: red; }\n") -> Path:
    filename = tmp_path / "styles.css"
    filename.write_text(content, encoding="utf-8")

    return filename


# ----------------------------------------------------------------------
def _SymlinksAreSupported(tmp_path: Path) -> bool:
    """Return True when symbolic links can be created; Windows requires developer mode."""

    link = tmp_path / "symlink_probe"

    try:
        link.symlink_to(tmp_path)
    except OSError:
        return False

    link.unlink()
    return True


# ----------------------------------------------------------------------
def _CaptureServe(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, str, int, bool]]:
    """Prevent content from being served and capture the arguments used when it would have been."""

    arguments: list[tuple[Path, str, int, bool]] = []

    monkeypatch.setattr(
        main_mod,
        "ServeImpl",
        lambda dm, directory, host, port, *, launch_browser: arguments.append(  # noqa: ARG005
            (directory, host, port, launch_browser),
        ),
    )

    return arguments


# ----------------------------------------------------------------------
# |
# |  Command Line
# |
# ----------------------------------------------------------------------
def test_NoArgsIsHelp():
    result = runner.invoke(app, [])

    assert result.exit_code == 2, result.output
    assert "Usage:" in result.output


# ----------------------------------------------------------------------
def test_Help():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output
    assert "--serve" in result.output


# ----------------------------------------------------------------------
def test_ContentFileMustExist(tmp_path: Path):
    css_filename = _CreateCssFile(tmp_path)

    result = runner.invoke(
        app,
        [str(tmp_path / "does_not_exist.yaml"), str(css_filename), str(tmp_path / "output")],
    )

    assert result.exit_code == 2, result.output


# ----------------------------------------------------------------------
def test_ContentFileMustNotBeADir(tmp_path: Path):
    css_filename = _CreateCssFile(tmp_path)

    result = runner.invoke(app, [str(tmp_path), str(css_filename), str(tmp_path / "output")])

    assert result.exit_code == 2, result.output


# ----------------------------------------------------------------------
def test_CssFileMustExist(tmp_path: Path):
    content_filename = _CreateResumeFile(tmp_path)

    result = runner.invoke(
        app,
        [str(content_filename), str(tmp_path / "does_not_exist.css"), str(tmp_path / "output")],
    )

    assert result.exit_code == 2, result.output


# ----------------------------------------------------------------------
def test_CssFileIsRequired(tmp_path: Path):
    content_filename = _CreateResumeFile(tmp_path)

    result = runner.invoke(app, [str(content_filename), str(tmp_path / "output")])

    assert result.exit_code == 2, result.output


# ----------------------------------------------------------------------
# |
# |  Functionality
# |
# ----------------------------------------------------------------------
def test_Standard(tmp_path: Path):
    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    result = runner.invoke(app, [str(content_filename), str(css_filename), str(output_directory)])

    assert result.exit_code == 0, result.output

    content = (output_directory / "index.html").read_text(encoding="utf-8")

    assert "Sam Taylor" in content
    assert 'href="styles.css"' in content

    # The postprocessed content was rendered and the temporary file used to hold it was removed
    assert SENTINEL not in content
    assert "Line 1<br>" in content
    # `iterdir` yields entries in filesystem order, which is not alphabetical on every filesystem
    assert sorted(tmp_path.iterdir()) == sorted([content_filename, css_filename, output_directory])


# ----------------------------------------------------------------------
def test_WithoutPostprocessedChanges(tmp_path: Path):
    """The original content is used when postprocessing does not modify it."""

    content_filename = _CreateResumeFile(tmp_path, "basics:\n  name: Sam Taylor\n")
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    result = runner.invoke(app, [str(content_filename), str(css_filename), str(output_directory)])

    assert result.exit_code == 0, result.output
    assert "Sam Taylor" in (output_directory / "index.html").read_text(encoding="utf-8")


# ----------------------------------------------------------------------
def test_Css(tmp_path: Path):
    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    result = runner.invoke(app, [str(content_filename), str(css_filename), str(output_directory)])

    assert result.exit_code == 0, result.output

    dest_css_filename = output_directory / "styles.css"

    assert dest_css_filename.read_text(encoding="utf-8") == "body { color: red; }\n"

    if _SymlinksAreSupported(tmp_path):
        assert dest_css_filename.is_symlink()
        # Windows returns the link target decorated with an extended-length path prefix
        assert dest_css_filename.resolve() == css_filename.resolve()


# ----------------------------------------------------------------------
def test_UnrecognizedOperation(tmp_path: Path):
    content_filename = _CreateResumeFile(
        tmp_path,
        "basics:\n  name: Sam Taylor\n  summary: <PostprocessMarkdown: unknown>\n",
    )

    result = runner.invoke(
        app,
        [str(content_filename), str(_CreateCssFile(tmp_path)), str(tmp_path / "output")],
    )

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == "'unknown' is not a recognized postprocess operation."


# ----------------------------------------------------------------------
@pytest.mark.parametrize("flag", ["--verbose", "--debug"])
def test_Flags(tmp_path: Path, flag: str):
    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    result = runner.invoke(app, [str(content_filename), str(css_filename), str(output_directory), flag])

    assert result.exit_code == 0, result.output
    assert (output_directory / "index.html").is_file()


# ----------------------------------------------------------------------
def test_FilenamesAreResolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Relative filenames are resolved against the current working directory."""

    _CreateResumeFile(tmp_path)
    _CreateCssFile(tmp_path)

    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["resume.yaml", "styles.css", "output"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "output" / "index.html").is_file()


# ----------------------------------------------------------------------
# |
# |  Serving
# |
# ----------------------------------------------------------------------
def test_Serve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    arguments = _CaptureServe(monkeypatch)

    result = runner.invoke(
        app,
        [
            str(content_filename),
            str(css_filename),
            str(output_directory),
            "--serve",
            "--host",
            "example.com",
            "--port",
            "8080",
        ],
    )

    assert result.exit_code == 0, result.output

    # The content was generated before it was served
    assert (output_directory / "index.html").is_file()
    assert arguments == [(output_directory, "example.com", 8080, False)]


# ----------------------------------------------------------------------
def test_ServeDefaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    arguments = _CaptureServe(monkeypatch)

    result = runner.invoke(
        app,
        [str(content_filename), str(css_filename), str(output_directory), "--serve"],
    )

    assert result.exit_code == 0, result.output
    assert arguments == [(output_directory, DEFAULT_HOST, DEFAULT_PORT, False)]


# ----------------------------------------------------------------------
def test_WithoutServe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Content is not served when the flag is not specified."""

    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    arguments = _CaptureServe(monkeypatch)

    result = runner.invoke(app, [str(content_filename), str(css_filename), str(output_directory)])

    assert result.exit_code == 0, result.output
    assert arguments == []


# ----------------------------------------------------------------------
def test_Browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Any available port is used when a browser is launched without an explicit port."""

    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    arguments = _CaptureServe(monkeypatch)

    result = runner.invoke(
        app,
        [str(content_filename), str(css_filename), str(output_directory), "--serve", "--browser"],
    )

    assert result.exit_code == 0, result.output
    assert arguments == [(output_directory, DEFAULT_HOST, 0, True)]


# ----------------------------------------------------------------------
def test_BrowserWithPort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The port that was explicitly provided is used when a browser is launched."""

    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    arguments = _CaptureServe(monkeypatch)

    result = runner.invoke(
        app,
        [
            str(content_filename),
            str(css_filename),
            str(output_directory),
            "--serve",
            "--browser",
            "--port",
            "8080",
        ],
    )

    assert result.exit_code == 0, result.output
    assert arguments == [(output_directory, DEFAULT_HOST, 8080, True)]


# ----------------------------------------------------------------------
def test_BrowserWithoutServe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    arguments = _CaptureServe(monkeypatch)

    result = runner.invoke(
        app,
        [str(content_filename), str(css_filename), str(output_directory), "--browser"],
    )

    assert result.exit_code == 2, result.output
    assert "'--browser' may only be specified when '--serve' is specified." in result.output

    # The content is not generated when the command line is not valid
    assert not output_directory.is_dir()
    assert arguments == []


# ----------------------------------------------------------------------
@pytest.mark.parametrize("port", ["-1", "65536"])
def test_PortMustBeWithinTheTcpRange(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, port: str):
    """A port that no server can bind is rejected rather than generating content that is not served."""

    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    arguments = _CaptureServe(monkeypatch)

    result = runner.invoke(
        app,
        [str(content_filename), str(css_filename), str(output_directory), "--serve", "--port", port],
    )

    assert result.exit_code == 2, result.output
    assert not output_directory.is_dir()
    assert arguments == []
