# noqa: D100
import html
import re
import shutil
import textwrap

from dataclasses import dataclass
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
    *,
    include_fonts: bool = True,
) -> None:
    """Generate HTML content from JSON resume content.

    The html is written to `index.html` within `output_directory`. `css_filename` (when provided) is
    symlinked to `<css filename>` within that same directory and referenced by the generated html;
    no stylesheet is referenced when `css_filename` is not provided.
    """

    if css_filename is not None and css_filename.name == _OUTPUT_FILENAME:
        msg = f"A stylesheet named '{_OUTPUT_FILENAME}' would replace the generated html."
        raise ValueError(msg)

    with dm.Nested(f"Reading '{filename}'..."):
        data = ResumeData.FromFile(filename)

    with dm.Nested("Generating content...") as content_dm:
        head_links: list[str] = []

        if include_fonts:
            head_links.append(_FONTS_LINK)

        if css_filename is not None:
            # The name is url-encoded so that characters that are significant within a uri ('#' and
            # '?', for example) reference the file rather than a fragment or query.
            href = html.escape(quote(css_filename.name), quote=True)
            head_links.append(f'<link rel="stylesheet" href="{href}" />')

        head_links_content = "\n".join(f"  {link}" for link in head_links)

        if head_links_content:
            head_links_content = f"\n\n{head_links_content}"

        fragment, rejected_uris = _CreateContent(data)

        for uri in rejected_uris:
            content_dm.WriteWarning(
                f"The uri '{uri}' is not safe to display and was not included in the generated content.\n",
            )

        content = _HTML_TEMPLATE.format(
            title=html.escape(data.basics.name, quote=False),
            head_links=head_links_content,
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

    content = _Element("div", classes="container-fluid", attributes={"id": "content"})

    content.Append(_CreateTitleRow(data.basics, rejected_uris))
    content.Append(_CreateContactRow(data.basics, rejected_uris))

    if data.basics.profiles:
        content.Append(_CreateProfilesRow(data.basics.profiles, rejected_uris))

    if data.basics.summary:
        content.Append(_CreateAboutRow(data.basics.summary))

    if data.skills:
        content.Append(
            _CreateKeywordRows(
                data.skills, item_class="skill", icon_classes="fas fa-lg fa-code", title="Skills"
            ),
        )

    if data.work:
        content.Append(
            _CreateExperienceRows(
                data.work,
                rejected_uris,
                name_attribute="company",
                item_class="experience",
                icon_classes="fas fa-lg fa-pen-square",
                title="Work Experience",
            ),
        )

    if data.education:
        content.Append(_CreateEducationRows(data.education))

    if data.volunteer:
        content.Append(
            _CreateExperienceRows(
                data.volunteer,
                rejected_uris,
                name_attribute="organization",
                item_class="volunteer",
                icon_classes="fas fa-lg fa-handshake-angle",
                title="Volunteer Experience",
            ),
        )

    if data.awards:
        content.Append(_CreateAwardRows(data.awards))

    if data.publications:
        content.Append(_CreatePublicationRows(data.publications, rejected_uris))

    if data.languages:
        content.Append(_CreateLanguagesRow(data.languages))

    if data.interests:
        content.Append(
            _CreateKeywordRows(
                data.interests, item_class="interest", icon_classes="fas fa-lg fa-heart", title="Interests"
            ),
        )

    if data.references:
        content.Append(_CreateReferenceRows(data.references))

    # Every link opens in a new tab; this includes the links produced when rendering markdown content.
    return _ANCHOR_REGEX.sub(r'<a\1 target="_blank">', content.ToString()), rejected_uris


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_OUTPUT_FILENAME = "index.html"


# ----------------------------------------------------------------------
_HTML_TEMPLATE = textwrap.dedent(
    """\
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <meta http-equiv="X-UA-Compatible" content="ie=edge">

      <title>{title}</title>

      <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous" />
      <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/js/all.min.js"></script>{head_links}
    </head>
    <body>
    {content}
    </body>
    </html>
    """,
)


# ----------------------------------------------------------------------
# The link included when fonts are requested; every font referenced by the bundled stylesheet is
# requested so that the styling does not silently fall back to a font that happens to be installed.
_FONTS_LINK = '<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Open+Sans:400,300,600|Merriweather:400,700" />'


# ----------------------------------------------------------------------
# The preset matches the configuration used by `require("markdown-it")()`.
_md = MarkdownIt("js-default")


# ----------------------------------------------------------------------
_LINE_HEADER_CLASSES = "col-6 section header"
_SECTION_HEADER_CLASSES = "col-3 section header"
_SECTION_CONTENT_CLASSES = "col section content"
_SUBSECTION_HEADER_CLASSES = "col-3 subsection header"
_SUBSECTION_CONTENT_CLASSES = "col subsection content"

_BADGE_CLASSES = "badge badge-pill badge-primary"

# Tags that are not associated with a closing tag.
_VOID_TAGS = frozenset(["br", "hr", "img", "input", "link", "meta"])

# Matches the opening tag of an anchor; attribute values are escaped when the content is created,
# so a '>' will never appear within the attributes themselves.
_ANCHOR_REGEX = re.compile(r"<a(?=[\s>])([^>]*)>")

# Matches the opening tag of the first element within a html fragment.
_FIRST_TAG_REGEX = re.compile(
    r"^\s*<(?P<tag>[A-Za-z][^\s/>]*)(?P<attributes>[^>]*?)(?P<terminator>/?>)",
)

# Matches the characters that a browser removes from a uri before it follows it.
_INSIGNIFICANT_URI_CHARS_REGEX = re.compile(r"[\x00-\x20]")


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class _ProfileDecorator:
    """Icon and link used when displaying a profile associated with a known network."""

    icon: str
    link: str


# ----------------------------------------------------------------------
_PROFILE_DECORATORS: dict[str, _ProfileDecorator] = {
    "linkedin": _ProfileDecorator(icon="fab fa-linkedin", link="https://www.linkedin.com/"),
    "github": _ProfileDecorator(icon="fab fa-github", link="https://github.com/"),
    "codestats": _ProfileDecorator(icon="fas fa-keyboard", link="https://codestats.net/"),
}


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
def _CreateSectionRow(
    row_classes: str,
    header_classes: str,
    icon_classes: str,
    title: str,
) -> _Element:
    """Create a row introduced by an icon and title."""

    return _Element("div", classes=row_classes).Append(
        _Element("div", classes=header_classes)
        .Append(_Element("div", classes="icon").Append(_Element("i", classes=icon_classes)))
        .Append(_Element("div").Text(title)),
    )


# ----------------------------------------------------------------------
def _CreateInlineContainer(*details: _Element) -> _Element:
    """Create the container used to display section details on a single line."""

    return _Element("div", classes="container-fluid inline").Append(
        _Element("div", classes="row").Append(details),
    )


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
# |  Title
# |
# ----------------------------------------------------------------------
def _CreateTitleRow(basics: Basics, rejected_uris: list[str]) -> _Element:
    """Create the row that displays the picture and name."""

    picture_uri = _SafeUri(basics.picture, rejected_uris)

    if picture_uri:
        picture: _Element = _Element(
            "img",
            attributes={"src": picture_uri, "alt": f"Picture of {basics.name}"},
        )
    else:
        picture = _Element("div")

    name = _Element("div", classes=f"{_SECTION_CONTENT_CLASSES} name").Html(_md.render(basics.name))

    if basics.label:
        name.Append(_Element("div", classes="label").Html(_md.renderInline(basics.label)))

    return (
        _Element("div", classes="row title")
        .Append(_Element("div", classes=f"{_SECTION_HEADER_CLASSES} picture").Append(picture))
        .Append(name)
    )


# ----------------------------------------------------------------------
# |
# |  Contact
# |
# ----------------------------------------------------------------------
def _CreateContactRow(basics: Basics, rejected_uris: list[str]) -> _Element:
    """Create the row that displays contact information."""

    details: list[_Element] = []

    if basics.email:
        details.append(
            _CreateContactDetail(
                "fas fa-lg fa-envelope",
                "info email",
                f"mailto:{basics.email}",
                "email address",
                basics.email,
            ),
        )
    else:
        details.append(_Element("span"))

    website = _SafeUri(basics.website, rejected_uris)

    if website:
        details.append(
            _CreateContactDetail(
                "fas fa-lg fa-link",
                "info website",
                website,
                "website",
                website,
            ),
        )
    else:
        details.append(_Element("span"))

    if basics.phone:
        details.append(
            _CreateContactDetail(
                "fas fa-lg fa-phone",
                "info phone",
                f"tel:{basics.phone}",
                "phone number",
                basics.phone,
            ),
        )
    else:
        details.append(_Element("span"))

    details.append(_CreateLocationDetail(basics.location) if basics.location else _Element("span"))

    return _CreateSectionRow(
        "row contact", _SECTION_HEADER_CLASSES, "fas fa-lg fa-address-book", "Contact"
    ).Append(
        _Element("div", classes=_SECTION_CONTENT_CLASSES).Append(_CreateInlineContainer(*details)),
    )


# ----------------------------------------------------------------------
def _CreateContactDetail(
    icon_classes: str,
    info_classes: str,
    href: str,
    alt: str,
    text: str,
) -> _Element:
    """Create a single contact detail displayed as a link."""

    return (
        _Element("div", classes="detail col")
        .Append(_Element("div", classes="icon").Append(_Element("i", classes=icon_classes)))
        .Append(
            _Element("div", classes=info_classes).Append(
                _Element("a", attributes={"href": href, "alt": alt}).Text(text),
            ),
        )
    )


# ----------------------------------------------------------------------
def _CreateLocationDetail(location: Location) -> _Element:
    """Create the contact detail that displays the location."""

    # The address and postal code are not displayed.
    info = _Element("div", classes="info location").Append(
        _Element("div", classes="city").Text(location.city),
    )

    if location.region:
        info.Append(_Element("div", classes="region").Text(location.region))
    else:
        info.Append(_Element("span"))

    if location.countryCode:
        info.Append(_Element("div", classes="countryCode").Text(location.countryCode))
    else:
        info.Append(_Element("span"))

    return (
        _Element("div", classes="detail col")
        .Append(_Element("div", classes="icon").Append(_Element("i", classes="fas fa-lg fa-map-marker")))
        .Append(info)
    )


# ----------------------------------------------------------------------
# |
# |  Profiles
# |
# ----------------------------------------------------------------------
def _CreateProfilesRow(profiles: list[Profile], rejected_uris: list[str]) -> _Element:
    """Create the row that displays profiles."""

    return _CreateSectionRow(
        "row profiles", _SECTION_HEADER_CLASSES, "fas fa-lg fa-hashtag", "Profiles"
    ).Append(
        _Element("div", classes=_SECTION_CONTENT_CLASSES).Append(
            _CreateInlineContainer(
                *(_CreateProfileDetail(profile, rejected_uris) for profile in profiles),
            ),
        ),
    )


# ----------------------------------------------------------------------
def _CreateProfileDetail(profile: Profile, rejected_uris: list[str]) -> _Element:
    """Create a single profile detail."""

    detail = _Element("div", classes="detail col")

    decorator = _PROFILE_DECORATORS.get(profile.network.lower())

    if decorator is None:
        detail.Append(_Element("span"))
    else:
        detail.Append(
            _Element("div", classes="icon network").Append(
                # The link displays an icon rather than text, so its name is provided by
                # `aria-label`; without it, the link is not identifiable by a screen reader.
                _Element(
                    "a",
                    attributes={"href": decorator.link, "aria-label": f"Link to {profile.network}"},
                ).Append(_Element("i", classes=f"fa-lg {decorator.icon}")),
            ),
        )

    url = _SafeUri(profile.url, rejected_uris)
    info = _Element("div", classes="info link")

    if url:
        info.Append(
            _Element(
                "a",
                attributes={"href": url, "alt": f"Profile link to {profile.network}"},
            ).Text(profile.username),
        )
    else:
        info.Text(profile.username)

    return detail.Append(info)


# ----------------------------------------------------------------------
# |
# |  About
# |
# ----------------------------------------------------------------------
def _CreateAboutRow(summary: str) -> _Element:
    """Create the row that displays the summary."""

    return _CreateSectionRow("row about", _SECTION_HEADER_CLASSES, "fas fa-lg fa-user", "About").Append(
        _Element("div", classes=_SECTION_CONTENT_CLASSES).Html(_md.render(summary)),
    )


# ----------------------------------------------------------------------
# |
# |  Skills and Interests
# |
# ----------------------------------------------------------------------
def _CreateKeywordRows(
    items: Sequence[Skill | Interest],
    *,
    item_class: str,
    icon_classes: str,
    title: str,
) -> list[_Element]:
    """Create the rows that display a named collection of keywords.

    Skills and interests are displayed in the same way; `keyword_list` is the class that the
    stylesheet targets when it styles both of them.
    """

    rows = [_CreateSectionRow(f"row {item_class}s", _LINE_HEADER_CLASSES, icon_classes, title)]

    rows += [
        _Element("div", classes=f"row line_item keyword_list {item_class}")
        .Append(
            _Element("div", classes=_SUBSECTION_HEADER_CLASSES.replace("col-3", "col-5")).Append(
                _Element("div", classes="name").Html(_md.renderInline(item.name)),
            ),
        )
        .Append(
            _Element("div", classes=_SUBSECTION_CONTENT_CLASSES).Append(
                _Element("div", classes="keywords").Append(
                    _CreateKeywordBadge(keyword) for keyword in item.keywords
                ),
            ),
        )
        for item in items
    ]

    return rows


# ----------------------------------------------------------------------
def _CreateKeywordBadge(keyword: str) -> _Element:
    """Create the badge that displays a single keyword."""

    content = _md.renderInline(keyword)

    # A keyword that renders as markup (a link, for example) is displayed as the rendered markup itself;
    # anything else is wrapped in a div. Note that the original implementation attempted to display
    # rendered content that did not begin with an element (an escaped ampersand, for example) as markup
    # as well, which produced a runtime error.
    match = _FIRST_TAG_REGEX.match(content) if content != keyword else None

    if match is None:
        return _Element("div", classes="item").Append(
            _Element("div", classes=f"nolink {_BADGE_CLASSES}").Html(content),
        )

    return _Element("div", classes="item").Html(_AddClasses(content, match, f"link {_BADGE_CLASSES}"))


# ----------------------------------------------------------------------
def _AddClasses(content: str, match: re.Match[str], classes: str) -> str:
    """Add classes to the first element within the html fragment provided."""

    attributes = match.group("attributes")

    existing_class_match = re.search(r"""\bclass=(?P<quote>["'])(?P<value>[^"']*)(?P=quote)""", attributes)

    if existing_class_match is None:
        updated_attributes = f'{attributes} class="{html.escape(classes, quote=True)}"'
    else:
        updated_value = f"{existing_class_match.group('value')} {html.escape(classes, quote=True)}"

        updated_attributes = (
            attributes[: existing_class_match.start("value")]
            + updated_value
            + attributes[existing_class_match.end("value") :]
        )

    return (
        content[: match.start()]
        + f"<{match.group('tag')}{updated_attributes}{match.group('terminator')}"
        + content[match.end() :]
    )


# ----------------------------------------------------------------------
# |
# |  Work and Volunteer Experience
# |
# ----------------------------------------------------------------------
def _CreateExperienceRows(
    experiences: Sequence[Work | Volunteer],
    rejected_uris: list[str],
    *,
    name_attribute: str,
    item_class: str,
    icon_classes: str,
    title: str,
) -> list[_Element]:
    """Create the rows that display experience.

    Work and volunteer experience differ only by the attribute that names the entity involved, which
    is also the class that the stylesheet targets when it styles that name.
    """

    rows = [_CreateSectionRow(f"row {item_class}s", _LINE_HEADER_CLASSES, icon_classes, title)]

    for experience in experiences:
        content = (
            _Element("div", classes=_SUBSECTION_CONTENT_CLASSES)
            .Append(_Element("div", classes="position").Html(_md.renderInline(experience.position)))
            .Append(_Element("div", classes="summary").Html(_md.render(experience.summary)))
        )

        if experience.highlights:
            content.Append(_CreateBulletList("highlights", experience.highlights))

        rows.append(
            _Element("div", classes=f"row line_item {item_class}")
            .Append(
                _Element("div", classes=_SUBSECTION_HEADER_CLASSES)
                .Append(
                    _CreateLinkedText(
                        getattr(experience, name_attribute),
                        _SafeUri(experience.website, rejected_uris),
                    ).AddClass(name_attribute),
                )
                .Append(_Element("div", classes="startDate").Text(_ToDateString(experience.startDate)))
                .Append(
                    _Element("div", classes="endDate").Text(
                        _ToDateString(experience.endDate) if experience.endDate else "Present",
                    ),
                ),
            )
            .Append(content),
        )

    return rows


# ----------------------------------------------------------------------
# |
# |  Education
# |
# ----------------------------------------------------------------------
def _CreateEducationRows(education: list[Education]) -> list[_Element]:
    """Create the rows that display education."""

    rows = [
        _CreateSectionRow("row educations", _LINE_HEADER_CLASSES, "fas fa-lg fa-graduation-cap", "Education"),
    ]

    for item in education:
        content = (
            _Element("div", classes=_SUBSECTION_CONTENT_CLASSES)
            .Append(_Element("div", classes="studyType").Html(_md.renderInline(item.studyType)))
            .Append(_Element("div", classes="area").Html(_md.renderInline(item.area)))
        )

        if item.gpa:
            # The value is displayed without the label that introduces it; the stylesheet provides it.
            content.Append(_Element("div", classes="gpa").Text(item.gpa))

        if item.courses:
            content.Append(_CreateBulletList("courses", item.courses))

        rows.append(
            _Element("div", classes="row line_item education")
            .Append(
                _Element("div", classes=_SUBSECTION_HEADER_CLASSES)
                .Append(_Element("div", classes="institution").Html(_md.renderInline(item.institution)))
                .Append(
                    _Element("div", classes="endDate").Text(
                        _ToDateString(item.endDate) if item.endDate else "",
                    ),
                ),
            )
            .Append(content),
        )

    return rows


# ----------------------------------------------------------------------
# |
# |  Awards
# |
# ----------------------------------------------------------------------
def _CreateAwardRows(awards: list[Award]) -> list[_Element]:
    """Create the rows that display awards."""

    rows = [_CreateSectionRow("row awards", _LINE_HEADER_CLASSES, "fas fa-lg fa-trophy", "Awards")]

    rows += [
        _Element("div", classes="row line_item award")
        .Append(
            _Element("div", classes=_SUBSECTION_HEADER_CLASSES)
            .Append(_Element("div", classes="awarder").Html(_md.renderInline(item.awarder)))
            .Append(_Element("div", classes="date").Text(_ToDateString(item.date))),
        )
        .Append(
            _Element("div", classes=_SUBSECTION_CONTENT_CLASSES)
            .Append(_Element("div", classes="title").Html(_md.renderInline(item.title)))
            .Append(_Element("div", classes="summary").Html(_md.render(item.summary))),
        )
        for item in awards
    ]

    return rows


# ----------------------------------------------------------------------
# |
# |  Publications
# |
# ----------------------------------------------------------------------
def _CreatePublicationRows(publications: list[Publication], rejected_uris: list[str]) -> list[_Element]:
    """Create the rows that display publications."""

    rows = [
        _CreateSectionRow("row publications", _LINE_HEADER_CLASSES, "fas fa-lg fa-book", "Publications"),
    ]

    rows += [
        _Element("div", classes="row line_item publication")
        .Append(
            _Element("div", classes=_SUBSECTION_HEADER_CLASSES)
            .Append(_Element("div", classes="publisher").Html(_md.renderInline(item.publisher)))
            .Append(_Element("div", classes="releaseDate").Text(_ToDateString(item.releaseDate))),
        )
        .Append(
            _Element("div", classes=_SUBSECTION_CONTENT_CLASSES)
            .Append(_CreateLinkedText(item.name, _SafeUri(item.website, rejected_uris)).AddClass("name"))
            .Append(_Element("div", classes="summary").Html(_md.render(item.summary))),
        )
        for item in publications
    ]

    return rows


# ----------------------------------------------------------------------
# |
# |  Languages
# |
# ----------------------------------------------------------------------
def _CreateLanguagesRow(languages: list[Language]) -> _Element:
    """Create the row that displays languages."""

    return _CreateSectionRow(
        "row languages", _SECTION_HEADER_CLASSES, "fas fa-lg fa-language", "Languages"
    ).Append(
        _Element("div", classes=_SECTION_CONTENT_CLASSES).Append(
            _CreateInlineContainer(
                *(
                    _Element("div", classes="detail col")
                    .Append(_Element("div", classes="language").Html(_md.renderInline(item.language)))
                    .Append(_Element("div", classes="fluency").Html(_md.renderInline(item.fluency)))
                    for item in languages
                ),
            ),
        ),
    )


# ----------------------------------------------------------------------
# |
# |  References
# |
# ----------------------------------------------------------------------
def _CreateReferenceRows(references: list[Reference]) -> list[_Element]:
    """Create the rows that display references."""

    rows = [
        _CreateSectionRow("row references", _LINE_HEADER_CLASSES, "fas fa-lg fa-quote-left", "References"),
    ]

    rows += [
        _Element("div", classes="row line_item reference")
        .Append(
            _Element("div", classes=_SUBSECTION_HEADER_CLASSES).Append(
                _Element("div", classes="name").Html(_md.renderInline(item.name)),
            ),
        )
        .Append(
            _Element("div", classes=_SUBSECTION_CONTENT_CLASSES).Html(
                _md.render(item.reference) if item.reference else "",
            ),
        )
        for item in references
    ]

    return rows


# ----------------------------------------------------------------------
# |
# |  Utilities
# |
# ----------------------------------------------------------------------
def _ToDateString(value: Date) -> str:
    """Convert a date into the string used when displaying content."""

    return f"{value:%B %Y}"


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
