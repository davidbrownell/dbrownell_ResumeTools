"""Unit tests for __main__.py."""

import tempfile
import textwrap

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
def _CaptureDownloads(
    monkeypatch: pytest.MonkeyPatch,
    content: str,
) -> list[str]:
    """Prevent content from being downloaded and capture the urls that would have been requested."""

    urls: list[str] = []

    class FakeResponse:
        def read(self) -> bytes:
            return content.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args) -> bool:
            return False

    def FakeUrlopen(url: str, timeout: int) -> FakeResponse:  # noqa: ARG001
        urls.append(url)
        return FakeResponse()

    monkeypatch.setattr(main_mod, "urlopen", FakeUrlopen)

    return urls


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

    result = runner.invoke(app, [str(content_filename)])

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
def test_WithoutOutputDirectory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A temporary directory is populated when an output directory is not provided."""

    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)

    served: list[tuple[Path, str]] = []

    # The temporary directory is removed once the command completes, so the content that it was
    # populated with is observed while it is served
    monkeypatch.setattr(
        main_mod,
        "ServeImpl",
        lambda dm, directory, host, port, *, launch_browser: served.append(  # noqa: ARG005
            (directory, (directory / "index.html").read_text(encoding="utf-8")),
        ),
    )

    result = runner.invoke(app, [str(content_filename), str(css_filename), "--serve"])

    assert result.exit_code == 0, result.output
    assert len(served) == 1

    output_directory, content = served[0]

    assert "Sam Taylor" in content
    assert output_directory.is_relative_to(Path(tempfile.gettempdir()))
    assert not output_directory.is_dir()

    # Nothing was written alongside the content that was rendered
    assert sorted(tmp_path.iterdir()) == sorted([content_filename, css_filename])


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
def test_Less(tmp_path: Path):
    content_filename = _CreateResumeFile(tmp_path)

    css_filename = tmp_path / "styles.less"
    css_filename.write_text("@color: red;\nbody { color: @color; }\n", encoding="utf-8")

    output_directory = tmp_path / "output"

    result = runner.invoke(app, [str(content_filename), str(css_filename), str(output_directory)])

    assert result.exit_code == 0, result.output

    dest_css_filename = output_directory / "styles.css"

    assert 'href="styles.css"' in (output_directory / "index.html").read_text(encoding="utf-8")

    # The compiled content is written to the output directory itself, so it remains available once
    # the temporary directory used while generating content is removed
    assert not dest_css_filename.is_symlink()
    assert dest_css_filename.read_text(encoding="utf-8") == textwrap.dedent(
        """\
        body {
          color: red;
        }
        """,
    )


# ----------------------------------------------------------------------
def test_LessWithImport(tmp_path: Path):
    """'@import' statements are resolved relative to the less content."""

    content_filename = _CreateResumeFile(tmp_path)

    (tmp_path / "colors.less").write_text("@color: blue;\n", encoding="utf-8")

    css_filename = tmp_path / "styles.less"
    css_filename.write_text('@import "colors.less";\nbody { color: @color; }\n', encoding="utf-8")

    output_directory = tmp_path / "output"

    result = runner.invoke(app, [str(content_filename), str(css_filename), str(output_directory)])

    assert result.exit_code == 0, result.output
    assert (output_directory / "styles.css").read_text(encoding="utf-8") == textwrap.dedent(
        """\
        body {
          color: blue;
        }
        """,
    )


# ----------------------------------------------------------------------
def test_LessReplacesAnExistingLink(tmp_path: Path):
    """A link created when a css stylesheet was generated is replaced rather than written through.

    Without this, the compiled content would overwrite the stylesheet that the link references.
    """

    if not _SymlinksAreSupported(tmp_path):
        pytest.skip("Symbolic links are not supported.")

    content_filename = _CreateResumeFile(tmp_path)
    css_filename = _CreateCssFile(tmp_path)
    output_directory = tmp_path / "output"

    result = runner.invoke(app, [str(content_filename), str(css_filename), str(output_directory)])

    assert result.exit_code == 0, result.output

    dest_css_filename = output_directory / "styles.css"

    assert dest_css_filename.is_symlink()

    # The less content shares its stem with the css content, so the compiled content is written to
    # the name that the link occupies
    less_filename = tmp_path / "styles.less"
    less_filename.write_text("@color: blue;\nbody { color: @color; }\n", encoding="utf-8")

    result = runner.invoke(app, [str(content_filename), str(less_filename), str(output_directory)])

    assert result.exit_code == 0, result.output
    assert css_filename.read_text(encoding="utf-8") == "body { color: red; }\n"
    assert not dest_css_filename.is_symlink()
    assert dest_css_filename.read_text(encoding="utf-8") == textwrap.dedent(
        """\
        body {
          color: blue;
        }
        """,
    )


# ----------------------------------------------------------------------
def test_CssUrl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    content_filename = _CreateResumeFile(tmp_path)
    output_directory = tmp_path / "output"

    urls = _CaptureDownloads(monkeypatch, "body { color: green; }\n")

    result = runner.invoke(
        app,
        [
            str(content_filename),
            "https://example.com/themes/styles.css",
            str(output_directory),
        ],
    )

    assert result.exit_code == 0, result.output
    assert urls == ["https://example.com/themes/styles.css"]

    dest_css_filename = output_directory / "styles.css"

    assert 'href="styles.css"' in (output_directory / "index.html").read_text(encoding="utf-8")

    # The downloaded content is written to the output directory itself, so it remains available once
    # the temporary directory used while generating content is removed
    assert not dest_css_filename.is_symlink()
    assert dest_css_filename.read_text(encoding="utf-8") == "body { color: green; }\n"

    # Nothing was written alongside the content that was rendered
    assert sorted(tmp_path.iterdir()) == sorted([content_filename, output_directory])


# ----------------------------------------------------------------------
def test_LessUrl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    content_filename = _CreateResumeFile(tmp_path)
    output_directory = tmp_path / "output"

    urls = _CaptureDownloads(monkeypatch, "@color: red;\nbody { color: @color; }\n")

    result = runner.invoke(
        app,
        [str(content_filename), "https://example.com/styles.less", str(output_directory)],
    )

    assert result.exit_code == 0, result.output
    assert urls == ["https://example.com/styles.less"]

    assert 'href="styles.css"' in (output_directory / "index.html").read_text(encoding="utf-8")

    # The downloaded less content is compiled to css; only the compiled result is preserved
    assert sorted(output_directory.iterdir()) == sorted(
        [output_directory / "index.html", output_directory / "styles.css"],
    )
    assert (output_directory / "styles.css").read_text(encoding="utf-8") == textwrap.dedent(
        """\
        body {
          color: red;
        }
        """,
    )


# ----------------------------------------------------------------------
def test_UrlWithQuery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The stylesheet is named after the url's path rather than after everything that follows it."""

    content_filename = _CreateResumeFile(tmp_path)
    output_directory = tmp_path / "output"

    urls = _CaptureDownloads(monkeypatch, "body { color: green; }\n")

    result = runner.invoke(
        app,
        [str(content_filename), "https://example.com/styles.css?raw=true", str(output_directory)],
    )

    assert result.exit_code == 0, result.output
    assert urls == ["https://example.com/styles.css?raw=true"]
    assert (output_directory / "styles.css").read_text(encoding="utf-8") == "body { color: green; }\n"


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "url",
    ["https://example.com/styles.txt", "https://example.com/themes/", "https://example.com"],
)
def test_UrlMustReferenceAStylesheet(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, url: str):
    content_filename = _CreateResumeFile(tmp_path)
    output_directory = tmp_path / "output"

    urls = _CaptureDownloads(monkeypatch, "body { color: green; }\n")

    result = runner.invoke(app, [str(content_filename), url, str(output_directory)])

    assert result.exit_code == 2, result.output
    assert f"'{url}' does not reference a css or less stylesheet." in result.output

    # The content is neither downloaded nor generated when the command line is not valid
    assert urls == []
    assert not output_directory.is_dir()


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
