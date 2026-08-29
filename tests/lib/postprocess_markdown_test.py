"""Unit tests for lib/postprocess_markdown.py."""

import io
import re
import textwrap

from pathlib import Path

import pytest

from dbrownell_Common.Streams.DoneManager import DoneManager

from dbrownell_ResumeTools.lib.postprocess_markdown import (
    POSTPROCESS_OPERATIONS,
    POSTPROCESS_SENTINEL,
    PostprocessMarkdown,
)


# ----------------------------------------------------------------------
# |
# |  Helpers
# |
# ----------------------------------------------------------------------
def _Sentinel(operation: str) -> str:
    """Return the sentinel decorated with `operation`."""

    return POSTPROCESS_SENTINEL.replace("operation", operation)


# ----------------------------------------------------------------------
def _Invoke(
    input_filename: Path,
    output_filename: Path | None = None,
) -> str:
    """Invoke `PostprocessMarkdown` and return everything written to the stream."""

    sink = io.StringIO()

    with DoneManager.Create(sink, "Testing...") as dm:
        PostprocessMarkdown(dm, input_filename, output_filename)

    return sink.getvalue()


# ----------------------------------------------------------------------
def _Postprocess(
    tmp_path: Path,
    content: str,
) -> str:
    """Write `content`, postprocess it, and return the postprocessed content."""

    input_filename = tmp_path / "input.md"
    input_filename.write_text(content, encoding="utf-8")

    output_filename = tmp_path / "output.md"

    _Invoke(input_filename, output_filename)

    return output_filename.read_text(encoding="utf-8")


# ----------------------------------------------------------------------
# |
# |  Constants
# |
# ----------------------------------------------------------------------
def test_Sentinel():
    assert POSTPROCESS_SENTINEL == "<PostprocessMarkdown: operation>"
    assert "operation" in POSTPROCESS_SENTINEL


# ----------------------------------------------------------------------
def test_Operations():
    assert POSTPROCESS_OPERATIONS == ["linebreak"]


# ----------------------------------------------------------------------
@pytest.mark.parametrize("operation", POSTPROCESS_OPERATIONS)
def test_EveryOperationIsImplemented(tmp_path: Path, operation: str):
    """Every operation advertised by `POSTPROCESS_OPERATIONS` is handled."""

    assert _Postprocess(tmp_path, _Sentinel(operation)) != _Sentinel(operation)


# ----------------------------------------------------------------------
# |
# |  linebreak
# |
# ----------------------------------------------------------------------
def test_Linebreak():
    """`linebreak` becomes the two trailing spaces that markdown treats as a hard line break."""

    assert _Sentinel("linebreak") == "<PostprocessMarkdown: linebreak>"


# ----------------------------------------------------------------------
def test_LinebreakReplacement(tmp_path: Path):
    assert _Postprocess(tmp_path, f"Line 1{_Sentinel('linebreak')}\nLine 2\n") == "Line 1  \nLine 2\n"


# ----------------------------------------------------------------------
@pytest.mark.parametrize("operation", ["linebreak", "Linebreak", "LineBreak", "LINEBREAK"])
def test_LinebreakIsCaseInsensitive(tmp_path: Path, operation: str):
    assert _Postprocess(tmp_path, f"a{_Sentinel(operation)}b") == "a  b"


# ----------------------------------------------------------------------
def test_MultipleSentinels(tmp_path: Path):
    content = textwrap.dedent(
        f"""\
        Line 1{_Sentinel("linebreak")}
        Line 2{_Sentinel("LINEBREAK")}
        Line 3
        """,
    )

    assert _Postprocess(tmp_path, content) == "Line 1  \nLine 2  \nLine 3\n"


# ----------------------------------------------------------------------
def test_AdjacentSentinels(tmp_path: Path):
    """Sentinels that are not separated by whitespace are each replaced."""

    content = f"a{_Sentinel('linebreak')}{_Sentinel('linebreak')}b"

    assert _Postprocess(tmp_path, content) == "a    b"


# ----------------------------------------------------------------------
def test_SurroundingContentIsPreserved(tmp_path: Path):
    content = textwrap.dedent(
        f"""\
        # Heading

        Some **bold** text with a <tag> and a [link](https://example.com).{_Sentinel("linebreak")}
        The next line.

        - A list item
        """,
    )

    assert _Postprocess(tmp_path, content) == content.replace(_Sentinel("linebreak"), "  ")


# ----------------------------------------------------------------------
def test_UnicodeIsPreserved(tmp_path: Path):
    content = f"Ünicode Nāme 日本語{_Sentinel('linebreak')}\n"

    assert _Postprocess(tmp_path, content) == "Ünicode Nāme 日本語  \n"


# ----------------------------------------------------------------------
# |
# |  Content That Is Not A Sentinel
# |
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "content",
    [
        "",
        "No sentinel here.\n",
        "<PostprocessMarkdown:linebreak>",  # No space after the colon
        "<postprocessmarkdown: linebreak>",  # The sentinel itself is case sensitive
        "<PostprocessMarkdown: >",  # No operation
        "<PostprocessMarkdown: linebreak",  # No terminator
        "PostprocessMarkdown: linebreak>",  # No introducer
        "<PostprocessMarkdown: line break>",  # Whitespace within the operation
    ],
    ids=repr,
)
def test_ContentIsNotModified(tmp_path: Path, content: str):
    input_filename = tmp_path / "input.md"
    input_filename.write_text(content, encoding="utf-8")

    output_filename = tmp_path / "output.md"

    output = _Invoke(input_filename, output_filename)

    assert "No changes were detected." in output
    assert "Content was modified." not in output
    assert not output_filename.exists()


# ----------------------------------------------------------------------
# |
# |  Errors
# |
# ----------------------------------------------------------------------
@pytest.mark.parametrize("operation", ["unknown", "Unknown", "line-break", "linebreaks"])
def test_UnrecognizedOperation(tmp_path: Path, operation: str):
    input_filename = tmp_path / "input.md"
    input_filename.write_text(_Sentinel(operation), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=f"^{re.escape(f"'{operation}' is not a recognized postprocess operation.")}$",
    ):
        _Invoke(input_filename, tmp_path / "output.md")


# ----------------------------------------------------------------------
def test_UnrecognizedOperationDoesNotWriteOutput(tmp_path: Path):
    input_filename = tmp_path / "input.md"
    input_filename.write_text(_Sentinel("unknown"), encoding="utf-8")

    output_filename = tmp_path / "output.md"

    with pytest.raises(ValueError, match="is not a recognized postprocess operation"):
        _Invoke(input_filename, output_filename)

    assert not output_filename.exists()


# ----------------------------------------------------------------------
def test_UnrecognizedOperationIsDetectedAfterValidOnes(tmp_path: Path):
    input_filename = tmp_path / "input.md"
    input_filename.write_text(
        f"{_Sentinel('linebreak')}{_Sentinel('unknown')}",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="'unknown' is not a recognized postprocess operation."):
        _Invoke(input_filename, tmp_path / "output.md")


# ----------------------------------------------------------------------
def test_InputFileDoesNotExist(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        _Invoke(tmp_path / "does_not_exist.md", tmp_path / "output.md")


# ----------------------------------------------------------------------
# |
# |  Output
# |
# ----------------------------------------------------------------------
def test_OutputIsOptional(tmp_path: Path):
    """Modifications are reported even when there is nowhere to write them."""

    input_filename = tmp_path / "input.md"
    input_filename.write_text(_Sentinel("linebreak"), encoding="utf-8")

    output = _Invoke(input_filename, None)

    assert "Content was modified." in output
    assert "Writing" not in output

    # The input file is never modified
    assert input_filename.read_text(encoding="utf-8") == _Sentinel("linebreak")
    assert list(tmp_path.iterdir()) == [input_filename]


# ----------------------------------------------------------------------
def test_OutputParentDirsAreCreated(tmp_path: Path):
    input_filename = tmp_path / "input.md"
    input_filename.write_text(_Sentinel("linebreak"), encoding="utf-8")

    output_filename = tmp_path / "does" / "not" / "exist" / "output.md"

    output = _Invoke(input_filename, output_filename)

    assert "Content was modified." in output
    assert str(output_filename) in output
    assert output_filename.read_text(encoding="utf-8") == "  "


# ----------------------------------------------------------------------
def test_OutputOverwritesExistingContent(tmp_path: Path):
    input_filename = tmp_path / "input.md"
    input_filename.write_text(_Sentinel("linebreak"), encoding="utf-8")

    output_filename = tmp_path / "output.md"
    output_filename.write_text("Previous content that is much longer.", encoding="utf-8")

    _Invoke(input_filename, output_filename)

    assert output_filename.read_text(encoding="utf-8") == "  "


# ----------------------------------------------------------------------
def test_OutputMayBeTheInputFile(tmp_path: Path):
    """The content may be postprocessed in place."""

    input_filename = tmp_path / "input.md"
    input_filename.write_text(f"a{_Sentinel('linebreak')}b", encoding="utf-8")

    _Invoke(input_filename, input_filename)

    assert input_filename.read_text(encoding="utf-8") == "a  b"

    # A second invocation is a no-op
    output = _Invoke(input_filename, input_filename)

    assert "No changes were detected." in output
    assert input_filename.read_text(encoding="utf-8") == "a  b"


# ----------------------------------------------------------------------
def test_OutputIsWrittenAsUtf8(tmp_path: Path):
    input_filename = tmp_path / "input.md"
    input_filename.write_text(f"日本語{_Sentinel('linebreak')}", encoding="utf-8")

    output_filename = tmp_path / "output.md"

    _Invoke(input_filename, output_filename)

    assert output_filename.read_bytes() == "日本語  ".encode()
