import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from rmrp import session_store as S  # noqa: E402


class SessionStoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "sub", "session.dat")

    def test_roundtrip(self):
        self.assertTrue(S.save(self.path, {"refresh_token": "abc", "user_id": "u1"}))
        self.assertEqual(S.load(self.path), {"refresh_token": "abc", "user_id": "u1"})

    def test_overwrite_keeps_latest_rotated_token(self):
        S.save(self.path, {"refresh_token": "one"})
        S.save(self.path, {"refresh_token": "two"})
        self.assertEqual(S.load(self.path)["refresh_token"], "two")

    def test_clear_and_missing(self):
        self.assertIsNone(S.load(self.path))
        S.save(self.path, {"refresh_token": "x"})
        S.clear(self.path)
        self.assertIsNone(S.load(self.path))
        S.clear(self.path)  # повторный сброс не падает

    def test_corrupt_file_is_ignored(self):
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as f:
            f.write("{не json")
        self.assertIsNone(S.load(self.path))

    def test_no_token_means_no_session(self):
        S.save(self.path, {"user_id": "u1"})
        self.assertIsNone(S.load(self.path))

    def test_dpapi_file_is_not_readable_off_windows(self):
        import base64
        import json
        os.makedirs(os.path.dirname(self.path))
        with open(self.path, "w") as f:
            json.dump({"v": 1, "mode": "dpapi", "data": base64.b64encode(b"x").decode()}, f)
        if sys.platform != "win32":
            self.assertIsNone(S.load(self.path))

    def test_token_not_stored_in_clear_on_windows_mode(self):
        S.save(self.path, {"refresh_token": "SECRET-TOKEN"})
        raw = open(self.path, encoding="utf-8").read()
        if sys.platform == "win32":
            self.assertNotIn("SECRET-TOKEN", raw)


if __name__ == "__main__":
    unittest.main()
