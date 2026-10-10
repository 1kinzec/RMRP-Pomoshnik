import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from rmrp import updater  # noqa: E402


def release(tag="v2.1.0", assets=None, **kw):
    base = {"tag_name": tag, "body": "Заметки", "html_url": "https://github.com/o/r/releases/tag/" + tag, "assets": assets if assets is not None else [
        {"name": f"RMRP-Pomoshnik-Setup-{tag.lstrip('v')}.exe", "browser_download_url": "https://github.com/o/r/releases/download/x/setup.exe", "size": 10},
        {"name": f"RMRP-Pomoshnik-Setup-{tag.lstrip('v')}.exe.sha256", "browser_download_url": "https://github.com/o/r/releases/download/x/setup.exe.sha256", "size": 70}]}
    base.update(kw)
    return json.dumps(base).encode()


class VersionTests(unittest.TestCase):
    def test_parse(self):
        self.assertGreater(updater.parse_version("2.10.0"), updater.parse_version("2.9.9"))
        self.assertGreater(updater.parse_version("v2.0.1"), updater.parse_version("2.0.0"))
        self.assertEqual(updater.parse_version("abc"), (0,))

    def test_newer_found(self):
        info = updater.check_latest("o/r", "2.0.1", lambda url: release())
        self.assertEqual(info["version"], "2.1.0")
        self.assertTrue(info["sha_url"])
        self.assertTrue(info["name"].endswith(".exe"))

    def test_same_or_older_ignored(self):
        self.assertIsNone(updater.check_latest("o/r", "2.1.0", lambda url: release()))
        self.assertIsNone(updater.check_latest("o/r", "3.0.0", lambda url: release()))

    def test_no_repo_no_asset_draft(self):
        self.assertIsNone(updater.check_latest("", "1.0", lambda url: release()))
        self.assertIsNone(updater.check_latest("o/r", "1.0", lambda url: release(assets=[])))
        self.assertIsNone(updater.check_latest("o/r", "1.0", lambda url: release(prerelease=True)))
        self.assertIsNone(updater.check_latest("o/r", "1.0", lambda url: release(draft=True)))

    def test_host_allowlist(self):
        self.assertTrue(updater.host_ok("https://github.com/a/b"))
        self.assertTrue(updater.host_ok("https://objects.githubusercontent.com/x"))
        self.assertFalse(updater.host_ok("http://github.com/a"))
        self.assertFalse(updater.host_ok("https://evilgithub.com/a"))
        self.assertFalse(updater.host_ok("https://github.com.evil.io/a"))


class Handler(http.server.BaseHTTPRequestHandler):
    payload = b"MZ-fake-installer-bytes"
    sha = hashlib.sha256(payload).hexdigest()

    def do_GET(self):
        body = self.payload if self.path.endswith(".exe") else (self.sha + "  setup.exe\n").encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def info(self, **kw):
        d = {"name": "RMRP-Pomoshnik-Setup-9.9.9.exe", "url": self.base + "/setup.exe", "sha_url": self.base + "/setup.exe.sha256", "size": len(Handler.payload)}
        d.update(kw)
        return d

    def run_dl(self, info, **kw):
        return updater.download(info, tempfile.mkdtemp(), hosts=("127.0.0.1",), require_https=False, **kw)

    def test_ok_with_progress(self):
        seen = []
        path = self.run_dl(self.info(), progress=lambda d, t: seen.append((d, t)))
        self.assertEqual(open(path, "rb").read(), Handler.payload)
        self.assertEqual(seen[-1][0], len(Handler.payload))

    def test_bad_hash_rejected(self):
        orig = Handler.sha
        Handler.sha = "0" * 64
        try:
            with self.assertRaisesRegex(RuntimeError, "Контрольная сумма"):
                self.run_dl(self.info())
        finally:
            Handler.sha = orig

    def test_wrong_size_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "не полностью"):
            self.run_dl(self.info(size=999))

    def test_foreign_host_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "Недопустимый"):
            updater.download(self.info(url="https://evil.example/setup.exe"), tempfile.mkdtemp())


if __name__ == "__main__":
    unittest.main()
