import json
import os
import sys
import unittest
import urllib.error
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from rmrp import api  # noqa: E402


class Resp:
    def __init__(self, body=b"{}"):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ApiTest(unittest.TestCase):
    def test_restore_session_rotates_and_notifies(self):
        db = api.Supabase()
        seen = []
        db.on_tokens = seen.append
        payload = {"access_token": "A2", "refresh_token": "R2", "user": {"id": "u1"}}
        with mock.patch("urllib.request.urlopen", return_value=Resp(json.dumps(payload).encode())) as op:
            db.restore_session("R1")
        req = op.call_args[0][0]
        self.assertIn("grant_type=refresh_token", req.full_url)
        self.assertEqual(json.loads(req.data), {"refresh_token": "R1"})
        self.assertEqual((db.access_token, db.refresh_token, db.user["id"]), ("A2", "R2", "u1"))
        self.assertEqual(seen, ["R2"])

    def test_logout_clears_saved_session(self):
        db = api.Supabase()
        seen = []
        db.on_tokens = seen.append
        db.access_token, db.refresh_token = "A", "R"
        with mock.patch("urllib.request.urlopen", return_value=Resp(b"")):
            db.auth_logout()
        self.assertEqual(seen, [None])
        self.assertIsNone(db.refresh_token)

    def test_restore_failure_is_apierror(self):
        db = api.Supabase()
        err = urllib.error.HTTPError("u", 400, "bad", {}, None)
        err.read = lambda: b'{"error_description":"Invalid Refresh Token"}'
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(api.ApiError) as cm:
                db.restore_session("old")
        self.assertEqual(cm.exception.status, 400)

    def test_offline_has_status_zero(self):
        db = api.Supabase()
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            with self.assertRaises(api.ApiError) as cm:
                db.restore_session("r")
        self.assertEqual(cm.exception.status, 0)

    def test_upload_sends_raw_bytes_with_auth(self):
        db = api.Supabase()
        db.access_token = "TOKEN"
        with mock.patch("urllib.request.urlopen", return_value=Resp(b'{"Key":"k"}')) as op:
            url = db.upload_object("memo-images", "u1/a b.jpg", b"\xff\xd8data", "image/jpeg")
        req = op.call_args[0][0]
        self.assertTrue(req.full_url.endswith("/storage/v1/object/memo-images/u1/a%20b.jpg"))
        self.assertEqual(req.data, b"\xff\xd8data")
        self.assertEqual(req.get_method(), "POST")
        h = {k.lower(): v for k, v in req.header_items()}
        self.assertEqual(h["content-type"], "image/jpeg")
        self.assertEqual(h["authorization"], "Bearer TOKEN")
        self.assertIn("/storage/v1/object/public/memo-images/u1/a%20b.jpg", url)

    def test_delete_objects_body(self):
        db = api.Supabase()
        db.access_token = "T"
        with mock.patch("urllib.request.urlopen", return_value=Resp(b"[]")) as op:
            db.delete_objects("memo-images", ["u1/a.jpg", "u1/b.jpg"])
            db.delete_objects("memo-images", [])  # пустой список — без запроса
        self.assertEqual(op.call_count, 1)
        req = op.call_args[0][0]
        self.assertEqual(req.get_method(), "DELETE")
        self.assertEqual(json.loads(req.data), {"prefixes": ["u1/a.jpg", "u1/b.jpg"]})

    def test_jwt_expired_triggers_single_refresh_and_retry(self):
        db = api.Supabase()
        db.access_token, db.refresh_token = "OLD", "R"
        expired = urllib.error.HTTPError("u", 401, "x", {}, None)
        expired.read = lambda: b'{"message":"JWT expired"}'
        calls = []

        def fake(req, timeout=None):
            calls.append(req.full_url)
            if "grant_type=refresh_token" in req.full_url:
                return Resp(b'{"access_token":"NEW","refresh_token":"R2"}')
            if len([c for c in calls if "rest/v1" in c]) == 1:
                raise expired
            self.assertEqual(req.get_header("Authorization"), "Bearer NEW")
            return Resp(b"[]")
        with mock.patch("urllib.request.urlopen", side_effect=fake):
            self.assertEqual(db.table("laws"), [])
        self.assertEqual(db.refresh_token, "R2")


if __name__ == "__main__":
    unittest.main()
