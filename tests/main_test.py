"""Unit tests for __main__.py."""

from pathlib import Path

import pytest

from typer.testing import CliRunner

from dbrownell_ResumeTools.__main__ import app


# ----------------------------------------------------------------------
# Note that these tests do not assert on terminal output;
# `DoneManager.CreateCommandLine` binds `sys.stdout` as a default argument value, so its content
# never reaches the runner's redirected stream. The messages themselves are verified in
# tests/lib/postprocess_markdown_test.py.
# ----------------------------------------------------------------------
SENTINEL = "<PostprocessMarkdown: linebreak>"

runner = CliRunner()


# ----------------------------------------------------------------------
def _CreateInputFile(
    tmp_path: Path,
    content: str = f"Line 1{SENTINEL}\nLine 2\n",
) -> Path:
    filename = tmp_path / "input.md"
    filename.write_text(content, encoding="utf-8")

    return filename


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


# ----------------------------------------------------------------------
def test_InputFileMustExist(tmp_path: Path):
    result = runner.invoke(app, [str(tmp_path / "does_not_exist.md")])

    assert result.exit_code == 2, result.output


# ----------------------------------------------------------------------
def test_InputFileMustNotBeADir(tmp_path: Path):
    result = runner.invoke(app, [str(tmp_path)])

    assert result.exit_code == 2, result.output


# ----------------------------------------------------------------------
# |
# |  Functionality
# |
# ----------------------------------------------------------------------
def test_WithOutputFilename(tmp_path: Path):
    input_filename = _CreateInputFile(tmp_path)
    output_filename = tmp_path / "output" / "output.md"

    result = runner.invoke(app, [str(input_filename), str(output_filename)])

    assert result.exit_code == 0, result.output
    assert output_filename.read_text(encoding="utf-8") == "Line 1  \nLine 2\n"


# ----------------------------------------------------------------------
def test_WithoutOutputFilename(tmp_path: Path):
    input_filename = _CreateInputFile(tmp_path)

    result = runner.invoke(app, [str(input_filename)])

    assert result.exit_code == 0, result.output

    # The input file is not modified and nothing else is created
    assert list(tmp_path.iterdir()) == [input_filename]
    assert input_filename.read_text(encoding="utf-8") == f"Line 1{SENTINEL}\nLine 2\n"


# ----------------------------------------------------------------------
def test_NoChanges(tmp_path: Path):
    input_filename = _CreateInputFile(tmp_path, "No sentinel here.\n")
    output_filename = tmp_path / "output.md"

    result = runner.invoke(app, [str(input_filename), str(output_filename)])

    assert result.exit_code == 0, result.output
    assert not output_filename.exists()


# ----------------------------------------------------------------------
def test_UnrecognizedOperation(tmp_path: Path):
    input_filename = _CreateInputFile(tmp_path, "<PostprocessMarkdown: unknown>")

    result = runner.invoke(app, [str(input_filename)])

    assert result.exit_code != 0
    assert isinstance(result.exception, ValueError)
    assert str(result.exception) == "'unknown' is not a recognized postprocess operation."


# ----------------------------------------------------------------------
@pytest.mark.parametrize("flag", ["--verbose", "--debug"])
def test_Flags(tmp_path: Path, flag: str):
    input_filename = _CreateInputFile(tmp_path)
    output_filename = tmp_path / "output.md"

    result = runner.invoke(app, [str(input_filename), str(output_filename), flag])

    assert result.exit_code == 0, result.output
    assert output_filename.read_text(encoding="utf-8") == "Line 1  \nLine 2\n"


# ----------------------------------------------------------------------
def test_FilenamesAreResolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Relative filenames are resolved against the current working directory."""

    _CreateInputFile(tmp_path)

    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["input.md", "output.md"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "output.md").read_text(encoding="utf-8") == "Line 1  \nLine 2\n"
