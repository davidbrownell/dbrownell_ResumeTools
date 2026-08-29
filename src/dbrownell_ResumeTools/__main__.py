# noqa: D100
import tempfile

from pathlib import Path
from typing import Annotated

import typer

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags
from typer.core import TyperGroup

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
    css_filename: Annotated[
        Path,
        typer.Argument(
            help="Path to the stylesheet referenced by the generated html.",
            dir_okay=False,
            exists=True,
            resolve_path=True,
        ),
    ],
    output_directory: Annotated[
        Path,
        typer.Argument(
            help="Directory populated with the generated html.",
            file_okay=False,
            resolve_path=True,
        ),
    ],
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
        postprocessed_filename = Path(temp_directory) / content_filename.name

        with dm.Nested("Postprocessing content...") as postprocess_dm:
            PostprocessMarkdownImpl(postprocess_dm, content_filename, postprocessed_filename)

            # The postprocessed content is only written when the content was modified; the original
            # content is used when no modifications were necessary.
            if not postprocessed_filename.is_file():
                postprocessed_filename = content_filename

        with dm.Nested("Generating html...") as generate_dm:
            GenerateHtmlImpl(generate_dm, postprocessed_filename, output_directory, css_filename)

        # The content is not served when errors were encountered while generating it.
        if serve and dm.result >= 0:
            dm.WriteLine("")
            ServeImpl(dm, output_directory, host, port, launch_browser=browser)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()  # pragma: no cover
