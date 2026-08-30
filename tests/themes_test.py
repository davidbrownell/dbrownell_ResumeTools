"""Unit tests that verify the theme files in src/dbrownell_ResumeTools/themes."""

import io
import re

from pathlib import Path

import pytest

from lessish import Lessish

from dbrownell_Common.Streams.DoneManager import DoneManager

from dbrownell_ResumeTools.lib import json_resume_schema
from dbrownell_ResumeTools.lib.generate_html import GenerateHtml


# ----------------------------------------------------------------------
# The themes are located within the package itself rather than within `lib`
_PACKAGE_DIR = Path(json_resume_schema.__file__).parent.parent

THEMES_DIR = _PACKAGE_DIR / "themes"
SAMPLES_DIR = _PACKAGE_DIR / "samples"

ALL_THEME_STEMS = ["standard", "sidebar", "timeline", "minimal", "modernist", "brutalist"]

SAMPLE_FILENAME = SAMPLES_DIR / "resume.json"


# ----------------------------------------------------------------------
# |
# |  Helpers
# |
# ----------------------------------------------------------------------
def _CompiledTheme(stem: str) -> str:
    """Return the css that a bundled less theme compiles to."""

    filename = THEMES_DIR / f"{stem}.less"

    return Lessish().compile(
        filename.read_text(encoding="utf-8"),
        filename=str(filename),
        compress=True,
    )


# ----------------------------------------------------------------------
def _ThemeIdentifiers(content: str) -> set[str]:
    """Return the ids and classes targeted by the theme provided."""

    content = re.sub(r"/\*.*?\*/", " ", content, flags=re.DOTALL)

    # An at-rule that is a statement rather than a block ('@import', for example) is not a selector,
    # yet the uri that it references resembles one.
    content = re.sub(r"@[\w-]+[^;{}]*;", " ", content)

    # Declaration blocks are the only blocks that do not themselves contain a block, so removing them
    # leaves the selectors (including those within an at-rule) and nothing that resembles one.
    content = re.sub(r"\{[^{}]*\}", " ", content)

    return set(re.findall(r"[#.](-?[A-Za-z_][\w-]*)", content))


# ----------------------------------------------------------------------
def _MarkupIdentifiers(content: str) -> set[str]:
    """Return the ids and classes assigned within the html provided."""

    return {
        identifier
        for match in re.finditer(r'\b(?:id|class)="([^"]*)"', content)
        for identifier in match.group(1).split()
    }


# ----------------------------------------------------------------------
# |
# |  Themes Directory
# |
# ----------------------------------------------------------------------
def test_ThemesDirExists():
    assert THEMES_DIR.is_dir(), THEMES_DIR


# ----------------------------------------------------------------------
def test_ThemesDirContents():
    """The themes directory contains one less theme per stem and nothing else beyond the bundled css."""

    assert sorted(item.name for item in THEMES_DIR.iterdir()) == sorted(
        [*(f"{stem}.less" for stem in ALL_THEME_STEMS), "standard.css"],
    )


# ----------------------------------------------------------------------
# |
# |  Themes
# |
# ----------------------------------------------------------------------
def test_StandardCssIsCompiledFromStandardLess():
    """The bundled css theme is `standard.less` expressed in another form.

    The less content is the one that is maintained; without this, an edit to it would not reach the
    css content and the two would silently drift apart.
    """

    assert (THEMES_DIR / "standard.css").read_text(encoding="utf-8") == _CompiledTheme("standard")


# ----------------------------------------------------------------------
@pytest.mark.parametrize("theme_stem", ALL_THEME_STEMS)
def test_CssTargetsTheGeneratedMarkup(tmp_path: Path, theme_stem: str):
    """Nothing that a bundled theme targets is absent from the generated markup.

    The generated markup names what each value is rather than how it is displayed, so this is the
    contract that a theme is written against; without this, a selector may be renamed on one side of
    that contract and silently style nothing.
    """

    output_directory = tmp_path / "output"

    sink = io.StringIO()

    with DoneManager.Create(sink, "Testing...") as dm:
        GenerateHtml(dm, SAMPLE_FILENAME, output_directory, None)

    theme_identifiers = _ThemeIdentifiers(_CompiledTheme(theme_stem))

    assert theme_identifiers

    markup_identifiers = _MarkupIdentifiers(
        (output_directory / "index.html").read_text(encoding="utf-8"),
    )

    assert theme_identifiers - markup_identifiers == set()
