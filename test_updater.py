import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from rmrp import updater  # noqa: E402


class VersionTests(unittest.TestCase):
    def manifest(self, version="3.1.0", **installer_overrides):
        payload = b"fake setup"
        installer = {
            "name": f"RMRP-Pomoshnik-Setup-{version}.exe",
            "url": f"https://cyihqnquxaxnonjbshm.supabase.co/storage/v1/object/public/app-releases/RMRP-Pomoshnik-Setup-{version}.exe",
            "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest(),
        }
        installer.update(installer_overrides)
        return json.dumps({"version": version, "notes": "Обновление", "installer": installer}).encode("utf-8")

    def test_parse(self):
        self.assertGreater(updater.parse_version("3.10.0"), updater.parse_version("3.9.9"))
        self.assertGreater(updater.parse_version("v3.0.1"), updater.parse_version("3.0.0"))
        self.assertEqual(updater.parse_version("abc"), (0,))

    def test_supabase_manifest(self):
        url = "https://cyihqnquxaxnonjbshm.supabase.co/storage/v1/object/public/app-releases/latest.json"
        raw = self.manifest()
        info = updater.check_latest(current="3.0.1", fetch=lambda _: raw, manifest_url=url)
        self.assertEqual(info["version"], "3.1.0")
        self.assertTrue(info["sha256"])
        self.assertIsNone(updater.check_latest(current="3.1.0", fetch=lambda _: raw, manifest_url=url))
        self.assertIsNone(updater.check_latest(current="3.0.1", fetch=lambda _: raw, manifest_url="https://evil.example/latest.json"))

    def test_manifest_rejects_invalid_metadata(self):
        url = "https://cyihqnquxaxnonjbshm.supabase.co/latest.json"
        bad_hash = self.manifest(sha256="not-a-hash")
        self.assertIsNone(updater.check_manifest(url, "3.0.0", lambda _: bad_hash))
        bad_name = self.manifest(name="malware.exe")
        self.assertIsNone(updater.check_manifest(url, "3.0.0", lambda _: bad_name))

    def test_host_allowlist(self):
        self.assertTrue(updater.host_ok("https://cyihqnquxaxnonjbshm.supabase.co/storage/file"))
        self.assertFalse(updater.host_ok("http://cyihqnquxaxnonjbshm.supabase.co/file"))
        self.assertFalse(updater.host_ok("https://evil-supabase.co/file"))
        self.assertFalse(updater.host_ok("https://supabase.co.evil.io/file"))


class ManifestCacheTests(unittest.TestCase):
    def test_manifest_request_bypasses_cdn_cache(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"{}"
        with patch("urllib.request.urlopen", return_value=response) as opened:
            updater._get("https://cyihqnquxaxnonjbshm.supabase.co/latest.json")
        request = opened.call_args.args[0]
        parsed = __import__("urllib.parse", fromlist=["urlsplit"]).urlsplit(request.full_url)
        query = __import__("urllib.parse", fromlist=["parse_qs"]).parse_qs(parsed.query)
        self.assertIn("_rmrp_check", query)
        self.assertEqual(request.get_header("Cache-control"), "no-cache, no-store, max-age=0")


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

    def test_manifest_rejects_bad_hash(self):
        with self.assertRaisesRegex(RuntimeError, "Контрольная сумма"):
            self.run_dl(self.info(sha256="0" * 64))

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
