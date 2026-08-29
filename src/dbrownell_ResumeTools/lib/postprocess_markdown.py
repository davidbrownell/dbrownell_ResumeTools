# noqa: D100
import hashlib
import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from dbrownell_Common.Streams.DoneManager import DoneManager


# ----------------------------------------------------------------------
POSTPROCESS_SENTINEL = "<PostprocessMarkdown: operation>"
POSTPROCESS_OPERATIONS = [
    "linebreak",
]


# ----------------------------------------------------------------------
def PostprocessMarkdown(
    dm: DoneManager,
    input_filename: Path,
    output_filename: Path | None,
) -> None:
    """Decorate markdown content to ensure that content is preserved as expected during the transformation process."""

    # ----------------------------------------------------------------------
    def CalculateHash(content: str) -> str:
        sha = hashlib.sha256()

        sha.update(content.encode("utf-8"))
        return sha.hexdigest()

    # ----------------------------------------------------------------------

    with dm.Nested("Reading content..."):
        content = input_filename.read_text(encoding="utf-8")
        original_hash = CalculateHash(content)

    with dm.Nested("Decorating content..."):
        # Turn POSTPROCESS_SENTINEL into a regex that matches the sentinel and any of the operations
        regex = re.compile(
            re.escape(POSTPROCESS_SENTINEL).replace(re.escape("operation"), r"(?P<operation>[^\s>]+)"),
        )

        # ----------------------------------------------------------------------
        def Sub(match: re.Match[str]) -> str:
            operation = match.group("operation")
            operation_lower = operation.lower()

            if operation_lower == "linebreak":
                return "  "

            msg = f"'{operation}' is not a recognized postprocess operation."
            raise ValueError(msg)

        # ----------------------------------------------------------------------

        content = regex.sub(Sub, content)

        new_hash = CalculateHash(content)

    if new_hash != original_hash:
        dm.WriteLine("Content was modified.")

        if output_filename is not None:
            with dm.Nested(f"Writing '{output_filename}'..."):
                output_filename.parent.mkdir(parents=True, exist_ok=True)
                output_filename.write_text(content, encoding="utf-8")
    else:
        dm.WriteLine("No changes were detected.")
