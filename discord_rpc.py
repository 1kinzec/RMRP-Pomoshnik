"""Discord Rich Presence по локальному IPC (без внешних зависимостей).

Windows: именованный канал \\\\?\\pipe\\discord-ipc-N. Linux/macOS: unix-сокет discord-ipc-N.
Нужен Application ID приложения из https://discord.com/developers/applications
"""
import json
import os
import socket
import struct
import threading
import time
import uuid

OP_HANDSHAKE, OP_FRAME, OP_CLOSE, OP_PING, OP_PONG = 0, 1, 2, 3, 4


class _PipeConn:
    def __init__(self, f):
        self.f = f

    def send(self, data):
        self.f.write(data)
        self.f.flush()

    def recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.f.read(n - len(buf))
            if not chunk:
                raise ConnectionError("pipe closed")
            buf += chunk
        return buf

    def close(self):
        try:
            self.f.close()
        except Exception:  # noqa: BLE001
            pass


class _SockConn:
    def __init__(self, s):
        self.s = s

    def send(self, data):
        self.s.sendall(data)

    def recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.s.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed")
            buf += chunk
        return buf

    def close(self):
        try:
            self.s.close()
        except Exception:  # noqa: BLE001
            pass


def _candidates():
    if os.name == "nt":
        return [rf"\\?\pipe\discord-ipc-{i}" for i in range(10)]
    bases = [os.environ.get(k) for k in ("XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP")] + ["/tmp"]
    paths = []
    for b in bases:
        if b:
            paths += [os.path.join(b, f"discord-ipc-{i}") for i in range(10)]
    return paths


def _open(path):
    if os.name == "nt":
        return _PipeConn(open(path, "r+b", buffering=0))
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect(path)
    return _SockConn(s)


class DiscordRPC:
    """Фоновый клиент. Безопасен для вызова из GUI-потока: все сетевые операции идут в worker."""

    def __init__(self, candidates=None):
        self.client_id = ""
        self.enabled = False
        self.activity = None  # dict | None
        self.status = "Выключено"
        self.on_status = None
        self._candidates = candidates
        self._conn = None
        self._thread = None
        self._stop = threading.Event()
        self._dirty = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ публичное API
    def configure(self, client_id, enabled, activity=None):
        with self._lock:
            reconnect = (client_id or "") != self.client_id
            self.client_id = (client_id or "").strip()
            self.enabled = bool(enabled)
            self.activity = activity if enabled else None
            if reconnect:
                self._drop()
        if self.enabled and not self.client_id:
            self._set_status("Не указан Application ID")
        elif not self.enabled:
            self._set_status("Выключено")
        self._ensure_thread()
        self._dirty.set()

    def shutdown(self):
        self._stop.set()
        self._dirty.set()
        with self._lock:
            self._drop()

    # ------------------------------------------------------------------ внутреннее
    def _set_status(self, text):
        if text != self.status:
            self.status = text
            if self.on_status:
                try:
                    self.on_status(text)
                except Exception:  # noqa: BLE001
                    pass

    def _ensure_thread(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="discord-rpc")
        self._thread.start()

    def _drop(self):
        if self._conn:
            self._conn.close()
        self._conn = None

    def _frame(self, op, payload):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        return struct.pack("<II", op, len(data)) + data

    def _read_frame(self):
        op, length = struct.unpack("<II", self._conn.recv_exact(8))
        body = self._conn.recv_exact(length) if length else b""
        return op, (json.loads(body.decode("utf-8")) if body else {})

    def _connect(self):
        for path in (self._candidates or _candidates()):
            try:
                conn = _open(path)
            except OSError:
                continue
            try:
                self._conn = conn
                conn.send(self._frame(OP_HANDSHAKE, {"v": 1, "client_id": self.client_id}))
                op, data = self._read_frame()
                if op == OP_CLOSE or data.get("evt") == "ERROR":
                    self._drop()
                    self._set_status("Discord отклонил Application ID")
                    return False
                return True
            except Exception:  # noqa: BLE001
                self._drop()
        return False

    def _send_activity(self):
        act = self.activity
        payload = {"cmd": "SET_ACTIVITY", "nonce": str(uuid.uuid4()),
                   "args": {"pid": os.getpid(), "activity": act}}
        self._conn.send(self._frame(OP_FRAME, payload))
        _, resp = self._read_frame()
        if resp.get("evt") == "ERROR":
            raise ConnectionError((resp.get("data") or {}).get("message", "ошибка Discord"))

    def _run(self):
        while not self._stop.is_set():
            self._dirty.clear()
            try:
                with self._lock:
                    enabled, cid = self.enabled, self.client_id
                if not enabled or not cid:
                    if self._conn:
                        with self._lock:
                            try:  # снимаем статус, если был выставлен
                                self.activity = None
                                self._send_activity()
                            except Exception:  # noqa: BLE001
                                pass
                            self._drop()
                else:
                    fresh = False
                    if self._conn is None:
                        self._set_status("Подключение…")
                        if self._connect():
                            self._set_status("Подключено")
                            fresh = True
                        else:
                            if self.status == "Подключение…":
                                self._set_status("Discord не запущен")
                    if self._conn is not None and (fresh or self.activity is not None):
                        with self._lock:
                            self._send_activity()
            except Exception:  # noqa: BLE001
                with self._lock:
                    self._drop()
                if self.enabled:
                    self._set_status("Соединение потеряно")
            if self._stop.is_set():
                break
            self._dirty.wait(15 if self._conn else 8)
        self._drop()


def build_activity(details, state, start_ts=None, large_text="RMRP Помощник", large_image="rmrp"):
    act = {"details": details[:120], "state": state[:120]}
    if start_ts:
        act["timestamps"] = {"start": int(start_ts)}
    if large_image:
        act["assets"] = {"large_image": large_image, "large_text": large_text}
    return act
