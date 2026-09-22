"""Run these with:  python -m unittest

They start the real app on a spare port and make real HTTP requests, so if
these pass the app genuinely works.
"""

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from wsgiref.simple_server import WSGIRequestHandler, make_server

from app import db
from app.main import application


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0, application, handler_class=QuietHandler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        db._reset_for_tests()

    # -- helpers ----------------------------------------------------------

    def get(self, path):
        with urlopen(f"{self.base}{path}") as res:
            return res.status, res.read().decode()

    def post(self, path, fields):
        request = Request(
            f"{self.base}{path}",
            data=urlencode(fields).encode(),
            method="POST",
        )
        try:
            # Don't follow the redirect: we want to see the 303 itself.
            opener = urlopen(request)
            return opener.status
        except HTTPError as err:
            return err.code

    # -- tests ------------------------------------------------------------

    def test_healthz_answers_200(self):
        status, body = self.get("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok"})

    def test_home_page_renders(self):
        status, body = self.get("/")
        self.assertEqual(status, 200)
        self.assertIn("It works", body)

    def test_note_can_be_added_and_read_back(self):
        self.post("/notes", {"body": "a note from the tests"})
        _, body = self.get("/api/notes")
        bodies = [n["body"] for n in json.loads(body)]
        self.assertIn("a note from the tests", bodies)

    def test_html_in_a_note_is_escaped(self):
        self.post("/notes", {"body": "<script>alert(1)</script>"})
        _, page = self.get("/")
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_empty_note_is_rejected(self):
        self.post("/notes", {"body": "   "})
        _, body = self.get("/api/notes")
        self.assertEqual(json.loads(body), [])

    def test_oversized_body_gets_413(self):
        code = self.post("/notes", {"body": "A" * 40_000})
        self.assertEqual(code, 413)

    def test_unknown_path_gets_404(self):
        with self.assertRaises(HTTPError) as caught:
            self.get("/no-such-page")
        self.assertEqual(caught.exception.code, 404)

    def test_status_reports_no_database(self):
        _, body = self.get("/api/status")
        status = json.loads(body)
        self.assertEqual(status["app"], "ok")
        self.assertFalse(status["database"]["configured"])


if __name__ == "__main__":
    unittest.main()
