# noqa: D100
from pathlib import Path  # noqa: TC003
from typing import Annotated

import typer

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags
from typer.core import TyperGroup

from dbrownell_ResumeTools.lib.postprocess_markdown import PostprocessMarkdown as PostprocessMarkdownImpl


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
@app.command("PostprocessMarkdown", no_args_is_help=True)
def PostprocessMarkdown(
    filename: Annotated[
        Path,
        typer.Argument(
            help="Path to the decorated markdown file to postprocess.",
            dir_okay=False,
            exists=True,
            resolve_path=True,
        ),
    ],
    output_filename: Annotated[
        Path | None,
        typer.Argument(
            help="Path to the undecorated markdown file to write.", dir_okay=False, resolve_path=True
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
    """Decorate markdown content to ensure that vertical whitespace is preserved during the transformation process."""

    with DoneManager.CreateCommandLine(
        flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
    ) as dm:
        PostprocessMarkdownImpl(dm, filename, output_filename)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()  # pragma: no cover
