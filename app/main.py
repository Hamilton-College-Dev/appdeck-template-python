"""Your app starts here.

Two things the hosting platform depends on. Don't change them:
  1. The app listens on port 8080.
  2. GET /healthz answers with HTTP 200.
Everything else on this page is yours to rewrite.
"""

import json
import logging
import os

from . import db, views
from .router import BodyTooLargeError, Router, read_form

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("app")

routes = Router()


# ---------------------------------------------------------------------------
# Health check
#
# The platform calls this every few seconds to decide whether your app is
# alive. If it stops answering 200, your site stops receiving visitors.
#
# Note what it does NOT do: it doesn't touch the database. If it did, a
# two-second database hiccup would convince the platform your whole app was
# dead. Database health is reported separately, at /api/status.
# ---------------------------------------------------------------------------
@routes.get("/healthz")
def healthz(environ):
    return json_response(200, {"status": "ok"})


# ---------------------------------------------------------------------------
# Your routes
# ---------------------------------------------------------------------------

@routes.get("/")
def home(environ):
    return html_response(200, views.home(db.list_notes(), db.has_database()))


@routes.post("/notes")
def create_note(environ):
    form = read_form(environ)
    try:
        db.add_note(form.get("body"))
    except ValueError as err:
        log.warning("Rejected note: %s", err)
    return 303, [("Location", "/")], b""


@routes.get("/api/notes")
def api_notes(environ):
    return json_response(200, db.list_notes())


@routes.get("/api/status")
def api_status(environ):
    configured = db.has_database()
    reachable = None

    if configured:
        try:
            db.list_notes(1)
            reachable = True
        except Exception:
            reachable = False

    return json_response(200, {
        "app": "ok",
        "database": {"configured": configured, "reachable": reachable},
        "storage": "postgresql" if configured else "in-memory (resets on restart)",
    })


# ---------------------------------------------------------------------------
# Plumbing. You shouldn't need to touch anything below here.
# ---------------------------------------------------------------------------

def _default(value):
    """Lets json.dumps handle datetimes."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise TypeError(f"Not JSON serialisable: {type(value)}")


def json_response(status, data):
    body = json.dumps(data, indent=2, default=_default).encode("utf-8")
    return status, [("Content-Type", "application/json; charset=utf-8")], body


def html_response(status, markup):
    return status, [("Content-Type", "text/html; charset=utf-8")], markup.encode("utf-8")


STATUS_TEXT = {
    200: "200 OK",
    303: "303 See Other",
    404: "404 Not Found",
    413: "413 Payload Too Large",
    500: "500 Internal Server Error",
}


def application(environ, start_response):
    """The WSGI entry point. gunicorn calls this for every request."""
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")

    handler = routes.match(method, path)

    try:
        if handler is None:
            status, headers, body = html_response(404, views.not_found())
        else:
            status, headers, body = handler(environ)
    except BodyTooLargeError as err:
        log.warning("%s %s: %s", method, path, err)
        status, headers, body = html_response(413, views.too_large())
    except Exception:
        log.exception("%s %s failed", method, path)
        status, headers, body = html_response(500, views.server_error())

    headers = list(headers) + [
        ("Content-Length", str(len(body))),
        ("X-Content-Type-Options", "nosniff"),
    ]
    start_response(STATUS_TEXT.get(status, f"{status} "), headers)
    return [body]


# Set up the database once, when the worker process starts.
try:
    db.init()
    log.info("Database connected." if db.has_database()
             else "No DATABASE_URL set. Using in-memory storage.")
except Exception as err:
    # Deliberately not fatal. Pages still render and /healthz still answers
    # 200, so the site stays up while the database sorts itself out.
    log.error("Database setup failed, continuing without it: %s", err)


if __name__ == "__main__":
    # A plain development server, for running on your own computer.
    # Production uses gunicorn instead (see the Dockerfile).
    from wsgiref.simple_server import make_server

    port = int(os.environ.get("PORT", 8080))
    log.info("Listening on http://0.0.0.0:%s", port)
    make_server("0.0.0.0", port, application).serve_forever()
