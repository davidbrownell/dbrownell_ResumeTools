# noqa: D100
import html
import re
import shutil
import textwrap

from typing import TYPE_CHECKING, Self
from urllib.parse import quote

from markdown_it import MarkdownIt

from dbrownell_ResumeTools.lib.json_resume_schema import ResumeData

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from datetime import date as Date  # noqa: N812
    from pathlib import Path

    from dbrownell_Common.Streams.DoneManager import DoneManager

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
        Skill,
        Volunteer,
        Work,
    )


# ----------------------------------------------------------------------
def GenerateHtml(
    dm: DoneManager,
    filename: Path,
    output_directory: Path,
    css_filename: Path | None,
) -> None:
    """Generate HTML content from JSON resume content.

    The html is written to `index.html` within `output_directory`. `css_filename` (when provided) is
    symlinked to `<css filename>` within that same directory and referenced by the generated html;
    no stylesheet is referenced when `css_filename` is not provided.

    The generated markup names what each value is rather than how it is displayed, so every
    presentation decision -- layout, icons, fonts, and the resources that provide them -- belongs to
    the stylesheet. `themes/standard.less` documents the classes that a stylesheet may target.
    """

    if css_filename is not None and css_filename.name == _OUTPUT_FILENAME:
        msg = f"A stylesheet named '{_OUTPUT_FILENAME}' would replace the generated html."
        raise ValueError(msg)

    with dm.Nested(f"Reading '{filename}'..."):
        data = ResumeData.FromFile(filename)

    with dm.Nested("Generating content...") as content_dm:
        if css_filename is None:
            stylesheet_link = ""
        else:
            # The name is url-encoded so that characters that are significant within a uri ('#' and
            # '?', for example) reference the file rather than a fragment or query.
            href = html.escape(quote(css_filename.name), quote=True)
            stylesheet_link = f'\n\n  <link rel="stylesheet" href="{href}" />'

        fragment, rejected_uris = _CreateContent(data)

        for uri in rejected_uris:
            content_dm.WriteWarning(
                f"The uri '{uri}' is not safe to display and was not included in the generated content.\n",
            )

        content = _HTML_TEMPLATE.format(
            title=html.escape(data.basics.name, quote=False),
            stylesheet_link=stylesheet_link,
            content=textwrap.indent(fragment, "  "),
        )

    output_filename = output_directory / _OUTPUT_FILENAME

    with dm.Nested(f"Writing '{output_filename}'..."):
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        output_filename.write_text(content, encoding="utf-8")

    if css_filename is not None:
        # The paths are resolved so that a stylesheet that already lives within `output_directory` is
        # recognized as such no matter how the paths were expressed, and so that the link that is
        # created is not interpreted relative to the directory that contains it.
        css_filename = css_filename.resolve()
        dest_css_filename = output_directory.resolve() / css_filename.name

        with dm.Nested(f"Linking '{dest_css_filename}'...") as link_dm:
            if dest_css_filename != css_filename:
                # An existing link or file is replaced; `is_symlink` is checked as well, as `exists`
                # returns False for a link that references content that is no longer available.
                if dest_css_filename.is_symlink() or dest_css_filename.exists():
                    dest_css_filename.unlink()

                try:
                    dest_css_filename.symlink_to(css_filename)
                except OSError as ex:
                    # Creating a symbolic link on Windows requires developer mode or elevated
                    # privileges; the content is copied when a link cannot be created.
                    link_dm.WriteWarning(
                        f"The symbolic link could not be created ({ex}); the file was copied instead.\n",
                        update_result=False,
                    )

                    shutil.copyfile(css_filename, dest_css_filename)


# ----------------------------------------------------------------------
def _CreateContent(data: ResumeData) -> tuple[str, list[str]]:
    """Create the html fragment that displays the resume data provided and the uris it rejected."""

    rejected_uris: list[str] = []

    content = _Element("div", attributes={"id": "resume"})

    content.Append(_CreateBasicsSection(data.basics, rejected_uris))
    content.Append(_CreateContactSection(data.basics, rejected_uris))

    if data.basics.profiles:
        content.Append(_CreateProfilesSection(data.basics.profiles, rejected_uris))

    if data.basics.summary:
        content.Append(_CreateAboutSection(data.basics.summary))

    if data.skills:
        content.Append(_CreateKeywordSection(data.skills, name="skills", heading="Skills"))

    if data.work:
        content.Append(
            _CreateExperienceSection(
                data.work,
                rejected_uris,
                name_attribute="company",
                name="work",
                heading="Work Experience",
            ),
        )

    if data.education:
        content.Append(_CreateEducationSection(data.education))

    if data.volunteer:
        content.Append(
            _CreateExperienceSection(
                data.volunteer,
                rejected_uris,
                name_attribute="organization",
                name="volunteer",
                heading="Volunteer Experience",
            ),
        )

    if data.awards:
        content.Append(_CreateAwardsSection(data.awards))

    if data.publications:
        content.Append(_CreatePublicationsSection(data.publications, rejected_uris))

    if data.languages:
        content.Append(_CreateLanguagesSection(data.languages))

    if data.interests:
        content.Append(_CreateKeywordSection(data.interests, name="interests", heading="Interests"))

    if data.references:
        content.Append(_CreateReferencesSection(data.references))

    # Every link opens in a new tab; this includes the links produced when rendering markdown content.
    return _ANCHOR_REGEX.sub(r'<a\1 target="_blank">', content.ToString()), rejected_uris


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_OUTPUT_FILENAME = "index.html"


# ----------------------------------------------------------------------
# The document references nothing but the stylesheet; a stylesheet that depends on an icon font or a
# web font requests it itself.
_HTML_TEMPLATE = textwrap.dedent(
    """\
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <meta http-equiv="X-UA-Compatible" content="ie=edge">

      <title>{title}</title>{stylesheet_link}
    </head>
    <body>
    {content}
    </body>
    </html>
    """,
)


# ----------------------------------------------------------------------
# The preset matches the configuration used by `require("markdown-it")()`.
_md = MarkdownIt("js-default")


# ----------------------------------------------------------------------
# Tags that are not associated with a closing tag.
_VOID_TAGS = frozenset(["br", "hr", "img", "input", "link", "meta"])

# Matches the opening tag of an anchor; attribute values are escaped when the content is created,
# so a '>' will never appear within the attributes themselves.
_ANCHOR_REGEX = re.compile(r"<a(?=[\s>])([^>]*)>")

# Matches the characters that a browser removes from a uri before it follows it.
_INSIGNIFICANT_URI_CHARS_REGEX = re.compile(r"[\x00-\x20]")

# Matches the characters that are replaced when a value provided by the content becomes a class.
_CLASS_NAME_REGEX = re.compile(r"[^a-z0-9]+")


# ----------------------------------------------------------------------
# |
# |  Element Creation
# |
# ----------------------------------------------------------------------
class _Element:
    """A html element and the content that it contains."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        tag: str,
        *,
        classes: str = "",
        attributes: dict[str, str] | None = None,
    ) -> None:
        self.tag = tag
        self.classes: list[str] = classes.split()
        self.attributes: dict[str, str] = attributes or {}
        self.children: list[_Element | str] = []

    # ----------------------------------------------------------------------
    def AddClass(self, classes: str) -> Self:
        """Add one or more space-delimited classes to this element."""

        self.classes += classes.split()
        return self

    # ----------------------------------------------------------------------
    def Append(self, child: _Element | str | Iterable[_Element | str]) -> Self:
        """Add content to this element; strings are treated as html and are not escaped."""

        if isinstance(child, (_Element, str)):
            self.children.append(child)
        else:
            self.children += child

        return self

    # ----------------------------------------------------------------------
    def Text(self, value: str) -> Self:
        """Add escaped text content to this element."""

        return self.Append(html.escape(value, quote=False))

    # ----------------------------------------------------------------------
    def Html(self, value: str) -> Self:
        """Add html content to this element."""

        return self.Append(value)

    # ----------------------------------------------------------------------
    def ToString(self, indentation_level: int = 0) -> str:
        """Convert this element and everything that it contains into html."""

        prefix = "  " * indentation_level

        attributes = dict(self.attributes)

        if self.classes:
            attributes = {"class": " ".join(self.classes), **attributes}

        attributes_content = "".join(
            f' {name}="{html.escape(value, quote=True)}"' for name, value in attributes.items()
        )

        if self.tag in _VOID_TAGS:
            return f"{prefix}<{self.tag}{attributes_content}>"

        if not self.children:
            return f"{prefix}<{self.tag}{attributes_content}></{self.tag}>"

        # Content that fits on a single line is displayed on a single line; this prevents the
        # introduction of whitespace that would otherwise be rendered within inline elements.
        if len(self.children) == 1:
            child = self.children[0]

            if isinstance(child, str) and "\n" not in child.strip("\n"):
                return f"{prefix}<{self.tag}{attributes_content}>{child.strip('\n')}</{self.tag}>"

        lines: list[str] = [f"{prefix}<{self.tag}{attributes_content}>"]
        child_prefix = "  " * (indentation_level + 1)

        for child in self.children:
            if isinstance(child, _Element):
                lines.append(child.ToString(indentation_level + 1))
            else:
                lines += [f"{child_prefix}{line}" if line else line for line in child.strip("\n").split("\n")]

        lines.append(f"{prefix}</{self.tag}>")

        return "\n".join(lines)


# ----------------------------------------------------------------------
def _CreateSection(
    name: str,
    heading: str,
    body: _Element | Iterable[_Element],
) -> _Element:
    """Create a section introduced by a heading.

    The icon that decorates the heading is an empty element; the stylesheet decides which icon each
    section is displayed with, or displays none at all.
    """

    return (
        _Element("section", classes=f"section {name}")
        .Append(
            _Element("div", classes="section-header")
            .Append(_Element("span", classes="icon"))
            .Append(_Element("span", classes="heading").Text(heading)),
        )
        .Append(_Element("div", classes="section-body").Append(body))
    )


# ----------------------------------------------------------------------
def _CreateEntry(
    entry_header: _Element | Iterable[_Element],
    entry_body: _Element | Iterable[_Element],
) -> _Element:
    """Create one of the entries that a section is composed of."""

    return (
        _Element("div", classes="entry")
        .Append(_Element("div", classes="entry-header").Append(entry_header))
        .Append(_Element("div", classes="entry-body").Append(entry_body))
    )


# ----------------------------------------------------------------------
def _CreateDetail(classes: str, value: _Element | Iterable[_Element] | str) -> _Element:
    """Create one of the short values that a section displays alongside the others; a string is escaped."""

    content = _Element("span", classes="value")

    if isinstance(value, str):
        content.Text(value)
    else:
        content.Append(value)

    return (
        _Element("div", classes=f"detail {classes}").Append(_Element("span", classes="icon")).Append(content)
    )


# ----------------------------------------------------------------------
def _CreateLinkDetail(classes: str, href: str, alt: str, text: str) -> _Element:
    """Create a detail whose value is displayed as a link."""

    return _CreateDetail(classes, _Element("a", attributes={"href": href, "alt": alt}).Text(text))


# ----------------------------------------------------------------------
def _CreateBulletList(classes: str, values: list[str]) -> _Element:
    """Create the list that displays the values associated with a single entry."""

    return _Element("ul", classes=classes).Append(
        _Element("li").Html(_md.renderInline(value)) for value in values
    )


# ----------------------------------------------------------------------
def _CreateLinkedText(text: str, uri: str | None) -> _Element:
    """Create the div that displays `text`, linked to `uri` when one is available."""

    if not uri:
        return _Element("div").Text(text)

    return _Element("div").Append(_Element("a", attributes={"href": uri, "alt": text}).Text(text))


# ----------------------------------------------------------------------
# |
# |  Basics
# |
# ----------------------------------------------------------------------
def _CreateBasicsSection(basics: Basics, rejected_uris: list[str]) -> _Element:
    """Create the section that displays the picture, name, and label."""

    section = _Element("section", classes="section basics")

    picture_uri = _SafeUri(basics.picture, rejected_uris)

    if picture_uri:
        section.Append(
            _Element("div", classes="picture").Append(
                _Element("img", attributes={"src": picture_uri, "alt": f"Picture of {basics.name}"}),
            ),
        )

    section.Append(_Element("div", classes="name").Html(_md.render(basics.name)))

    if basics.label:
        section.Append(_Element("div", classes="label").Html(_md.renderInline(basics.label)))

    return section


# ----------------------------------------------------------------------
# |
# |  Contact
# |
# ----------------------------------------------------------------------
def _CreateContactSection(basics: Basics, rejected_uris: list[str]) -> _Element:
    """Create the section that displays contact information."""

    details: list[_Element] = []

    if basics.email:
        details.append(
            _CreateLinkDetail("email", f"mailto:{basics.email}", "email address", basics.email),
        )

    website = _SafeUri(basics.website, rejected_uris)

    if website:
        details.append(_CreateLinkDetail("website", website, "website", website))

    if basics.phone:
        details.append(_CreateLinkDetail("phone", f"tel:{basics.phone}", "phone number", basics.phone))

    if basics.location:
        details.append(_CreateLocationDetail(basics.location))

    return _CreateSection("contact", "Contact", details)


# ----------------------------------------------------------------------
def _CreateLocationDetail(location: Location) -> _Element:
    """Create the detail that displays the location; the address and postal code are not displayed."""

    values = [_Element("span", classes="city").Text(location.city)]

    if location.region:
        values.append(_Element("span", classes="region").Text(location.region))

    if location.countryCode:
        values.append(_Element("span", classes="countryCode").Text(location.countryCode))

    return _CreateDetail("location", values)


# ----------------------------------------------------------------------
# |
# |  Profiles
# |
# ----------------------------------------------------------------------
def _CreateProfilesSection(profiles: list[Profile], rejected_uris: list[str]) -> _Element:
    """Create the section that displays profiles."""

    return _CreateSection(
        "profiles",
        "Profiles",
        [_CreateProfileDetail(profile, rejected_uris) for profile in profiles],
    )


# ----------------------------------------------------------------------
def _CreateProfileDetail(profile: Profile, rejected_uris: list[str]) -> _Element:
    """Create a single profile detail.

    The network is provided as a class rather than as an icon, as the networks that can be decorated
    are the ones that the stylesheet has an icon for rather than the ones known here.
    """

    url = _SafeUri(profile.url, rejected_uris)
    classes = f"profile {_ToClassName(profile.network)}"

    if not url:
        return _CreateDetail(classes, profile.username)

    return _CreateDetail(
        classes,
        _Element(
            "a",
            attributes={"href": url, "alt": f"Profile link to {profile.network}"},
        ).Text(profile.username),
    )


# ----------------------------------------------------------------------
# |
# |  About
# |
# ----------------------------------------------------------------------
def _CreateAboutSection(summary: str) -> _Element:
    """Create the section that displays the summary."""

    return _CreateSection("about", "About", _Element("div", classes="summary").Html(_md.render(summary)))


# ----------------------------------------------------------------------
# |
# |  Skills and Interests
# |
# ----------------------------------------------------------------------
def _CreateKeywordSection(
    items: Sequence[Skill | Interest],
    *,
    name: str,
    heading: str,
) -> _Element:
    """Create the section that displays a named collection of keywords.

    Skills and interests are displayed in the same way; they differ only by the section that
    contains them.
    """

    return _CreateSection(
        name,
        heading,
        [
            _CreateEntry(
                _Element("div", classes="name").Html(_md.renderInline(item.name)),
                _Element("ul", classes="keywords").Append(
                    _Element("li", classes="keyword").Html(_md.renderInline(keyword))
                    for keyword in item.keywords
                ),
            )
            for item in items
        ],
    )


# ----------------------------------------------------------------------
# |
# |  Work and Volunteer Experience
# |
# ----------------------------------------------------------------------
def _CreateExperienceSection(
    experiences: Sequence[Work | Volunteer],
    rejected_uris: list[str],
    *,
    name_attribute: str,
    name: str,
    heading: str,
) -> _Element:
    """Create the section that displays experience.

    Work and volunteer experience differ only by the attribute that names the entity involved, which
    is also the class that the stylesheet targets when it styles that name.
    """

    entries: list[_Element] = []

    for experience in experiences:
        entry_body = [
            _Element("div", classes="position").Html(_md.renderInline(experience.position)),
            _Element("div", classes="summary").Html(_md.render(experience.summary)),
        ]

        if experience.highlights:
            entry_body.append(_CreateBulletList("highlights", experience.highlights))

        entries.append(
            _CreateEntry(
                [
                    _CreateLinkedText(
                        getattr(experience, name_attribute),
                        _SafeUri(experience.website, rejected_uris),
                    ).AddClass(name_attribute),
                    _Element("div", classes="startDate").Text(_ToDateString(experience.startDate)),
                    _Element("div", classes="endDate").Text(
                        _ToDateString(experience.endDate) if experience.endDate else "Present",
                    ),
                ],
                entry_body,
            ),
        )

    return _CreateSection(name, heading, entries)


# ----------------------------------------------------------------------
# |
# |  Education
# |
# ----------------------------------------------------------------------
def _CreateEducationSection(education: list[Education]) -> _Element:
    """Create the section that displays education."""

    entries: list[_Element] = []

    for item in education:
        entry_header = [_Element("div", classes="institution").Html(_md.renderInline(item.institution))]

        if item.endDate:
            entry_header.append(_Element("div", classes="endDate").Text(_ToDateString(item.endDate)))

        entry_body = [
            _Element("div", classes="studyType").Html(_md.renderInline(item.studyType)),
            _Element("div", classes="area").Html(_md.renderInline(item.area)),
        ]

        if item.gpa:
            # The value is displayed without the label that introduces it; the stylesheet provides it.
            entry_body.append(_Element("div", classes="gpa").Text(item.gpa))

        if item.courses:
            entry_body.append(_CreateBulletList("courses", item.courses))

        entries.append(_CreateEntry(entry_header, entry_body))

    return _CreateSection("education", "Education", entries)


# ----------------------------------------------------------------------
# |
# |  Awards
# |
# ----------------------------------------------------------------------
def _CreateAwardsSection(awards: list[Award]) -> _Element:
    """Create the section that displays awards."""

    return _CreateSection(
        "awards",
        "Awards",
        [
            _CreateEntry(
                [
                    _Element("div", classes="awarder").Html(_md.renderInline(item.awarder)),
                    _Element("div", classes="date").Text(_ToDateString(item.date)),
                ],
                [
                    _Element("div", classes="title").Html(_md.renderInline(item.title)),
                    _Element("div", classes="summary").Html(_md.render(item.summary)),
                ],
            )
            for item in awards
        ],
    )


# ----------------------------------------------------------------------
# |
# |  Publications
# |
# ----------------------------------------------------------------------
def _CreatePublicationsSection(publications: list[Publication], rejected_uris: list[str]) -> _Element:
    """Create the section that displays publications."""

    return _CreateSection(
        "publications",
        "Publications",
        [
            _CreateEntry(
                [
                    _Element("div", classes="publisher").Html(_md.renderInline(item.publisher)),
                    _Element("div", classes="releaseDate").Text(_ToDateString(item.releaseDate)),
                ],
                [
                    _CreateLinkedText(item.name, _SafeUri(item.website, rejected_uris)).AddClass("name"),
                    _Element("div", classes="summary").Html(_md.render(item.summary)),
                ],
            )
            for item in publications
        ],
    )


# ----------------------------------------------------------------------
# |
# |  Languages
# |
# ----------------------------------------------------------------------
def _CreateLanguagesSection(languages: list[Language]) -> _Element:
    """Create the section that displays languages."""

    return _CreateSection(
        "languages",
        "Languages",
        [
            _CreateDetail(
                "language",
                [
                    _Element("span", classes="name").Html(_md.renderInline(item.language)),
                    _Element("span", classes="fluency").Html(_md.renderInline(item.fluency)),
                ],
            )
            for item in languages
        ],
    )


# ----------------------------------------------------------------------
# |
# |  References
# |
# ----------------------------------------------------------------------
def _CreateReferencesSection(references: list[Reference]) -> _Element:
    """Create the section that displays references."""

    return _CreateSection(
        "references",
        "References",
        [
            _CreateEntry(
                _Element("div", classes="name").Html(_md.renderInline(item.name)),
                _Element("div", classes="reference").Html(_md.render(item.reference))
                if item.reference
                else [],
            )
            for item in references
        ],
    )


# ----------------------------------------------------------------------
# |
# |  Utilities
# |
# ----------------------------------------------------------------------
def _ToDateString(value: Date) -> str:
    """Convert a date into the string used when displaying content."""

    return f"{value:%B %Y}"


# ----------------------------------------------------------------------
def _ToClassName(value: str) -> str:
    """Convert a value provided by the content into a class that a stylesheet can target."""

    return _CLASS_NAME_REGEX.sub("-", value.lower()).strip("-")


# ----------------------------------------------------------------------
def _SafeUri(value: str | None, rejected_uris: list[str]) -> str | None:
    """Return a normalized `value` when it can be displayed; anything else is added to `rejected_uris`.

    Uris written as markdown are validated by markdown-it, which rejects those that execute content
    when they are followed ('javascript:', for example). Uris provided directly by the schema are
    never rendered as markdown, so the same validation is applied here to ensure that generated
    content cannot execute the content that produced it.

    That validation assumes normalized content, so it is applied to the uri as a browser would see
    it rather than to the uri as it was written; a scheme that embeds an insignificant character
    ('java<TAB>script:', for example) is not recognized by the validation itself, yet a browser
    removes that character before following the uri. The uri that is displayed is normalized so that
    any remaining character that is significant within a uri is encoded rather than interpreted.
    """

    if not value:
        return None

    if not _md.validateLink(_INSIGNIFICANT_URI_CHARS_REGEX.sub("", value)):
        rejected_uris.append(value)
        return None

    return _md.normalizeLink(value)
