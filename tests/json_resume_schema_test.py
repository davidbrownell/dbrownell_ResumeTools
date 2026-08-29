"""Unit tests for json_resume_schema.py."""

import json
import re
import textwrap

from datetime import date as Date
from pathlib import Path

import pytest
import yaml

from pydantic import TypeAdapter, ValidationError

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
# |
# |  Test Data
# |
# ----------------------------------------------------------------------
def _FullResumeContent() -> dict:
    """Return a dict that populates every field defined by the schema."""

    return {
        "basics": {
            "name": "Jane Doe",
            "label": "Software Engineer",
            "picture": "https://example.com/jane.png",
            "email": "jane@example.com",
            "phone": "555-1234",
            "website": "https://example.com",
            "summary": "Summary of Jane.",
            "location": {
                "address": "123 Main St",
                "city": "Atlanta",
                "postalCode": "30301",
                "countryCode": "US",
                "region": "GA",
            },
            "profiles": [
                {
                    "network": "GitHub",
                    "username": "janedoe",
                    "url": "https://github.com/janedoe",
                },
                {
                    "network": "LinkedIn",
                    "username": "jane-doe",
                    "url": "https://linkedin.com/in/jane-doe",
                },
            ],
        },
        "work": [
            {
                "company": "Acme",
                "position": "Engineer",
                "website": "https://acme.example.com",
                "startDate": "2020-01-02",
                "endDate": "2022-03-04",
                "summary": "Built things.",
                "highlights": ["Highlight 1", "Highlight 2"],
            },
        ],
        "volunteer": [
            {
                "organization": "Helpers",
                "website": "https://helpers.example.com",
                "position": "Volunteer",
                "startDate": "2019-05-06",
                "endDate": "2019-12-31",
                "summary": "Helped out.",
                "highlights": ["Helped a lot"],
            },
        ],
        "education": [
            {
                "institution": "Georgia Tech",
                "area": "Computer Science",
                "studyType": "Bachelor",
                "startDate": "2015-08-01",
                "endDate": "2019-05-01",
                "gpa": "4.0",
                "courses": ["CS 101", "CS 102"],
            },
        ],
        "awards": [
            {
                "title": "Best Engineer",
                "date": "2021-06-15",
                "awarder": "Acme",
                "summary": "For being the best.",
            },
        ],
        "publications": [
            {
                "name": "A Paper",
                "publisher": "A Publisher",
                "releaseDate": "2021-01-01",
                "website": "https://example.com/paper",
                "summary": "About a thing.",
            },
        ],
        "skills": [
            {
                "name": "Python",
                "level": "Master",
                "keywords": ["pydantic", "pytest"],
            },
        ],
        "languages": [
            {"language": "English", "fluency": "Native speaker"},
        ],
        "interests": [
            {"name": "Hiking", "keywords": ["mountains", "trails"]},
        ],
        "references": [
            {"name": "John Smith", "reference": "She is great."},
        ],
        "meta": {"canonical": "https://example.com/resume.json", "version": "v1.0.0"},
    }


# ----------------------------------------------------------------------
def _FullResumeData() -> ResumeData:
    """Return the ResumeData instance that corresponds to `_FullResumeContent`."""

    return ResumeData(
        basics=Basics(
            name="Jane Doe",
            label="Software Engineer",
            picture="https://example.com/jane.png",
            email="jane@example.com",
            phone="555-1234",
            website="https://example.com",
            summary="Summary of Jane.",
            location=Location(
                address="123 Main St",
                city="Atlanta",
                postalCode="30301",
                countryCode="US",
                region="GA",
            ),
            profiles=[
                Profile(network="GitHub", username="janedoe", url="https://github.com/janedoe"),
                Profile(
                    network="LinkedIn",
                    username="jane-doe",
                    url="https://linkedin.com/in/jane-doe",
                ),
            ],
        ),
        work=[
            Work(
                company="Acme",
                position="Engineer",
                website="https://acme.example.com",
                startDate=Date(2020, 1, 2),
                endDate=Date(2022, 3, 4),
                summary="Built things.",
                highlights=["Highlight 1", "Highlight 2"],
            ),
        ],
        volunteer=[
            Volunteer(
                organization="Helpers",
                website="https://helpers.example.com",
                position="Volunteer",
                startDate=Date(2019, 5, 6),
                endDate=Date(2019, 12, 31),
                summary="Helped out.",
                highlights=["Helped a lot"],
            ),
        ],
        education=[
            Education(
                institution="Georgia Tech",
                area="Computer Science",
                studyType="Bachelor",
                startDate=Date(2015, 8, 1),
                endDate=Date(2019, 5, 1),
                gpa="4.0",
                courses=["CS 101", "CS 102"],
            ),
        ],
        awards=[
            Award(
                title="Best Engineer",
                date=Date(2021, 6, 15),
                awarder="Acme",
                summary="For being the best.",
            ),
        ],
        publications=[
            Publication(
                name="A Paper",
                publisher="A Publisher",
                releaseDate=Date(2021, 1, 1),
                website="https://example.com/paper",
                summary="About a thing.",
            ),
        ],
        skills=[
            Skill(name="Python", level=SkillLevel.Master, keywords=["pydantic", "pytest"]),
        ],
        languages=[Language(language="English", fluency="Native speaker")],
        interests=[Interest(name="Hiking", keywords=["mountains", "trails"])],
        references=[Reference(name="John Smith", reference="She is great.")],
        meta={"canonical": "https://example.com/resume.json", "version": "v1.0.0"},
    )


# ----------------------------------------------------------------------
def _MinimalResumeContent() -> dict:
    return {"basics": {"name": "Jane Doe"}}


# ----------------------------------------------------------------------
# |
# |  SkillLevel
# |
# ----------------------------------------------------------------------
def test_SkillLevelValues():
    assert [item.value for item in SkillLevel] == [
        "Beginner",
        "Intermediate",
        "Advanced",
        "Master",
    ]


# ----------------------------------------------------------------------
def test_SkillLevelIsStr():
    assert isinstance(SkillLevel.Beginner, str)
    assert SkillLevel.Advanced == "Advanced"
    assert SkillLevel("Master") is SkillLevel.Master


# ----------------------------------------------------------------------
# |
# |  Location
# |
# ----------------------------------------------------------------------
def test_LocationRequiredOnly():
    location = Location(address="123 Main St", city="Atlanta", postalCode="30301")

    assert location.address == "123 Main St"
    assert location.city == "Atlanta"
    assert location.postalCode == "30301"
    assert location.countryCode is None
    assert location.region is None


# ----------------------------------------------------------------------
def test_LocationAll():
    location = Location(
        address="123 Main St",
        city="Atlanta",
        postalCode="30301",
        countryCode="US",
        region="GA",
    )

    assert location.countryCode == "US"
    assert location.region == "GA"


# ----------------------------------------------------------------------
def test_LocationIsKeywordOnly():
    with pytest.raises(TypeError):
        Location("123 Main St", "Atlanta", "30301")  # ty: ignore[missing-argument, too-many-positional-arguments]


# ----------------------------------------------------------------------
def test_LocationMissingRequired():
    with pytest.raises(TypeError):
        Location(address="123 Main St", city="Atlanta")  # ty: ignore[missing-argument]


# ----------------------------------------------------------------------
# |
# |  Profile
# |
# ----------------------------------------------------------------------
def test_Profile():
    profile = Profile(network="GitHub", username="janedoe", url="https://github.com/janedoe")

    assert profile.network == "GitHub"
    assert profile.username == "janedoe"
    assert profile.url == "https://github.com/janedoe"


# ----------------------------------------------------------------------
# |
# |  Basics
# |
# ----------------------------------------------------------------------
def test_BasicsRequiredOnly():
    basics = Basics(name="Jane Doe")

    assert basics.name == "Jane Doe"
    assert basics.label is None
    assert basics.picture is None
    assert basics.email is None
    assert basics.phone is None
    assert basics.website is None
    assert basics.summary is None
    assert basics.location is None
    assert basics.profiles == []


# ----------------------------------------------------------------------
def test_BasicsUriValuesAreNotValidated():
    """`Uri` is an alias for `str`; no url validation is performed."""

    basics = Basics(name="Jane Doe", picture="not a url", website="also not a url")

    assert basics.picture == "not a url"
    assert basics.website == "also not a url"

    validated = TypeAdapter(Basics).validate_python(
        {"name": "Jane Doe", "picture": "not a url", "website": "also not a url"},
    )

    assert validated == basics


# ----------------------------------------------------------------------
def test_BasicsProfilesDefaultIsNotShared():
    basics1 = Basics(name="One")
    basics2 = Basics(name="Two")

    basics1.profiles.append(Profile(network="GitHub", username="one", url="https://example.com"))

    assert len(basics1.profiles) == 1
    assert basics2.profiles == []


# ----------------------------------------------------------------------
# |
# |  Work
# |
# ----------------------------------------------------------------------
def test_WorkRequiredOnly():
    work = Work(
        company="Acme",
        position="Engineer",
        startDate=Date(2020, 1, 2),
        summary="Built things.",
    )

    assert work.company == "Acme"
    assert work.position == "Engineer"
    assert work.startDate == Date(2020, 1, 2)
    assert work.website is None
    assert work.endDate is None
    assert work.highlights == []


# ----------------------------------------------------------------------
# |
# |  Volunteer
# |
# ----------------------------------------------------------------------
def test_VolunteerRequiredOnly():
    volunteer = Volunteer(
        organization="Helpers",
        position="Volunteer",
        startDate=Date(2019, 5, 6),
        summary="Helped out.",
    )

    assert volunteer.organization == "Helpers"
    assert volunteer.website is None
    assert volunteer.endDate is None
    assert volunteer.highlights == []


# ----------------------------------------------------------------------
# |
# |  Education
# |
# ----------------------------------------------------------------------
def test_EducationRequiredOnly():
    education = Education(institution="Georgia Tech", area="Computer Science", studyType="Bachelor")

    assert education.institution == "Georgia Tech"
    assert education.area == "Computer Science"
    assert education.studyType == "Bachelor"
    assert education.startDate is None
    assert education.endDate is None
    assert education.gpa is None
    assert education.courses == []


# ----------------------------------------------------------------------
# |
# |  Award
# |
# ----------------------------------------------------------------------
def test_Award():
    award = Award(
        title="Best Engineer",
        date=Date(2021, 6, 15),
        awarder="Acme",
        summary="For being the best.",
    )

    assert award.title == "Best Engineer"
    assert award.date == Date(2021, 6, 15)
    assert award.awarder == "Acme"
    assert award.summary == "For being the best."


# ----------------------------------------------------------------------
# |
# |  Publication
# |
# ----------------------------------------------------------------------
def test_PublicationRequiredOnly():
    publication = Publication(
        name="A Paper",
        publisher="A Publisher",
        releaseDate=Date(2021, 1, 1),
        summary="About a thing.",
    )

    assert publication.name == "A Paper"
    assert publication.releaseDate == Date(2021, 1, 1)
    assert publication.website is None


# ----------------------------------------------------------------------
# |
# |  Skill
# |
# ----------------------------------------------------------------------
def test_SkillRequiredOnly():
    skill = Skill(name="Python")

    assert skill.name == "Python"
    assert skill.level is None
    assert skill.keywords == []


# ----------------------------------------------------------------------
def test_SkillWithLevel():
    skill = Skill(name="Python", level=SkillLevel.Advanced, keywords=["pytest"])

    assert skill.level is SkillLevel.Advanced
    assert skill.keywords == ["pytest"]


# ----------------------------------------------------------------------
# |
# |  Language, Interest, Reference
# |
# ----------------------------------------------------------------------
def test_Language():
    language = Language(language="English", fluency="Native speaker")

    assert language.language == "English"
    assert language.fluency == "Native speaker"


# ----------------------------------------------------------------------
def test_InterestRequiredOnly():
    interest = Interest(name="Hiking")

    assert interest.name == "Hiking"
    assert interest.keywords == []


# ----------------------------------------------------------------------
def test_ReferenceRequiredOnly():
    reference = Reference(name="John Smith")

    assert reference.name == "John Smith"
    assert reference.reference is None


# ----------------------------------------------------------------------
# |
# |  ResumeData
# |
# ----------------------------------------------------------------------
def test_ResumeDataRequiredOnly():
    resume_data = ResumeData(basics=Basics(name="Jane Doe"))

    assert resume_data.basics.name == "Jane Doe"
    assert resume_data.work == []
    assert resume_data.volunteer == []
    assert resume_data.education == []
    assert resume_data.awards == []
    assert resume_data.publications == []
    assert resume_data.skills == []
    assert resume_data.languages == []
    assert resume_data.interests == []
    assert resume_data.references == []
    assert resume_data.meta is None


# ----------------------------------------------------------------------
def test_ResumeDataEquality():
    assert _FullResumeData() == _FullResumeData()
    assert _FullResumeData() != ResumeData(basics=Basics(name="Jane Doe"))


# ----------------------------------------------------------------------
# |
# |  Validation
# |
# ----------------------------------------------------------------------
def test_ValidateFullContent():
    assert TypeAdapter(ResumeData).validate_python(_FullResumeContent()) == _FullResumeData()


# ----------------------------------------------------------------------
def test_ValidateMinimalContent():
    assert TypeAdapter(ResumeData).validate_python(_MinimalResumeContent()) == ResumeData(
        basics=Basics(name="Jane Doe"),
    )


# ----------------------------------------------------------------------
def test_ValidateCoercesDateStrings():
    resume_data = TypeAdapter(ResumeData).validate_python(
        {
            "basics": {"name": "Jane Doe"},
            "work": [
                {
                    "company": "Acme",
                    "position": "Engineer",
                    "startDate": "2020-01-02",
                    "summary": "s",
                },
            ],
        },
    )

    assert resume_data.work[0].startDate == Date(2020, 1, 2)


# ----------------------------------------------------------------------
def test_ValidateCoercesEnumStrings():
    resume_data = TypeAdapter(ResumeData).validate_python(
        {"basics": {"name": "Jane Doe"}, "skills": [{"name": "Python", "level": "Intermediate"}]},
    )

    assert resume_data.skills[0].level is SkillLevel.Intermediate


# ----------------------------------------------------------------------
def test_ValidateMissingBasics():
    with pytest.raises(ValidationError) as exec_info:
        TypeAdapter(ResumeData).validate_python({})

    errors = exec_info.value.errors()

    assert len(errors) == 1
    assert errors[0]["type"] == "missing"
    assert errors[0]["loc"] == ("basics",)


# ----------------------------------------------------------------------
def test_ValidateMissingNestedValue():
    with pytest.raises(ValidationError) as exec_info:
        TypeAdapter(ResumeData).validate_python(
            {"basics": {"name": "Jane Doe"}, "languages": [{"language": "English"}]},
        )

    errors = exec_info.value.errors()

    assert len(errors) == 1
    assert errors[0]["type"] == "missing"
    assert errors[0]["loc"] == ("languages", 0, "fluency")


# ----------------------------------------------------------------------
def test_ValidateInvalidSkillLevel():
    with pytest.raises(ValidationError) as exec_info:
        TypeAdapter(ResumeData).validate_python(
            {"basics": {"name": "Jane Doe"}, "skills": [{"name": "Python", "level": "Wizard"}]},
        )

    errors = exec_info.value.errors()

    assert len(errors) == 1
    assert errors[0]["type"] == "enum"
    assert errors[0]["loc"] == ("skills", 0, "level")


# ----------------------------------------------------------------------
def test_ValidateInvalidDate():
    with pytest.raises(ValidationError) as exec_info:
        TypeAdapter(ResumeData).validate_python(
            {
                "basics": {"name": "Jane Doe"},
                "awards": [
                    {
                        "title": "t",
                        "date": "not-a-date",
                        "awarder": "a",
                        "summary": "s",
                    },
                ],
            },
        )

    errors = exec_info.value.errors()

    assert len(errors) == 1
    assert errors[0]["loc"] == ("awards", 0, "date")


# ----------------------------------------------------------------------
def test_ValidateIgnoresExtraValues():
    """Extra values are silently discarded rather than rejected."""

    content = _MinimalResumeContent()
    content["basics"]["not_part_of_the_schema"] = "value"  # type: ignore[index]
    content["also_not_part_of_the_schema"] = "value"

    resume_data = TypeAdapter(ResumeData).validate_python(content)

    assert resume_data == ResumeData(basics=Basics(name="Jane Doe"))
    assert not hasattr(resume_data, "also_not_part_of_the_schema")


# ----------------------------------------------------------------------
def test_ValidateMetaAcceptsArbitraryContent():
    ta = TypeAdapter(ResumeData)

    for meta in [None, "a string", 123, ["a", "list"], {"a": {"nested": "dict"}}]:
        content = _MinimalResumeContent()
        content["meta"] = meta

        assert ta.validate_python(content).meta == meta


# ----------------------------------------------------------------------
# |
# |  ResumeData.FromFile
# |
# ----------------------------------------------------------------------
@pytest.mark.parametrize("suffix", [".json", ".JSON", ".Json"])
def test_FromFileJson(tmp_path: Path, suffix: str):
    filename = tmp_path / f"resume{suffix}"
    filename.write_text(json.dumps(_FullResumeContent()), encoding="utf-8")

    assert ResumeData.FromFile(filename) == _FullResumeData()


# ----------------------------------------------------------------------
@pytest.mark.parametrize("suffix", [".yaml", ".yml", ".YAML", ".YML", ".Yaml"])
def test_FromFileYaml(tmp_path: Path, suffix: str):
    filename = tmp_path / f"resume{suffix}"
    filename.write_text(yaml.safe_dump(_FullResumeContent()), encoding="utf-8")

    assert ResumeData.FromFile(filename) == _FullResumeData()


# ----------------------------------------------------------------------
def test_FromFileYamlWithCommentsAndNativeDates(tmp_path: Path):
    """YAML-specific conveniences (comments, native dates) survive the round trip."""

    filename = tmp_path / "resume.yaml"

    filename.write_text(
        textwrap.dedent(
            """\
            # This is a comment.
            basics:
              name: Jane Doe  # This is another comment.

            work:
              - company: Acme
                position: Engineer
                startDate: 2020-01-02  # A native YAML date, not a string.
                summary: Built things.
            """,
        ),
        encoding="utf-8",
    )

    resume_data = ResumeData.FromFile(filename)

    assert resume_data.basics.name == "Jane Doe"
    assert resume_data.work[0].startDate == Date(2020, 1, 2)


# ----------------------------------------------------------------------
def test_FromFileUnicode(tmp_path: Path):
    filename = tmp_path / "resume.json"

    content = _MinimalResumeContent()
    content["basics"]["name"] = "Ünicode Nāme 日本語"  # type: ignore[index]

    filename.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")

    assert ResumeData.FromFile(filename).basics.name == "Ünicode Nāme 日本語"


# ----------------------------------------------------------------------
@pytest.mark.parametrize("filename_template", ["resume.txt", "resume.xml", "resume", "resume.yamlx"])
def test_FromFileUnsupportedSuffix(tmp_path: Path, filename_template: str):
    filename = tmp_path / filename_template
    filename.write_text(json.dumps(_MinimalResumeContent()), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=f"^{re.escape(f"'{filename}' is not a supported file type.")}$",
    ):
        ResumeData.FromFile(filename)


# ----------------------------------------------------------------------
def test_FromFileDoesNotExist(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        ResumeData.FromFile(tmp_path / "does_not_exist.yaml")


# ----------------------------------------------------------------------
def test_FromFileInvalidContent(tmp_path: Path):
    filename = tmp_path / "resume.yaml"
    filename.write_text(yaml.safe_dump({"work": []}), encoding="utf-8")

    with pytest.raises(ValidationError) as exec_info:
        ResumeData.FromFile(filename)

    assert exec_info.value.errors()[0]["loc"] == ("basics",)


# ----------------------------------------------------------------------
def test_FromFileMalformedJson(tmp_path: Path):
    filename = tmp_path / "resume.json"
    filename.write_text("{ this is not json }", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        ResumeData.FromFile(filename)


# ----------------------------------------------------------------------
def test_FromFileMalformedYaml(tmp_path: Path):
    filename = tmp_path / "resume.yaml"
    filename.write_text("basics:\n  name: [unterminated\n", encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        ResumeData.FromFile(filename)


# ----------------------------------------------------------------------
def test_FromFileYamlIsLoadedSafely(tmp_path: Path):
    """Arbitrary python tags are rejected rather than constructed."""

    filename = tmp_path / "resume.yaml"
    filename.write_text(
        "basics:\n  name: !!python/object/apply:os.system ['echo unsafe']\n",
        encoding="utf-8",
    )

    with pytest.raises(yaml.constructor.ConstructorError):  # ty: ignore[possibly-missing-submodule]
        ResumeData.FromFile(filename)


# ----------------------------------------------------------------------
def test_FromFileEmptyYaml(tmp_path: Path):
    """An empty yaml document loads as None and fails validation."""

    filename = tmp_path / "resume.yaml"
    filename.write_text("", encoding="utf-8")

    with pytest.raises(ValidationError) as exec_info:
        ResumeData.FromFile(filename)

    errors = exec_info.value.errors()

    assert len(errors) == 1
    assert errors[0]["type"] == "dataclass_type"
