"""Unit tests for lib/generate_html.py."""

import io
import textwrap

from pathlib import Path

import pytest

from dbrownell_Common.Streams.DoneManager import DoneManager

from dbrownell_ResumeTools.lib.generate_html import GenerateHtml


# ----------------------------------------------------------------------
# |
# |  Content
# |
# ----------------------------------------------------------------------
MINIMAL_CONTENT = """\
    basics:
      name: Sam Taylor
    """

# Content that populates every value displayed within the generated html.
FULL_CONTENT = """\
    basics:
      name: Sam Taylor
      picture: https://example.com/photo.jpg
      email: sam@example.com
      phone: (555) 555-0142
      website: https://example.com
      summary: A **summary**.
      location:
        address: 1 Main Street
        city: Raleigh
        postalCode: "27601"
        countryCode: US
        region: NC
      profiles:
        - network: GitHub
          username: samtaylor
          url: https://github.com/samtaylor
        # A network without a decorator is displayed without an icon.
        - network: Bitbucket
          username: sam
          url: https://bitbucket.org/sam
    skills:
      - name: Python
        keywords:
          - asyncio
          # A keyword that renders as markup is displayed as the markup itself.
          - "[tokio](https://tokio.rs)"
    work:
      - company: Northwind
        position: Engineer
        website: https://northwind.example.com
        startDate: 2019-03-01
        # endDate is omitted to indicate a current position.
        summary: Did work.
      - company: Contoso
        position: Senior Engineer
        startDate: 2014-06-15
        endDate: 2019-02-28
        summary: Did other work.
    education:
      - institution: Georgia Tech
        area: Computer Science
        studyType: Master of Science
        endDate: 2014-05-03
      - institution: UNC
        area: Computer Science
        studyType: Bachelor of Science
    """

# Content whose uris execute content when they are followed; none of them are displayed.
UNSAFE_CONTENT = """\
    basics:
      name: Sam Taylor
      picture: "javascript:alert(1)"
      email: sam@example.com
      website: "javascript:alert(2)"
      profiles:
        - network: GitHub
          username: samtaylor
          url: "vbscript:msgbox(3)"
    work:
      - company: Contoso
        position: Engineer
        website: "data:text/html,<script>alert(4)</script>"
        startDate: 2014-06-15
        endDate: 2019-02-28
        summary: Did work.
    """

UNSAFE_URIS = [
    "javascript:alert(1)",
    "javascript:alert(2)",
    "vbscript:msgbox(3)",
    "data:text/html,<script>alert(4)</script>",
]

CSS = "body { color: red; }\n"

FONTS_LINK = '  <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Open+Sans:400,300,600|Merriweather:400,700" />\n'


# ----------------------------------------------------------------------
# |
# |  Helpers
# |
# ----------------------------------------------------------------------
def _Generate(
    tmp_path: Path,
    content: str,
    css_filename: Path | None = None,
    *,
    include_fonts: bool = True,
) -> tuple[Path, str]:
    """Generate html and return the output directory and the terminal output produced."""

    filename = tmp_path / "resume.yaml"
    filename.write_text(textwrap.dedent(content), encoding="utf-8")

    output_directory = tmp_path / "output"

    sink = io.StringIO()

    with DoneManager.Create(sink, "Testing...") as dm:
        GenerateHtml(dm, filename, output_directory, css_filename, include_fonts=include_fonts)

    return output_directory, sink.getvalue()


# ----------------------------------------------------------------------
def _GenerateContent(
    tmp_path: Path,
    content: str,
    css_filename: Path | None = None,
    *,
    include_fonts: bool = True,
) -> str:
    """Generate html and return the content that was generated."""

    output_directory, _ = _Generate(tmp_path, content, css_filename, include_fonts=include_fonts)

    return (output_directory / "index.html").read_text(encoding="utf-8")


# ----------------------------------------------------------------------
def _Fragment(content: str, indentation_level: int) -> str:
    """Return an html fragment as it appears within the generated content."""

    return textwrap.indent(textwrap.dedent(content), "  " * indentation_level)


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
# |
# |  Document
# |
# ----------------------------------------------------------------------
def test_MinimalContent(tmp_path: Path):
    """The document generated for the smallest valid resume."""

    expected = textwrap.dedent(
        """\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <meta http-equiv="X-UA-Compatible" content="ie=edge">

          <title>Sam Taylor</title>

          <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous" />
          <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/js/all.min.js"></script>
        </head>
        <body>
          <div class="container-fluid" id="content">
            <div class="row title">
              <div class="col-3 section header picture">
                <div></div>
              </div>
              <div class="col section content name"><p>Sam Taylor</p></div>
            </div>
            <div class="row contact">
              <div class="col-3 section header">
                <div class="icon">
                  <i class="fas fa-lg fa-address-book"></i>
                </div>
                <div>Contact</div>
              </div>
              <div class="col section content">
                <div class="container-fluid inline">
                  <div class="row">
                    <span></span>
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </body>
        </html>
        """,
    )

    assert _GenerateContent(tmp_path, MINIMAL_CONTENT, include_fonts=False) == expected


# ----------------------------------------------------------------------
def test_OutputDirIsCreated(tmp_path: Path):
    output_directory, _ = _Generate(tmp_path, MINIMAL_CONTENT)

    assert (output_directory / "index.html").is_file()


# ----------------------------------------------------------------------
def test_Fonts(tmp_path: Path):
    assert FONTS_LINK in _GenerateContent(tmp_path, MINIMAL_CONTENT)


# ----------------------------------------------------------------------
def test_WithoutFonts(tmp_path: Path):
    assert FONTS_LINK not in _GenerateContent(tmp_path, MINIMAL_CONTENT, include_fonts=False)


# ----------------------------------------------------------------------
def test_EmptySectionsAreNotDisplayed(tmp_path: Path):
    content = _GenerateContent(tmp_path, MINIMAL_CONTENT)

    assert "row profiles" not in content
    assert "row about" not in content
    assert "row skills" not in content
    assert "row experiences" not in content
    assert "row educations" not in content


# ----------------------------------------------------------------------
# |
# |  Title
# |
# ----------------------------------------------------------------------
def test_Title(tmp_path: Path):
    expected = _Fragment(
        """\
        <div class="row title">
          <div class="col-3 section header picture">
            <img src="https://example.com/photo.jpg" alt="Picture of Sam Taylor">
          </div>
          <div class="col section content name"><p>Sam Taylor</p></div>
        </div>
        """,
        2,
    )

    assert expected in _GenerateContent(tmp_path, FULL_CONTENT)


# ----------------------------------------------------------------------
# |
# |  Contact
# |
# ----------------------------------------------------------------------
def test_Contact(tmp_path: Path):
    expected = _Fragment(
        """\
        <div class="row">
          <div class="detail col">
            <div class="icon">
              <i class="fas fa-lg fa-envelope"></i>
            </div>
            <div class="info email">
              <a href="mailto:sam@example.com" alt="email address" target="_blank">sam@example.com</a>
            </div>
          </div>
          <div class="detail col">
            <div class="icon">
              <i class="fas fa-lg fa-link"></i>
            </div>
            <div class="info website">
              <a href="https://example.com" alt="website" target="_blank">https://example.com</a>
            </div>
          </div>
          <div class="detail col">
            <div class="icon">
              <i class="fas fa-lg fa-phone"></i>
            </div>
            <div class="info phone">
              <a href="tel:(555) 555-0142" alt="phone number" target="_blank">(555) 555-0142</a>
            </div>
          </div>
          <div class="detail col">
            <div class="icon">
              <i class="fas fa-lg fa-map-marker"></i>
            </div>
            <div class="info location">
              <div class="city">Raleigh</div>
              <div class="region">NC</div>
              <div class="countryCode">US</div>
            </div>
          </div>
        </div>
        """,
        5,
    )

    assert expected in _GenerateContent(tmp_path, FULL_CONTENT)


# ----------------------------------------------------------------------
def test_LocationWithoutOptionalValues(tmp_path: Path):
    """The address and postal code are not displayed; the region and country code are optional."""

    content = _GenerateContent(
        tmp_path,
        """\
        basics:
          name: Sam Taylor
          location:
            address: 1 Main Street
            city: Raleigh
            postalCode: "27601"
        """,
    )

    expected = _Fragment(
        """\
        <div class="info location">
          <div class="city">Raleigh</div>
          <span></span>
          <span></span>
        </div>
        """,
        7,
    )

    assert expected in content

    assert "1 Main Street" not in content
    assert "27601" not in content


# ----------------------------------------------------------------------
# |
# |  Profiles
# |
# ----------------------------------------------------------------------
def test_Profiles(tmp_path: Path):
    expected = _Fragment(
        """\
        <div class="row">
          <div class="detail col">
            <div class="icon network">
              <a href="https://github.com/" aria-label="Link to GitHub" target="_blank">
                <i class="fa-lg fab fa-github"></i>
              </a>
            </div>
            <div class="info link">
              <a href="https://github.com/samtaylor" alt="Profile link to GitHub" target="_blank">samtaylor</a>
            </div>
          </div>
          <div class="detail col">
            <span></span>
            <div class="info link">
              <a href="https://bitbucket.org/sam" alt="Profile link to Bitbucket" target="_blank">sam</a>
            </div>
          </div>
        </div>
        """,
        5,
    )

    assert expected in _GenerateContent(tmp_path, FULL_CONTENT)


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("network", "icon"),
    [
        ("linkedin", "fab fa-linkedin"),
        ("GitHub", "fab fa-github"),
        ("CodeStats", "fas fa-keyboard"),
    ],
)
def test_ProfileNetworksAreCaseInsensitive(tmp_path: Path, network: str, icon: str):
    content = _GenerateContent(
        tmp_path,
        f"""\
        basics:
          name: Sam Taylor
          profiles:
            - network: {network}
              username: sam
              url: https://example.com/sam
        """,
    )

    assert f'<i class="fa-lg {icon}"></i>' in content


# ----------------------------------------------------------------------
# |
# |  About
# |
# ----------------------------------------------------------------------
def test_About(tmp_path: Path):
    expected = _Fragment(
        """\
        <div class="row about">
          <div class="col-3 section header">
            <div class="icon">
              <i class="fas fa-lg fa-user"></i>
            </div>
            <div>About</div>
          </div>
          <div class="col section content"><p>A <strong>summary</strong>.</p></div>
        </div>
        """,
        2,
    )

    assert expected in _GenerateContent(tmp_path, FULL_CONTENT)


# ----------------------------------------------------------------------
# |
# |  Skills
# |
# ----------------------------------------------------------------------
def test_Skills(tmp_path: Path):
    expected = _Fragment(
        """\
        <div class="row line_item skill">
          <div class="col-5 subsection header">
            <div class="name">Python</div>
          </div>
          <div class="col subsection content">
            <div class="keywords">
              <div class="item">
                <div class="nolink badge badge-pill badge-primary">asyncio</div>
              </div>
              <div class="item"><a href="https://tokio.rs" class="link badge badge-pill badge-primary" target="_blank">tokio</a></div>
            </div>
          </div>
        </div>
        """,
        2,
    )

    assert expected in _GenerateContent(tmp_path, FULL_CONTENT)


# ----------------------------------------------------------------------
def test_SkillKeywordThatRendersWithoutAnElement(tmp_path: Path):
    """Rendered content that does not begin with an element is displayed as a badge."""

    content = _GenerateContent(
        tmp_path,
        """\
        basics:
          name: Sam Taylor
        skills:
          - name: Python
            keywords:
              - R&D
        """,
    )

    expected = _Fragment(
        """\
        <div class="item">
          <div class="nolink badge badge-pill badge-primary">R&amp;D</div>
        </div>
        """,
        5,
    )

    assert expected in content


# ----------------------------------------------------------------------
# |
# |  Work Experience
# |
# ----------------------------------------------------------------------
def test_Work(tmp_path: Path):
    content = _GenerateContent(tmp_path, FULL_CONTENT)

    # A current position with a website is displayed as a link
    current = _Fragment(
        """\
        <div class="row line_item experience">
          <div class="col-3 subsection header">
            <div class="company">
              <a href="https://northwind.example.com" alt="Northwind" target="_blank">Northwind</a>
            </div>
            <div class="startDate">March 2019</div>
            <div class="endDate">Present</div>
          </div>
          <div class="col subsection content">
            <div class="position">Engineer</div>
            <div class="summary"><p>Did work.</p></div>
          </div>
        </div>
        """,
        2,
    )

    # A previous position without a website is displayed as text
    previous = _Fragment(
        """\
        <div class="row line_item experience">
          <div class="col-3 subsection header">
            <div class="company">Contoso</div>
            <div class="startDate">June 2014</div>
            <div class="endDate">February 2019</div>
          </div>
          <div class="col subsection content">
            <div class="position">Senior Engineer</div>
            <div class="summary"><p>Did other work.</p></div>
          </div>
        </div>
        """,
        2,
    )

    assert current in content
    assert previous in content


# ----------------------------------------------------------------------
# |
# |  Education
# |
# ----------------------------------------------------------------------
def test_Education(tmp_path: Path):
    content = _GenerateContent(tmp_path, FULL_CONTENT)

    with_end_date = _Fragment(
        """\
        <div class="row line_item education">
          <div class="col-3 subsection header">
            <div class="institution">Georgia Tech</div>
            <div class="endDate">May 2014</div>
          </div>
          <div class="col subsection content">
            <div class="studyType">Master of Science</div>
            <div class="area">Computer Science</div>
          </div>
        </div>
        """,
        2,
    )

    without_end_date = _Fragment(
        """\
        <div class="row line_item education">
          <div class="col-3 subsection header">
            <div class="institution">UNC</div>
            <div class="endDate"></div>
          </div>
          <div class="col subsection content">
            <div class="studyType">Bachelor of Science</div>
            <div class="area">Computer Science</div>
          </div>
        </div>
        """,
        2,
    )

    assert with_end_date in content
    assert without_end_date in content


# ----------------------------------------------------------------------
# |
# |  Links and Escaping
# |
# ----------------------------------------------------------------------
def test_EveryLinkOpensInANewTab(tmp_path: Path):
    content = _GenerateContent(tmp_path, FULL_CONTENT)

    assert content.count("<a ") == content.count(' target="_blank">')


# ----------------------------------------------------------------------
def test_LinksWithinRenderedMarkdownOpenInANewTab(tmp_path: Path):
    content = _GenerateContent(
        tmp_path,
        """\
        basics:
          name: Sam Taylor
          summary: See [my work](https://example.com/work).
        """,
    )

    assert '<p>See <a href="https://example.com/work" target="_blank">my work</a>.</p>' in content


# ----------------------------------------------------------------------
def test_TextIsEscaped(tmp_path: Path):
    content = _GenerateContent(
        tmp_path,
        """\
        basics:
          name: Sam Taylor
          email: "sam+<b>@example.com"
        """,
    )

    assert '<a href="mailto:sam+&lt;b&gt;@example.com" alt="email address" target="_blank">' in content


# ----------------------------------------------------------------------
# |
# |  Unsafe Uris
# |
# ----------------------------------------------------------------------
def test_SafeUrisAreDisplayed(tmp_path: Path):
    """A uri that does not execute content when it is followed is displayed."""

    content = _GenerateContent(
        tmp_path,
        """\
        basics:
          name: Sam Taylor
          picture: photo.jpg
          website: https://example.com
        """,
    )

    assert '<img src="photo.jpg" alt="Picture of Sam Taylor">' in content
    assert '<a href="https://example.com" alt="website" target="_blank">https://example.com</a>' in content


# ----------------------------------------------------------------------
def test_UnsafePictureIsNotDisplayed(tmp_path: Path):
    expected = _Fragment(
        """\
        <div class="row title">
          <div class="col-3 section header picture">
            <div></div>
          </div>
          <div class="col section content name"><p>Sam Taylor</p></div>
        </div>
        """,
        2,
    )

    assert expected in _GenerateContent(tmp_path, UNSAFE_CONTENT)


# ----------------------------------------------------------------------
def test_UnsafeWebsiteIsNotDisplayed(tmp_path: Path):
    expected = _Fragment(
        """\
        <div class="row">
          <div class="detail col">
            <div class="icon">
              <i class="fas fa-lg fa-envelope"></i>
            </div>
            <div class="info email">
              <a href="mailto:sam@example.com" alt="email address" target="_blank">sam@example.com</a>
            </div>
          </div>
          <span></span>
          <span></span>
          <span></span>
        </div>
        """,
        5,
    )

    assert expected in _GenerateContent(tmp_path, UNSAFE_CONTENT)


# ----------------------------------------------------------------------
def test_UnsafeProfileIsDisplayedWithoutALink(tmp_path: Path):
    """The username remains visible when a profile's uri is not displayed."""

    expected = _Fragment(
        """\
        <div class="detail col">
          <div class="icon network">
            <a href="https://github.com/" aria-label="Link to GitHub" target="_blank">
              <i class="fa-lg fab fa-github"></i>
            </a>
          </div>
          <div class="info link">samtaylor</div>
        </div>
        """,
        6,
    )

    assert expected in _GenerateContent(tmp_path, UNSAFE_CONTENT)


# ----------------------------------------------------------------------
def test_UnsafeCompanyIsDisplayedWithoutALink(tmp_path: Path):
    """The company remains visible when its uri is not displayed."""

    expected = _Fragment(
        """\
        <div class="row line_item experience">
          <div class="col-3 subsection header">
            <div class="company">Contoso</div>
            <div class="startDate">June 2014</div>
            <div class="endDate">February 2019</div>
          </div>
          <div class="col subsection content">
            <div class="position">Engineer</div>
            <div class="summary"><p>Did work.</p></div>
          </div>
        </div>
        """,
        2,
    )

    assert expected in _GenerateContent(tmp_path, UNSAFE_CONTENT)


# ----------------------------------------------------------------------
def test_UnsafeUrisAreReported(tmp_path: Path):
    output_directory, output = _Generate(tmp_path, UNSAFE_CONTENT)

    for uri in UNSAFE_URIS:
        assert (
            f"WARNING: The uri '{uri}' is not safe to display and was not included in the generated content."
            in output
        )

    content = (output_directory / "index.html").read_text(encoding="utf-8")

    for uri in UNSAFE_URIS:
        assert uri not in content


# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "uri",
    [
        # A browser removes these characters before it follows the uri, so each of them is followed
        # as 'javascript:alert(1)'.
        r"java\tscript:alert(1)",
        r"java\nscript:alert(1)",
        r"java\rscript:alert(1)",
        r"java\0script:alert(1)",
        r"\x01javascript:alert(1)",
        r"javascript:alert(1)\t",
    ],
)
def test_UnsafeUriWithAnInsignificantCharacterIsNotDisplayed(tmp_path: Path, uri: str):
    """A scheme that embeds a character that a browser removes still executes content."""

    output_directory, output = _Generate(
        tmp_path,
        f"""\
        basics:
          name: Sam Taylor
          website: "{uri}"
        """,
    )

    assert "is not safe to display and was not included in the generated content." in output

    content = (output_directory / "index.html").read_text(encoding="utf-8")

    assert "script:alert(1)" not in content
    assert '<i class="fas fa-lg fa-link"></i>' not in content


# ----------------------------------------------------------------------
def test_SafeUriIsNormalized(tmp_path: Path):
    """A character that is significant within a uri is encoded rather than interpreted."""

    content = _GenerateContent(
        tmp_path,
        """\
        basics:
          name: Sam Taylor
          website: "https://example.com/my resume"
        """,
    )

    assert (
        '<a href="https://example.com/my%20resume" alt="website" target="_blank">https://example.com/my%20resume</a>'
        in content
    )


# ----------------------------------------------------------------------
def test_UnsafeUriWithinMarkdownIsNotDisplayed(tmp_path: Path):
    """Markdown links are validated by markdown-it rather than by the uris provided by the schema."""

    content = _GenerateContent(
        tmp_path,
        """\
        basics:
          name: Sam Taylor
          summary: See [my work](javascript:alert(1)).
        """,
    )

    assert '<div class="col section content"><p>See [my work](javascript:alert(1)).</p></div>' in content


# ----------------------------------------------------------------------
# |
# |  Css
# |
# ----------------------------------------------------------------------
def test_Css(tmp_path: Path):
    css_filename = tmp_path / "styles.css"
    css_filename.write_text(CSS, encoding="utf-8")

    output_directory, _ = _Generate(tmp_path, MINIMAL_CONTENT, css_filename)

    content = (output_directory / "index.html").read_text(encoding="utf-8")

    assert '  <link rel="stylesheet" href="styles.css" />\n' in content

    dest_css_filename = output_directory / "styles.css"

    assert dest_css_filename.read_text(encoding="utf-8") == CSS

    if _SymlinksAreSupported(tmp_path):
        assert dest_css_filename.is_symlink()
        # Windows returns the link target decorated with an extended-length path prefix
        assert dest_css_filename.resolve() == css_filename.resolve()


# ----------------------------------------------------------------------
def test_CssFilenameIsEncoded(tmp_path: Path):
    """Characters that are significant within a uri reference the file rather than a fragment."""

    css_filename = tmp_path / "sty&le#s.css"
    css_filename.write_text(CSS, encoding="utf-8")

    output_directory, _ = _Generate(tmp_path, MINIMAL_CONTENT, css_filename)

    content = (output_directory / "index.html").read_text(encoding="utf-8")

    assert '  <link rel="stylesheet" href="sty%26le%23s.css" />\n' in content


# ----------------------------------------------------------------------
def test_CssMayNotReplaceTheGeneratedHtml(tmp_path: Path):
    css_filename = tmp_path / "index.html"
    css_filename.write_text(CSS, encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="A stylesheet named 'index.html' would replace the generated html.",
    ):
        _Generate(tmp_path, MINIMAL_CONTENT, css_filename)

    # The generated html is not written when the stylesheet is rejected
    assert not (tmp_path / "output").exists()


# ----------------------------------------------------------------------
def test_CssWithinTheOutputDirIsNotReplaced(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A relative stylesheet that resolves to its destination is left as it is."""

    output_directory = tmp_path / "output"
    output_directory.mkdir()

    css_filename = output_directory / "styles.css"
    css_filename.write_text(CSS, encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    _Generate(tmp_path, MINIMAL_CONTENT, Path("output") / "styles.css")

    assert css_filename.read_text(encoding="utf-8") == CSS


# ----------------------------------------------------------------------
def test_ExistingCssIsReplaced(tmp_path: Path):
    css_filename = tmp_path / "styles.css"
    css_filename.write_text(CSS, encoding="utf-8")

    output_directory = tmp_path / "output"
    output_directory.mkdir()

    (output_directory / "styles.css").write_text("body { color: blue; }\n", encoding="utf-8")

    _Generate(tmp_path, MINIMAL_CONTENT, css_filename)

    assert (output_directory / "styles.css").read_text(encoding="utf-8") == CSS


# ----------------------------------------------------------------------
def test_CssIsCopiedWhenTheLinkCannotBeCreated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Creating a symbolic link on Windows requires developer mode or elevated privileges."""

    # ----------------------------------------------------------------------
    def SymlinkTo(*args, **kwargs) -> None:
        msg = "symbolic links are not supported"
        raise OSError(msg)

    # ----------------------------------------------------------------------

    monkeypatch.setattr(Path, "symlink_to", SymlinkTo)

    css_filename = tmp_path / "styles.css"
    css_filename.write_text(CSS, encoding="utf-8")

    output_directory, output = _Generate(tmp_path, MINIMAL_CONTENT, css_filename)

    dest_css_filename = output_directory / "styles.css"

    assert not dest_css_filename.is_symlink()
    assert dest_css_filename.read_text(encoding="utf-8") == CSS

    assert (
        "WARNING: The symbolic link could not be created (symbolic links are not supported); the file was copied instead."
        in output
    )
