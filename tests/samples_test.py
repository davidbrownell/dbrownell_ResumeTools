"""Unit tests that verify the sample files in src/dbrownell_ResumeTools/samples."""

import dataclasses
import io
import re

from pathlib import Path
from typing import Any

import pytest

from lessish import Lessish

from dbrownell_Common.Streams.DoneManager import DoneManager

from dbrownell_ResumeTools.lib import json_resume_schema
from dbrownell_ResumeTools.lib.generate_html import GenerateHtml
from dbrownell_ResumeTools.lib.json_resume_schema import (
    Award,
    Basics,
    Education,
    Interest,
    Language,
    Location,
    Profile,
    Publication,
    Reference,
    ResumeData,
    Skill,
    SkillLevel,
    Volunteer,
    Work,
)


# ----------------------------------------------------------------------
# The samples are located within the package itself rather than within `lib`
SAMPLES_DIR = Path(json_resume_schema.__file__).parent.parent / "samples"

ALL_STYLESHEET_STEMS = ["standard", "sidebar", "timeline", "minimal"]

FULL_SAMPLE_STEMS = ["resume"]
MINIMAL_SAMPLE_STEMS = ["resume_minimal"]

ALL_SAMPLE_STEMS = FULL_SAMPLE_STEMS + MINIMAL_SAMPLE_STEMS
ALL_SAMPLE_SUFFIXES = [".json", ".yaml"]

ALL_DATACLASSES = [
    Award,
    Basics,
    Education,
    Interest,
    Language,
    Location,
    Profile,
    Publication,
    Reference,
    ResumeData,
    Skill,
    Volunteer,
    Work,
]


# ----------------------------------------------------------------------
# |
# |  Helpers
# |
# ----------------------------------------------------------------------
def _AllSampleFilenames() -> list[Path]:
    """Return every resume sample file, sorted by name.

    The samples directory contains content that is not a resume (stylesheets, for example); those
    files are not returned.
    """

    return sorted(item for item in SAMPLES_DIR.iterdir() if item.suffix in ALL_SAMPLE_SUFFIXES)


# ----------------------------------------------------------------------
def _PopulatedFields(value: Any, results: set[tuple[str, str]] | None = None) -> set[tuple[str, str]]:
    """Return the (class name, field name) pairs populated within `value` (recursively).

    A field is considered populated when it is not None and not an empty list.
    """

    if results is None:
        results = set()

    if isinstance(value, list):
        for item in value:
            _PopulatedFields(item, results)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        class_name = type(value).__name__

        for dataclass_field in dataclasses.fields(value):
            field_value = getattr(value, dataclass_field.name)

            if field_value is None or field_value == []:
                continue

            results.add((class_name, dataclass_field.name))
            _PopulatedFields(field_value, results)

    return results


# ----------------------------------------------------------------------
def _AllFields() -> set[tuple[str, str]]:
    """Return every (class name, field name) pair defined by the schema."""

    return {
        (the_class.__name__, dataclass_field.name)
        for the_class in ALL_DATACLASSES
        for dataclass_field in dataclasses.fields(the_class)
    }


# ----------------------------------------------------------------------
def _CompiledStylesheet(stem: str) -> str:
    """Return the css that a bundled less stylesheet compiles to."""

    filename = SAMPLES_DIR / f"{stem}.less"

    return Lessish().compile(
        filename.read_text(encoding="utf-8"),
        filename=str(filename),
        compress=True,
    )


# ----------------------------------------------------------------------
def _StylesheetIdentifiers(content: str) -> set[str]:
    """Return the ids and classes targeted by the stylesheet provided."""

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
# |  Samples Directory
# |
# ----------------------------------------------------------------------
def test_SamplesDirExists():
    assert SAMPLES_DIR.is_dir(), SAMPLES_DIR


# ----------------------------------------------------------------------
def test_SamplesDirContents():
    """The samples directory contains exactly one file per stem/suffix combination."""

    assert [item.name for item in _AllSampleFilenames()] == sorted(
        f"{stem}{suffix}" for stem in ALL_SAMPLE_STEMS for suffix in ALL_SAMPLE_SUFFIXES
    )


# ----------------------------------------------------------------------
# |
# |  Validation
# |
# ----------------------------------------------------------------------
@pytest.mark.parametrize("filename", _AllSampleFilenames(), ids=lambda filename: filename.name)
def test_SampleIsValid(filename: Path):
    """Every sample file can be loaded and validated."""

    assert isinstance(ResumeData.FromFile(filename), ResumeData)


# ----------------------------------------------------------------------
@pytest.mark.parametrize("stem", ALL_SAMPLE_STEMS)
def test_SampleFormatsAreEquivalent(stem: str):
    """The yaml and json variants of a sample describe the same content."""

    resume_data = [ResumeData.FromFile(SAMPLES_DIR / f"{stem}{suffix}") for suffix in ALL_SAMPLE_SUFFIXES]

    assert all(item == resume_data[0] for item in resume_data[1:])


# ----------------------------------------------------------------------
# |
# |  Content
# |
# ----------------------------------------------------------------------
@pytest.mark.parametrize("stem", MINIMAL_SAMPLE_STEMS)
def test_MinimalSampleContent(stem: str):
    """The minimal samples populate nothing beyond the required values."""

    resume_data = ResumeData.FromFile(SAMPLES_DIR / f"{stem}{ALL_SAMPLE_SUFFIXES[0]}")

    assert _PopulatedFields(resume_data) == {("ResumeData", "basics"), ("Basics", "name")}


# ----------------------------------------------------------------------
@pytest.mark.parametrize("stem", FULL_SAMPLE_STEMS)
def test_FullSamplePopulatesEveryField(stem: str):
    """The full samples demonstrate every field defined by the schema."""

    resume_data = ResumeData.FromFile(SAMPLES_DIR / f"{stem}{ALL_SAMPLE_SUFFIXES[0]}")

    assert _AllFields() - _PopulatedFields(resume_data) == set()


# ----------------------------------------------------------------------
@pytest.mark.parametrize("stem", FULL_SAMPLE_STEMS)
def test_FullSampleDemonstratesEverySkillLevel(stem: str):
    """The full samples demonstrate every SkillLevel value."""

    resume_data = ResumeData.FromFile(SAMPLES_DIR / f"{stem}{ALL_SAMPLE_SUFFIXES[0]}")

    assert {skill.level for skill in resume_data.skills} == {*SkillLevel, None}


# ----------------------------------------------------------------------
@pytest.mark.parametrize("stem", FULL_SAMPLE_STEMS)
def test_FullSampleDemonstratesOptionalOmissions(stem: str):
    """The full samples demonstrate that optional values may be omitted."""

    resume_data = ResumeData.FromFile(SAMPLES_DIR / f"{stem}{ALL_SAMPLE_SUFFIXES[0]}")

    assert any(item.endDate is None for item in resume_data.work)
    assert any(item.level is None for item in resume_data.skills)
    assert any(item.keywords == [] for item in resume_data.interests)
    assert any(item.reference is None for item in resume_data.references)


# ----------------------------------------------------------------------
# |
# |  Stylesheet
# |
# ----------------------------------------------------------------------
def test_StandardCssIsCompiledFromStandardLess():
    """The bundled css stylesheet is `standard.less` expressed in another form.

    The less content is the one that is maintained; without this, an edit to it would not reach the
    css content and the two would silently drift apart.
    """

    assert (SAMPLES_DIR / "standard.css").read_text(encoding="utf-8") == _CompiledStylesheet("standard")


# ----------------------------------------------------------------------
@pytest.mark.parametrize("stylesheet_stem", ALL_STYLESHEET_STEMS)
@pytest.mark.parametrize("stem", FULL_SAMPLE_STEMS)
def test_CssTargetsTheGeneratedMarkup(tmp_path: Path, stem: str, stylesheet_stem: str):
    """Nothing that a bundled stylesheet targets is absent from the generated markup.

    The generated markup names what each value is rather than how it is displayed, so this is the
    contract that a stylesheet is written against; without this, a selector may be renamed on one
    side of that contract and silently style nothing.
    """

    output_directory = tmp_path / "output"

    sink = io.StringIO()

    with DoneManager.Create(sink, "Testing...") as dm:
        GenerateHtml(dm, SAMPLES_DIR / f"{stem}{ALL_SAMPLE_SUFFIXES[0]}", output_directory, None)

    stylesheet_identifiers = _StylesheetIdentifiers(_CompiledStylesheet(stylesheet_stem))

    assert stylesheet_identifiers

    markup_identifiers = _MarkupIdentifiers(
        (output_directory / "index.html").read_text(encoding="utf-8"),
    )

    assert stylesheet_identifiers - markup_identifiers == set()
