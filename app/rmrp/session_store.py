"""Локальное хранилище сессии для автовхода «на этом компьютере».

Хранится только refresh-токен (не пароль). На Windows файл шифруется DPAPI: расшифровать его
может лишь тот же пользователь Windows на этом же компьютере, поэтому скопированный файл на другом ПК бесполезен.
На других системах (разработка/тесты) токен лежит в файле с правами 600.
"""
import base64
import json
import os
import sys
import threading
import time

_LOCK = threading.Lock()
_ENTROPY = b"RMRP-Pomoshnik-session-v1"


def _dpapi(data, protect):
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def to_blob(b):
        buf = ctypes.create_string_buffer(b, len(b))
        return Blob(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf

    src, _keep1 = to_blob(data)
    ent, _keep2 = to_blob(_ENTROPY)
    out = Blob()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    ok = fn(ctypes.byref(src), None, ctypes.byref(ent), None, None, 0, ctypes.byref(out))
    if not ok:
        raise OSError("DPAPI недоступен")
    try:
        return ctypes.string_at(out.pbData, out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out.pbData)


def _use_dpapi():
    return sys.platform == "win32"


def save(path, payload):
    """Сохраняет словарь сессии. Возвращает True при успехе."""
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        if _use_dpapi():
            mode, blob = "dpapi", _dpapi(raw, True)
        else:
            mode, blob = "plain", raw
        doc = {"v": 1, "mode": mode, "data": base64.b64encode(blob).decode("ascii"), "saved": int(time.time())}
        with _LOCK:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(doc, f)
            try:
                os.chmod(tmp, 0o600)
            except OSError:
                pass
            os.replace(tmp, path)
        return True
    except Exception:  # noqa: BLE001
        return False


def load(path):
    """Возвращает словарь сессии или None (нет файла, повреждён, другой компьютер/пользователь)."""
    try:
        with _LOCK:
            with open(path, "r", encoding="utf-8") as f:
                doc = json.load(f)
        blob = base64.b64decode(doc["data"])
        if doc.get("mode") == "dpapi":
            if not _use_dpapi():
                return None
            blob = _dpapi(blob, False)
        data = json.loads(blob.decode("utf-8"))
        return data if isinstance(data, dict) and data.get("refresh_token") else None
    except Exception:  # noqa: BLE001
        return None


def clear(path):
    with _LOCK:
        try:
            os.remove(path)
        except OSError:
            pass
