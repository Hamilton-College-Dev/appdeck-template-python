"""A very small WSGI router.

You register a method and a path, and it hands back the matching handler.
That is all it does.

This app speaks WSGI, which is the standard interface every Python web server
understands. That means if you later decide you want Flask or another
framework, it drops straight in: point gunicorn at your Flask app instead of
this one and everything else keeps working.
"""

from html import escape as escape_html  # noqa: F401  (re-exported for views)
from urllib.parse import parse_qs


class Router:
    def __init__(self):
        self._routes = {}

    def add(self, method, path, handler):
        self._routes[(method, path)] = handler
        return self

    def get(self, path):
        """Use as a decorator: @routes.get("/about")"""
        def decorate(handler):
            self.add("GET", path, handler)
            return handler
        return decorate

    def post(self, path):
        def decorate(handler):
            self.add("POST", path, handler)
            return handler
        return decorate

    def match(self, method, path):
        return self._routes.get((method, path))


class BodyTooLargeError(Exception):
    """Raised when a request body is over the limit."""


def read_form(environ, limit_bytes=16 * 1024):
    """Read an HTML form submission into a plain dict.

    Stops reading past the limit so a huge upload can't exhaust memory.
    """
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0

    if length > limit_bytes:
        raise BodyTooLargeError(f"Request body larger than {limit_bytes} bytes")

    if length <= 0:
        return {}

    raw = environ["wsgi.input"].read(length).decode("utf-8", errors="replace")
    return {key: values[0] for key, values in parse_qs(raw).items()}
