"""Unit tests for json_resume_schema.py."""

import json
import re
import textwrap

from datetime import date as CalendarDate
from pathlib import Path

import pytest
import yaml

from pydantic import TypeAdapter, ValidationError

from dbrownell_ResumeTools.lib.json_resume_schema import (
    Award,
    Basics,
    Certificate,
    Education,
    Interest,
    Language,
    Location,
    Meta,
    Profile,
    Project,
    Publication,
    Reference,
    ResumeData,
    ResumeDate,
    Skill,
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
            "image": "https://example.com/jane.png",
            "email": "jane@example.com",
            "phone": "555-1234",
            "url": "https://example.com",
            "summary": "Summary of Jane.",
            "location": {
                "address": "123 Main St",
                "postalCode": "30301",
                "city": "Atlanta",
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
                "name": "Acme",
                "location": "Atlanta, GA",
                "description": "A maker of things",
                "position": "Engineer",
                "url": "https://acme.example.com",
                "startDate": "2020-01-02",
                "endDate": "2022-03-04",
                "summary": "Built things.",
                "highlights": ["Highlight 1", "Highlight 2"],
            },
        ],
        "volunteer": [
            {
                "organization": "Helpers",
                "position": "Volunteer",
                "url": "https://helpers.example.com",
                "startDate": "2019-05-06",
                "endDate": "2019-12-31",
                "summary": "Helped out.",
                "highlights": ["Helped a lot"],
            },
        ],
        "education": [
            {
                "institution": "Georgia Tech",
                "url": "https://gatech.example.com",
                "area": "Computer Science",
                "studyType": "Bachelor",
                "startDate": "2015-08-01",
                "endDate": "2019-05-01",
                "score": "4.0",
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
        "certificates": [
            {
                "name": "A Certificate",
                "date": "2023-02",
                "url": "https://example.com/certificate",
                "issuer": "An Issuer",
            },
        ],
        "publications": [
            {
                "name": "A Paper",
                "publisher": "A Publisher",
                "releaseDate": "2021-01-01",
                "url": "https://example.com/paper",
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
        "projects": [
            {
                "name": "A Project",
                "description": "Something that was built.",
                "highlights": ["Highlight 1"],
                "keywords": ["Rust"],
                "startDate": "2021",
                "endDate": "2022-03",
                "url": "https://example.com/project",
                "roles": ["Author"],
                "entity": "Acme",
                "type": "application",
            },
        ],
        "meta": {
            "canonical": "https://example.com/resume.json",
            "version": "v1.0.0",
            "lastModified": "2021-06-15T09:00:00",
        },
    }


# ----------------------------------------------------------------------
def _FullResumeData() -> ResumeData:
    """Return the ResumeData instance that corresponds to `_FullResumeContent`."""

    return ResumeData(
        basics=Basics(
            name="Jane Doe",
            label="Software Engineer",
            image="https://example.com/jane.png",
            email="jane@example.com",
            phone="555-1234",
            url="https://example.com",
            summary="Summary of Jane.",
            location=Location(
                address="123 Main St",
                postalCode="30301",
                city="Atlanta",
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
                name="Acme",
                location="Atlanta, GA",
                description="A maker of things",
                position="Engineer",
                url="https://acme.example.com",
                startDate=ResumeDate(2020, 1, 2),
                endDate=ResumeDate(2022, 3, 4),
                summary="Built things.",
                highlights=["Highlight 1", "Highlight 2"],
            ),
        ],
        volunteer=[
            Volunteer(
                organization="Helpers",
                position="Volunteer",
                url="https://helpers.example.com",
                startDate=ResumeDate(2019, 5, 6),
                endDate=ResumeDate(2019, 12, 31),
                summary="Helped out.",
                highlights=["Helped a lot"],
            ),
        ],
        education=[
            Education(
                institution="Georgia Tech",
                url="https://gatech.example.com",
                area="Computer Science",
                studyType="Bachelor",
                startDate=ResumeDate(2015, 8, 1),
                endDate=ResumeDate(2019, 5, 1),
                score="4.0",
                courses=["CS 101", "CS 102"],
            ),
        ],
        awards=[
            Award(
                title="Best Engineer",
                date=ResumeDate(2021, 6, 15),
                awarder="Acme",
                summary="For being the best.",
            ),
        ],
        certificates=[
            Certificate(
                name="A Certificate",
                date=ResumeDate(2023, 2),
                url="https://example.com/certificate",
                issuer="An Issuer",
            ),
        ],
        publications=[
            Publication(
                name="A Paper",
                publisher="A Publisher",
                releaseDate=ResumeDate(2021, 1, 1),
                url="https://example.com/paper",
                summary="About a thing.",
            ),
        ],
        skills=[
            Skill(name="Python", level="Master", keywords=["pydantic", "pytest"]),
        ],
        languages=[Language(language="English", fluency="Native speaker")],
        interests=[Interest(name="Hiking", keywords=["mountains", "trails"])],
        references=[Reference(name="John Smith", reference="She is great.")],
        projects=[
            Project(
                name="A Project",
                description="Something that was built.",
                highlights=["Highlight 1"],
                keywords=["Rust"],
                startDate=ResumeDate(2021),
                endDate=ResumeDate(2022, 3),
                url="https://example.com/project",
                roles=["Author"],
                entity="Acme",
                type="application",
            ),
        ],
        meta=Meta(
            canonical="https://example.com/resume.json",
            version="v1.0.0",
            lastModified="2021-06-15T09:00:00",
        ),
    )


# ----------------------------------------------------------------------
def _MinimalResumeContent() -> dict:
    return {"basics": {"name": "Jane Doe"}}


# ----------------------------------------------------------------------
# |
# |  ResumeDate
# |
# ----------------------------------------------------------------------
def test_ResumeDateComplete():
    value = ResumeDate(2020, 1, 2)

    assert value.year == 2020
    assert value.month == 1
    assert value.day == 2


# ----------------------------------------------------------------------
def test_ResumeDatePartial():
    assert ResumeDate(2020) == ResumeDate(2020, None, None)
    assert ResumeDate(2020, 6) == ResumeDate(2020, 6, None)


# ----------------------------------------------------------------------
def test_ResumeDateIsFrozen():
    with pytest.raises(AttributeError):
        ResumeDate(2020).year = 2021  # ty: ignore[invalid-assignment]


# ----------------------------------------------------------------------
# |
# |  Location
# |
# ----------------------------------------------------------------------
def test_LocationRequiredOnly():
    location = Location(address="123 Main St", postalCode="30301", city="Atlanta")

    assert location.address == "123 Main St"
    assert location.city == "Atlanta"
    assert location.postalCode == "30301"
    assert location.countryCode is None
    assert location.region is None


# ----------------------------------------------------------------------
def test_LocationAll():
    location = Location(
        address="123 Main St",
        postalCode="30301",
        city="Atlanta",
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
    assert basics.image is None
    assert basics.email is None
    assert basics.phone is None
    assert basics.url is None
    assert basics.summary is None
    assert basics.location is None
    assert basics.profiles == []


# ----------------------------------------------------------------------
def test_BasicsUriValuesAreNotValidated():
    """`Uri` is an alias for `str`; no url validation is performed."""

    basics = Basics(name="Jane Doe", image="not a url", url="also not a url")

    assert basics.image == "not a url"
    assert basics.url == "also not a url"

    validated = TypeAdapter(Basics).validate_python(
        {"name": "Jane Doe", "image": "not a url", "url": "also not a url"},
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
        name="Acme",
        position="Engineer",
        startDate=ResumeDate(2020, 1, 2),
        summary="Built things.",
    )

    assert work.name == "Acme"
    assert work.position == "Engineer"
    assert work.startDate == ResumeDate(2020, 1, 2)
    assert work.location is None
    assert work.description is None
    assert work.url is None
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
        startDate=ResumeDate(2019, 5, 6),
        summary="Helped out.",
    )

    assert volunteer.organization == "Helpers"
    assert volunteer.url is None
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
    assert education.url is None
    assert education.startDate is None
    assert education.endDate is None
    assert education.score is None
    assert education.courses == []


# ----------------------------------------------------------------------
# |
# |  Award
# |
# ----------------------------------------------------------------------
def test_Award():
    award = Award(
        title="Best Engineer",
        date=ResumeDate(2021, 6, 15),
        awarder="Acme",
        summary="For being the best.",
    )

    assert award.title == "Best Engineer"
    assert award.date == ResumeDate(2021, 6, 15)
    assert award.awarder == "Acme"
    assert award.summary == "For being the best."


# ----------------------------------------------------------------------
# |
# |  Certificate
# |
# ----------------------------------------------------------------------
def test_CertificateRequiredOnly():
    certificate = Certificate(name="A Certificate", issuer="An Issuer")

    assert certificate.name == "A Certificate"
    assert certificate.issuer == "An Issuer"
    assert certificate.date is None
    assert certificate.url is None


# ----------------------------------------------------------------------
def test_CertificateAll():
    certificate = Certificate(
        name="A Certificate",
        date=ResumeDate(2023, 2),
        url="https://example.com/certificate",
        issuer="An Issuer",
    )

    assert certificate.date == ResumeDate(2023, 2)
    assert certificate.url == "https://example.com/certificate"


# ----------------------------------------------------------------------
# |
# |  Publication
# |
# ----------------------------------------------------------------------
def test_PublicationRequiredOnly():
    publication = Publication(
        name="A Paper",
        publisher="A Publisher",
        releaseDate=ResumeDate(2021, 1, 1),
        summary="About a thing.",
    )

    assert publication.name == "A Paper"
    assert publication.releaseDate == ResumeDate(2021, 1, 1)
    assert publication.url is None


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
    """A level is free-form text rather than one of a fixed set of values."""

    skill = Skill(name="Python", level="Wizard", keywords=["pytest"])

    assert skill.level == "Wizard"
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
# |  Project
# |
# ----------------------------------------------------------------------
def test_ProjectRequiredOnly():
    project = Project(name="A Project", description="Something that was built.")

    assert project.name == "A Project"
    assert project.description == "Something that was built."
    assert project.highlights == []
    assert project.keywords == []
    assert project.startDate is None
    assert project.endDate is None
    assert project.url is None
    assert project.roles == []
    assert project.entity is None
    assert project.type is None


# ----------------------------------------------------------------------
# |
# |  Meta
# |
# ----------------------------------------------------------------------
def test_MetaRequiredOnly():
    meta = Meta()

    assert meta.canonical is None
    assert meta.version is None
    assert meta.lastModified is None


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
    assert resume_data.certificates == []
    assert resume_data.publications == []
    assert resume_data.skills == []
    assert resume_data.languages == []
    assert resume_data.interests == []
    assert resume_data.references == []
    assert resume_data.projects == []
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
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2020-01-02", ResumeDate(2020, 1, 2)),
        ("2020-01", ResumeDate(2020, 1)),
        ("2020", ResumeDate(2020)),
        (2020, ResumeDate(2020)),
        (CalendarDate(2020, 1, 2), ResumeDate(2020, 1, 2)),
    ],
)
def test_ValidateCoercesDates(value: object, expected: ResumeDate):
    """A date may omit the month and the day that follows it, and may be written as yaml resolves it."""

    resume_data = TypeAdapter(ResumeData).validate_python(
        {
            "basics": {"name": "Jane Doe"},
            "work": [
                {
                    "name": "Acme",
                    "position": "Engineer",
                    "startDate": value,
                    "summary": "s",
                },
            ],
        },
    )

    assert resume_data.work[0].startDate == expected


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
@pytest.mark.parametrize(
    "value",
    [
        "not-a-date",
        "2020-1-2",  # each part is written with the number of digits that it has
        "2020-13-01",  # a month that a calendar does not contain
        "2020-02-30",  # a day that the month does not contain
        "2020-01-02T09:00:00",
        "",
        [],
    ],
)
def test_ValidateInvalidDate(value: object):
    with pytest.raises(ValidationError) as exec_info:
        TypeAdapter(ResumeData).validate_python(
            {
                "basics": {"name": "Jane Doe"},
                "awards": [
                    {
                        "title": "t",
                        "date": value,
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
def test_ValidateMetaValuesAreOptional():
    """Every value within `meta` is optional, and the tooling configuration beside them is ignored."""

    content = _MinimalResumeContent()
    content["meta"] = {"version": "v1.0.0", "tooling_configuration": {"a": "value"}}

    assert TypeAdapter(ResumeData).validate_python(content).meta == Meta(version="v1.0.0")


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
              - name: Acme
                position: Engineer
                startDate: 2020-01-02  # A native YAML date, not a string.
                summary: Built things.
            """,
        ),
        encoding="utf-8",
    )

    resume_data = ResumeData.FromFile(filename)

    assert resume_data.basics.name == "Jane Doe"
    assert resume_data.work[0].startDate == ResumeDate(2020, 1, 2)


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
