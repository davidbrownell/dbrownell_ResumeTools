"""Unit tests that verify the sample files in src/dbrownell_ResumeTools/samples."""

import dataclasses

from pathlib import Path
from typing import Any

import pytest

from dbrownell_ResumeTools import json_resume_schema
from dbrownell_ResumeTools.json_resume_schema import (
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
SAMPLES_DIR = Path(json_resume_schema.__file__).parent / "samples"

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
    """Return every sample file, sorted by name."""

    return sorted(SAMPLES_DIR.iterdir())


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
