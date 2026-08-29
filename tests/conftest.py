"""Test configuration shared by all tests."""

import os

# `typer.rich_utils` reads these when it is imported, so they must be set before any test module
# imports typer.
#
# GitHub Actions runners define `GITHUB_ACTIONS`, which typer treats as a request to force terminal
# output. Rich then renders help and error text with ansi escape sequences embedded within option
# names (`--serve` becomes `\x1b[1;36m-\x1b[0m\x1b[1;36m-serve\x1b[0m`) and wraps messages to the
# width of the terminal, neither of which survives a literal comparison against the output.
os.environ["_TYPER_FORCE_DISABLE_TERMINAL"] = "1"
os.environ["TERMINAL_WIDTH"] = "200"
