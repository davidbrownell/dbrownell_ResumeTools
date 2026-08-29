# noqa: D100
import tempfile

from pathlib import Path
from typing import Annotated
from urllib.parse import unquote, urlparse
from urllib.request import urlopen

import typer

from lessish import Lessish
from typer.core import TyperGroup

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags

from dbrownell_ResumeTools.lib.generate_html import GenerateHtml as GenerateHtmlImpl
from dbrownell_ResumeTools.lib.postprocess_markdown import PostprocessMarkdown as PostprocessMarkdownImpl
from dbrownell_ResumeTools.lib.serve import DEFAULT_HOST, DEFAULT_PORT, Serve as ServeImpl


# ----------------------------------------------------------------------
class NaturalOrderGrouper(TyperGroup):  # noqa: D101
    # ----------------------------------------------------------------------
    def list_commands(self, *args, **kwargs) -> list[str]:  # noqa: ARG002, D102
        return list(self.commands.keys())  # pragma: no cover


# ----------------------------------------------------------------------
app = typer.Typer(
    cls=NaturalOrderGrouper,
    help=__doc__,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=False,
)


# ----------------------------------------------------------------------
@app.command("GenerateHtml", no_args_is_help=True)
def GenerateHtml(
    content_filename: Annotated[
        Path,
        typer.Argument(
            help="Path to the JSON resume content to render.",
            dir_okay=False,
            exists=True,
            resolve_path=True,
        ),
    ],
    style_filename: Annotated[
        str,
        typer.Argument(
            help="Path or url to the css or less stylesheet referenced by the generated html; less content is compiled to css.",
        ),
    ],
    output_directory: Annotated[
        Path | None,
        typer.Argument(
            help="Directory populated with the generated html; a temporary directory that is removed once the process exits is used when not provided.",
            file_okay=False,
            resolve_path=True,
        ),
    ] = None,
    serve: Annotated[  # noqa: FBT002
        bool,
        typer.Option(
            "--serve",
            help="Serve the generated html over http until the process is interrupted.",
        ),
    ] = False,
    browser: Annotated[  # noqa: FBT002
        bool,
        typer.Option(
            "--browser",
            help="Launch a browser that displays the served content; the content is served until that browser is closed. May only be specified when '--serve' is specified.",
        ),
    ] = False,
    host: Annotated[
        str,
        typer.Option("--host", help="Host name used when '--serve' is specified."),
    ] = DEFAULT_HOST,
    port: Annotated[
        int | None,
        typer.Option(
            "--port",
            min=0,
            max=65535,
            help=f"Port used when '--serve' is specified; 0 selects any available port. Defaults to {DEFAULT_PORT} or, when '--browser' is specified, any available port.",
        ),
    ] = None,
    verbose: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--verbose", help="Write verbose information to the terminal."),
    ] = False,
    debug: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--debug", help="Write debug information to the terminal."),
    ] = False,
) -> None:
    """Postprocess the content's markdown and generate html based on the results."""

    if browser and not serve:
        msg = "'--browser' may only be specified when '--serve' is specified."
        raise typer.BadParameter(msg)

    # The style is validated here rather than by typer, as typer validates a value that is a
    # filename or a url as one or the other but not as either.
    style = _ResolveStyle(style_filename)

    if port is None:
        # A launched browser is directed to the port that was selected, so there is no reason to
        # require that a specific port is available.
        port = 0 if browser else DEFAULT_PORT

    with (
        DoneManager.CreateCommandLine(
            flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
        ) as dm,
        tempfile.TemporaryDirectory() as temp_directory,
    ):
        if output_directory is None:
            # The generated content is only available for the lifetime of the process, which is
            # sufficient when it is served rather than kept.
            output_directory = Path(temp_directory) / "output"

        postprocessed_filename = Path(temp_directory) / content_filename.name

        with dm.Nested("Postprocessing content...") as postprocess_dm:
            PostprocessMarkdownImpl(postprocess_dm, content_filename, postprocessed_filename)

            # The postprocessed content is only written when the content was modified; the original
            # content is used when no modifications were necessary.
            if not postprocessed_filename.is_file():
                postprocessed_filename = content_filename

        if isinstance(style, str):
            with dm.Nested(f"Downloading '{style}'..."):
                style_path = _Download(style, Path(temp_directory))
        else:
            style_path = style

        if style_path.suffix.lower() == _LESS_EXTENSION:
            with dm.Nested(f"Compiling '{style_path}'..."):
                style_path = _CompileLess(style_path, output_directory)
        elif isinstance(style, str):
            # Downloaded content is written to the output directory so that the generated content
            # continues to reference a stylesheet that is available once the process exits.
            style_path = _WriteStylesheet(
                style_path.read_text(encoding="utf-8"),
                style_path.name,
                output_directory,
            )

        with dm.Nested("Generating html...") as generate_dm:
            GenerateHtmlImpl(generate_dm, postprocessed_filename, output_directory, style_path)

        # The content is not served when errors were encountered while generating it.
        if serve and dm.result >= 0:
            dm.WriteLine("")
            ServeImpl(dm, output_directory, host, port, launch_browser=browser)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
_CSS_EXTENSION = ".css"
_LESS_EXTENSION = ".less"

# Schemes that identify a style as content to download; everything else (including a windows drive
# letter, which parses as a scheme) is a filename.
_URL_SCHEMES = frozenset(["http", "https"])

_DOWNLOAD_TIMEOUT_SECONDS = 30


# ----------------------------------------------------------------------
def _ResolveStyle(value: str) -> str | Path:
    """Return `value` as the url that it is or as the existing file that it names."""

    if urlparse(value).scheme in _URL_SCHEMES:
        # The url names the file written to the output directory, so it must name a stylesheet.
        if Path(unquote(urlparse(value).path)).suffix.lower() not in [_CSS_EXTENSION, _LESS_EXTENSION]:
            msg = f"'{value}' does not reference a css or less stylesheet."
            raise typer.BadParameter(msg)

        return value

    filename = Path(value).resolve()

    if not filename.is_file():
        msg = f"'{value}' is not a file or a url."
        raise typer.BadParameter(msg)

    return filename


# ----------------------------------------------------------------------
def _Download(url: str, output_directory: Path) -> Path:
    """Download style content to a file within `output_directory` named after the url."""

    # The scheme was validated when the style was resolved.
    with urlopen(url, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:  # noqa: S310
        content = response.read().decode("utf-8")

    output_directory.mkdir(parents=True, exist_ok=True)
    output_filename = output_directory / Path(unquote(urlparse(url).path)).name

    output_filename.write_text(content, encoding="utf-8")

    return output_filename


# ----------------------------------------------------------------------
def _WriteStylesheet(content: str, name: str, output_directory: Path) -> Path:
    """Write stylesheet content to `name` within `output_directory`."""

    output_directory.mkdir(parents=True, exist_ok=True)
    output_filename = output_directory / name

    # A link left behind when a css stylesheet was previously generated is removed rather than
    # written through, as writing through it would overwrite the stylesheet that it references.
    if output_filename.is_symlink():
        output_filename.unlink()

    output_filename.write_text(content, encoding="utf-8")

    return output_filename


# ----------------------------------------------------------------------
def _CompileLess(filename: Path, output_directory: Path) -> Path:
    """Compile less content into a css file within `output_directory`.

    The result is written to the output directory rather than to a temporary one so that the
    generated content continues to reference a stylesheet that is available once the process exits.
    """

    return _WriteStylesheet(
        # `filename` is provided so that '@import' statements are resolved relative to the less content.
        Lessish().compile(filename.read_text(encoding="utf-8"), filename=str(filename)),
        filename.with_suffix(_CSS_EXTENSION).name,
        output_directory,
    )


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()  # pragma: no cover
