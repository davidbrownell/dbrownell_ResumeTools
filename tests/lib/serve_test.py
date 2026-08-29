"""Unit tests for lib/serve.py."""

import io
import threading

from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags

from dbrownell_ResumeTools.lib import serve as serve_mod
from dbrownell_ResumeTools.lib.serve import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    KEEPALIVE_PATH,
    CreateServer,
    Serve,
)


# ----------------------------------------------------------------------
# |
# |  Helpers
# |
# ----------------------------------------------------------------------
CONTENT = "<html><body>Sam Taylor</body></html>\n"

# The content as it is served when a `keepalive_func` is provided.
KEEPALIVE_SCRIPT = f'<script>\n  setInterval(() => fetch("{KEEPALIVE_PATH}"), 1000);\n</script>\n'
AUGMENTED_CONTENT = CONTENT.replace("</body>", f"{KEEPALIVE_SCRIPT}</body>")


# ----------------------------------------------------------------------
def _CreateContent(tmp_path: Path) -> Path:
    """Populate a directory with the content to serve."""

    directory = tmp_path / "html"
    directory.mkdir()

    # The content is written as bytes so that the line endings are not translated on Windows
    (directory / "index.html").write_bytes(CONTENT.encode("utf-8"))

    return directory


# ----------------------------------------------------------------------
def _Get(url: str) -> tuple[str, dict[str, str]]:
    """Return the content and headers associated with `url`."""

    with urlopen(url) as response:  # noqa: S310
        return response.read().decode("utf-8"), dict(response.headers)


# ----------------------------------------------------------------------
class _ServerContext:
    """Serve content on a background thread for the duration of the context."""

    # ----------------------------------------------------------------------
    def __init__(self, directory: Path, **kwargs: Any) -> None:
        self._httpd = CreateServer(directory, port=0, **kwargs)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    # ----------------------------------------------------------------------
    def __enter__(self) -> str:
        self._thread.start()
        return f"http://{DEFAULT_HOST}:{self._httpd.server_address[1]}"

    # ----------------------------------------------------------------------
    def __exit__(self, *args) -> None:
        self._httpd.shutdown()
        self._thread.join()
        self._httpd.server_close()


# ----------------------------------------------------------------------
# |
# |  Constants
# |
# ----------------------------------------------------------------------
def test_Defaults():
    assert DEFAULT_HOST == "localhost"
    assert DEFAULT_PORT == 8000
    assert KEEPALIVE_PATH == "/__keepalive__"


# ----------------------------------------------------------------------
# |
# |  CreateServer
# |
# ----------------------------------------------------------------------
def test_ServesContent(tmp_path: Path):
    with _ServerContext(_CreateContent(tmp_path)) as url:
        content, headers = _Get(f"{url}/index.html")

        assert content == CONTENT
        assert headers["Cache-Control"] == "no-store, must-revalidate"

        # The index is served when the directory itself is requested
        assert _Get(f"{url}/")[0] == CONTENT


# ----------------------------------------------------------------------
def test_ContentThatDoesNotExist(tmp_path: Path):
    with _ServerContext(_CreateContent(tmp_path)) as url, pytest.raises(HTTPError) as exc_info:
        _Get(f"{url}/does_not_exist.html")

    assert exc_info.value.code == 404


# ----------------------------------------------------------------------
def test_RequestsAreLogged(tmp_path: Path):
    messages: list[str] = []
    lock = threading.Lock()

    # ----------------------------------------------------------------------
    def Log(message: str) -> None:
        with lock:
            messages.append(message)

    # ----------------------------------------------------------------------

    with _ServerContext(_CreateContent(tmp_path), log_func=Log) as url:
        _Get(f"{url}/index.html")

    assert any("index.html" in message for message in messages)


# ----------------------------------------------------------------------
def test_RequestsAreNotLoggedWithoutLogFunc(tmp_path: Path, capsys: pytest.CaptureFixture):
    with _ServerContext(_CreateContent(tmp_path)) as url:
        _Get(f"{url}/index.html")

    assert "index.html" not in capsys.readouterr().err


# ----------------------------------------------------------------------
# |
# |  Keepalive
# |
# ----------------------------------------------------------------------
def test_KeepaliveRequests(tmp_path: Path):
    """A keepalive request invokes `keepalive_func` and is not associated with any content."""

    invocations: list[int] = []

    with _ServerContext(
        _CreateContent(tmp_path),
        keepalive_func=lambda: invocations.append(1),
    ) as url:
        with urlopen(f"{url}{KEEPALIVE_PATH}") as response:  # noqa: S310
            assert response.status == 204
            assert response.read() == b""

        assert invocations == [1]


# ----------------------------------------------------------------------
def test_HtmlIsAugmented(tmp_path: Path):
    """Html is augmented with the script that produces keepalive requests."""

    with _ServerContext(_CreateContent(tmp_path), keepalive_func=lambda: None) as url:
        assert _Get(f"{url}/index.html")[0] == AUGMENTED_CONTENT

        # The index is augmented when the directory itself is requested
        assert _Get(f"{url}/")[0] == AUGMENTED_CONTENT


# ----------------------------------------------------------------------
def test_HtmlWithoutBodyIsAugmented(tmp_path: Path):
    """The script is appended to html that is not associated with a body."""

    directory = _CreateContent(tmp_path)
    (directory / "fragment.html").write_bytes(b"<p>Sam Taylor</p>\n")

    with _ServerContext(directory, keepalive_func=lambda: None) as url:
        assert _Get(f"{url}/fragment.html")[0] == f"<p>Sam Taylor</p>\n{KEEPALIVE_SCRIPT}"


# ----------------------------------------------------------------------
def test_NonHtmlIsNotAugmented(tmp_path: Path):
    directory = _CreateContent(tmp_path)
    (directory / "styles.css").write_bytes(b"body { color: red; }\n")

    with _ServerContext(directory, keepalive_func=lambda: None) as url:
        assert _Get(f"{url}/styles.css")[0] == "body { color: red; }\n"


# ----------------------------------------------------------------------
def test_AugmentedContentThatDoesNotExist(tmp_path: Path):
    with (
        _ServerContext(_CreateContent(tmp_path), keepalive_func=lambda: None) as url,
        pytest.raises(HTTPError) as exc_info,
    ):
        _Get(f"{url}/does_not_exist.html")

    assert exc_info.value.code == 404


# ----------------------------------------------------------------------
# |
# |  Serve
# |
# ----------------------------------------------------------------------
def test_Serve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`Serve` displays the url that is being served and returns when interrupted."""

    directory = _CreateContent(tmp_path)
    arguments: dict[str, Any] = {}

    # ----------------------------------------------------------------------
    class MockServer:
        server_address = ("localhost", 1234)

        # ----------------------------------------------------------------------
        def __enter__(self) -> "MockServer":
            return self

        # ----------------------------------------------------------------------
        def __exit__(self, *args) -> None:
            pass

        # ----------------------------------------------------------------------
        def serve_forever(self) -> None:
            arguments["log_func"]("GET /index.html")
            raise KeyboardInterrupt

    # ----------------------------------------------------------------------
    def CreateServerMock(
        mock_directory: Path,
        host: str,
        port: int,
        log_func,  # noqa: ANN001
        keepalive_func,  # noqa: ANN001
    ) -> MockServer:
        arguments.update(
            {
                "directory": mock_directory,
                "host": host,
                "port": port,
                "log_func": log_func,
                "keepalive_func": keepalive_func,
            },
        )

        return MockServer()

    # ----------------------------------------------------------------------

    monkeypatch.setattr(serve_mod, "CreateServer", CreateServerMock)

    sink = io.StringIO()

    with DoneManager.Create(sink, "Testing...", flags=DoneManagerFlags.Create(verbose=True)) as dm:
        Serve(dm, directory, "example.com", 8080)

    assert arguments["directory"] == directory
    assert arguments["host"] == "example.com"
    assert arguments["port"] == 8080

    # Keepalive requests are only honored when a browser is launched
    assert arguments["keepalive_func"] is None

    output = sink.getvalue()

    assert f"Serving '{directory}'..." in output

    # The port reported is the one selected by the server rather than the one requested
    assert f"http://example.com:{MockServer.server_address[1]}" in output

    assert "Press Ctrl+C to stop serving the content." in output

    # The request that was logged is displayed as verbose output
    assert "GET /index.html" in output

    assert "no longer being served" in output


# ----------------------------------------------------------------------
def test_ServeLaunchesBrowser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The content is served until the browser that was launched stops requesting keepalives."""

    monkeypatch.setattr(serve_mod, "KEEPALIVE_TIMEOUT_SECONDS", 0.25)

    urls: list[str] = []

    # ----------------------------------------------------------------------
    def Open(url: str) -> bool:
        urls.append(url)

        # The request is made on another thread, as the content is not served until `Serve` begins
        # serving it.
        threading.Thread(target=_Get, args=(f"{url}{KEEPALIVE_PATH}",), daemon=True).start()

        return True

    # ----------------------------------------------------------------------

    monkeypatch.setattr(serve_mod.webbrowser, "open", Open)

    sink = io.StringIO()

    with DoneManager.Create(sink, "Testing...") as dm:
        Serve(dm, _CreateContent(tmp_path), port=0, launch_browser=True)

    output = sink.getvalue()

    assert len(urls) == 1
    assert urls[0] in output
    assert "Close the browser or press Ctrl+C to stop serving the content." in output
    assert "no longer being served" in output


# ----------------------------------------------------------------------
def test_ServeBrowserThatCannotBeLaunched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The content is no longer served once a browser that was never launched is expected to display it."""

    monkeypatch.setattr(serve_mod, "BROWSER_LAUNCH_TIMEOUT_SECONDS", 0.25)
    monkeypatch.setattr(serve_mod.webbrowser, "open", lambda url: False)  # noqa: ARG005

    sink = io.StringIO()

    with DoneManager.Create(sink, "Testing...") as dm:
        Serve(dm, _CreateContent(tmp_path), port=0, launch_browser=True)

    output = sink.getvalue()

    assert "The browser could not be launched." in output
    assert "no longer being served" in output
