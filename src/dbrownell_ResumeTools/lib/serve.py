# noqa: D100
import functools
import os
import threading
import time
import webbrowser

from contextlib import contextmanager
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from dbrownell_Common.Streams.DoneManager import DoneManager


# ----------------------------------------------------------------------
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8000

# The path requested by the browser to indicate that it is still displaying the content; requesting
# content is not sufficient, as the content is displayed long after it has been requested.
KEEPALIVE_PATH = "/__keepalive__"

# How often the browser indicates that it is still displaying the content and how long the content
# continues to be served once those indications stop arriving.
KEEPALIVE_INTERVAL_SECONDS = 1.0
KEEPALIVE_TIMEOUT_SECONDS = 5.0

# How long a launched browser has to display the content before it is considered closed.
BROWSER_LAUNCH_TIMEOUT_SECONDS = 30.0


# ----------------------------------------------------------------------
def CreateServer(
    directory: Path,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    log_func: Callable[[str], None] | None = None,
    keepalive_func: Callable[[], None] | None = None,
) -> ThreadingHTTPServer:
    """Create the http server that serves the content within `directory`.

    A `port` of 0 causes an available port to be selected; the port that was selected is available
    via the server's `server_address`.

    When `keepalive_func` is provided, the html that is served is augmented with a script that
    periodically requests `KEEPALIVE_PATH`; `keepalive_func` is invoked for each of those requests.
    """

    return ThreadingHTTPServer(
        (host, port),
        functools.partial(
            _RequestHandler,
            directory=str(directory),
            log_func=log_func,
            keepalive_func=keepalive_func,
        ),
    )


# ----------------------------------------------------------------------
def Serve(
    dm: DoneManager,
    directory: Path,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    launch_browser: bool = False,
) -> None:
    """Serve the content within `directory` over http.

    The content is served until the process is interrupted or, when `launch_browser` is True, until
    the browser that was launched to display the content is closed.
    """

    with dm.Nested(f"Serving '{directory}'...") as serve_dm:
        # Requests are served by multiple threads, so writes to the terminal must be serialized.
        write_lock = threading.Lock()

        # ----------------------------------------------------------------------
        def Flush() -> None:
            # The content is served until the process is interrupted, so everything that is written is
            # flushed to ensure that it is displayed even when the output is redirected.
            with serve_dm.YieldStream() as stream:
                stream.flush()

        # ----------------------------------------------------------------------
        def Log(message: str) -> None:
            with write_lock:
                serve_dm.WriteVerbose(f"{message}\n")
                Flush()

        # ----------------------------------------------------------------------

        session = _BrowserSession() if launch_browser else None

        with CreateServer(
            directory,
            host,
            port,
            Log,
            None if session is None else session.Touch,
        ) as httpd:
            url = f"http://{host}:{httpd.server_address[1]}"
            instructions = "Close the browser or press Ctrl+C" if session is not None else "Press Ctrl+C"

            serve_dm.WriteLine(f"{url}\n\n{instructions} to stop serving the content.\n")

            Flush()

            try:
                if session is None:
                    httpd.serve_forever()
                else:
                    with session.Monitor(httpd):
                        if not webbrowser.open(url):
                            serve_dm.WriteWarning(
                                "The browser could not be launched.\n",
                                update_result=False,
                            )

                        httpd.serve_forever()
            except KeyboardInterrupt:
                pass

            serve_dm.WriteLine("\nThe content is no longer being served.\n")


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------

# The script embedded within the html that is served; a browser only requests content once, so this
# is the only way to know that the browser is still displaying it.
_KEEPALIVE_SCRIPT = (
    "<script>\n"
    f'  setInterval(() => fetch("{KEEPALIVE_PATH}"), {int(KEEPALIVE_INTERVAL_SECONDS * 1000)});\n'
    "</script>\n"
).encode()


# ----------------------------------------------------------------------
class _BrowserSession:
    """Stops the server once the browser that displays the content is closed.

    The browser is considered closed once it stops indicating that it is still displaying the
    content.
    """

    # ----------------------------------------------------------------------
    def __init__(self) -> None:
        # The deadline is modified while the monitor waits for it to elapse, so those modifications
        # must be observed by the monitor as they are made.
        self._condition = threading.Condition()
        self._deadline = 0.0
        self._stopped = False

    # ----------------------------------------------------------------------
    def Touch(self) -> None:
        """Indicate that the browser is still displaying the content."""

        with self._condition:
            self._deadline = time.monotonic() + KEEPALIVE_TIMEOUT_SECONDS
            self._condition.notify()

    # ----------------------------------------------------------------------
    @contextmanager
    def Monitor(self, httpd: ThreadingHTTPServer) -> Iterator[None]:
        """Shut `httpd` down once the browser is closed."""

        with self._condition:
            # The browser has yet to display the content, so it is given additional time to launch.
            self._deadline = time.monotonic() + BROWSER_LAUNCH_TIMEOUT_SECONDS

        thread = threading.Thread(target=self._Monitor, args=(httpd,), daemon=True)
        thread.start()

        try:
            yield
        finally:
            with self._condition:
                self._stopped = True
                self._condition.notify()

            thread.join()

    # ----------------------------------------------------------------------
    def _Monitor(self, httpd: ThreadingHTTPServer) -> None:
        with self._condition:
            while not self._stopped:
                remaining = self._deadline - time.monotonic()

                if remaining <= 0:
                    break

                self._condition.wait(remaining)

            stopped = self._stopped

        if not stopped:
            httpd.shutdown()


# ----------------------------------------------------------------------
class _RequestHandler(SimpleHTTPRequestHandler):
    """Request handler that serves static content and writes its output to a `DoneManager`."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        *args,
        log_func: Callable[[str], None] | None = None,
        keepalive_func: Callable[[], None] | None = None,
        **kwargs,
    ) -> None:
        self._log_func = log_func
        self._keepalive_func = keepalive_func

        super().__init__(*args, **kwargs)

    # ----------------------------------------------------------------------
    def do_GET(self) -> None:
        """Serve keepalive requests and html augmented with the keepalive script."""

        if self._keepalive_func is None:
            super().do_GET()
            return

        if self.path == KEEPALIVE_PATH:
            self._keepalive_func()

            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return

        content = self._CreateAugmentedContent()

        if content is None:
            super().do_GET()
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()

        self.wfile.write(content)

    # ----------------------------------------------------------------------
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        """Write request information to the `DoneManager` rather than to `sys.stderr`."""

        if self._log_func is not None:
            self._log_func(f"[{self.address_string()}] {format % args}")

    # ----------------------------------------------------------------------
    def end_headers(self) -> None:
        """Prevent the browser from caching content that is regenerated between runs."""

        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    # ----------------------------------------------------------------------
    def _CreateAugmentedContent(self) -> bytes | None:
        """Return the requested html with the keepalive script embedded within it (if applicable)."""

        path = self.translate_path(self.path)

        if path.endswith(("/", os.sep)):
            path += "index.html"

        filename = Path(path)

        if filename.suffix.lower() not in (".htm", ".html") or not filename.is_file():
            return None

        content = filename.read_bytes()

        if b"</body>" in content:
            return content.replace(b"</body>", _KEEPALIVE_SCRIPT + b"</body>", 1)

        return content + _KEEPALIVE_SCRIPT
