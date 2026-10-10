import json
import os
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from rmrp.discord_rpc import DiscordRPC, build_activity  # noqa: E402


class FakeDiscord(threading.Thread):
    def __init__(self, path):
        super().__init__(daemon=True)
        self.path = path
        self.received = []
        self.srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.srv.bind(path)
        self.srv.listen(1)

    def _read(self, c):
        hdr = b""
        while len(hdr) < 8:
            d = c.recv(8 - len(hdr))
            if not d:
                return None
            hdr += d
        op, ln = struct.unpack("<II", hdr)
        body = b""
        while len(body) < ln:
            body += c.recv(ln - len(body))
        return op, json.loads(body)

    def _send(self, c, op, obj):
        data = json.dumps(obj).encode()
        c.sendall(struct.pack("<II", op, len(data)) + data)

    def run(self):
        c, _ = self.srv.accept()
        while True:
            m = self._read(c)
            if m is None:
                break
            op, obj = m
            self.received.append((op, obj))
            if op == 0:
                self._send(c, 1, {"cmd": "DISPATCH", "evt": "READY", "data": {}})
            else:
                self._send(c, 1, {"cmd": obj.get("cmd"), "evt": None, "data": {}, "nonce": obj.get("nonce")})


class RpcTests(unittest.TestCase):
    def test_handshake_and_activity(self):
        d = tempfile.mkdtemp()
        path = os.path.join(d, "ipc")
        srv = FakeDiscord(path)
        srv.start()
        statuses = []
        rpc = DiscordRPC(candidates=[path])
        rpc.on_status = statuses.append
        rpc.configure("123456789", True, build_activity("Изучает ФЗ «О полиции»", "Статья 12", 1700000000))
        for _ in range(50):
            if len(srv.received) >= 2:
                break
            time.sleep(0.1)
        rpc.shutdown()
        self.assertEqual(srv.received[0][0], 0)
        self.assertEqual(srv.received[0][1]["client_id"], "123456789")
        act = srv.received[1][1]["args"]["activity"]
        self.assertEqual(srv.received[1][1]["cmd"], "SET_ACTIVITY")
        self.assertEqual(act["details"], "Изучает ФЗ «О полиции»")
        self.assertEqual(act["timestamps"]["start"], 1700000000)
        self.assertIn("Подключено", statuses)

    def test_no_discord_is_graceful(self):
        rpc = DiscordRPC(candidates=["/nonexistent/ipc"])
        rpc.configure("1", True, build_activity("a", "b"))
        time.sleep(0.5)
        self.assertEqual(rpc.status, "Discord не запущен")
        rpc.shutdown()

    def test_missing_client_id(self):
        rpc = DiscordRPC(candidates=[])
        rpc.configure("", True, None)
        self.assertEqual(rpc.status, "Не указан Application ID")
        rpc.shutdown()


if __name__ == "__main__":
    unittest.main()
