"""Автообновление через GitHub Releases: проверка версии, скачивание с проверкой SHA-256, запуск установщика.

Логика без GUI (тестируется отдельно). Работает с публичным репозиторием; у приватного релизы
без токена не читаются — тогда проверка просто молча ничего не находит.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

from .config import APP_VERSION, GITHUB_REPO

ALLOWED_HOSTS = ("github.com", "githubusercontent.com")
ASSET_RE = re.compile(r"RMRP-Pomoshnik-Setup-.*\.exe")
UA = {"User-Agent": f"RMRP-Pomoshnik/{APP_VERSION}"}


def parse_version(text):
    nums = re.findall(r"\d+", str(text))
    return tuple(int(x) for x in nums[:4]) or (0,)


def host_ok(url, hosts=ALLOWED_HOSTS, require_https=True):
    u = urllib.parse.urlparse(url)
    if require_https and u.scheme != "https":
        return False
    h = (u.hostname or "").lower()
    return any(h == x or h.endswith("." + x) for x in hosts)


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers=dict(UA, Accept="application/vnd.github+json"))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def can_self_update():
    return bool(getattr(sys, "frozen", False)) and os.name == "nt"


def check_latest(repo=None, current=None, fetch=None):
    """Возвращает dict с данными новой версии или None, если обновления нет / репозиторий не задан."""
    repo = repo if repo is not None else GITHUB_REPO
    if not repo:
        return None
    data = json.loads((fetch or _get)(f"https://api.github.com/repos/{repo}/releases/latest").decode("utf-8"))
    if data.get("draft") or data.get("prerelease"):
        return None
    version = str(data.get("tag_name", "")).lstrip("vV")
    if parse_version(version) <= parse_version(current or APP_VERSION):
        return None
    assets = data.get("assets") or []
    asset = next((a for a in assets if ASSET_RE.fullmatch(a.get("name", ""))), None)
    if not asset:
        return None
    sha = next((a for a in assets if a.get("name") == asset["name"] + ".sha256"), None)
    return {"version": version, "notes": data.get("body") or "", "name": asset["name"], "url": asset["browser_download_url"],
            "size": int(asset.get("size") or 0), "sha_url": sha["browser_download_url"] if sha else None,
            "page": data.get("html_url") or f"https://github.com/{repo}/releases"}


def download(info, dest_dir=None, progress=None, hosts=ALLOWED_HOSTS, require_https=True, opener=None):
    """Скачивает установщик. Проверяет хост, размер и SHA-256 (если в релизе есть .sha256). Возвращает путь к файлу."""
    if not host_ok(info["url"], hosts, require_https):
        raise RuntimeError("Недопустимый адрес загрузки обновления.")
    opener = opener or urllib.request.urlopen
    dest_dir = dest_dir or tempfile.mkdtemp(prefix="rmrp_update_")
    path = os.path.join(dest_dir, os.path.basename(info["name"]))
    part = path + ".part"
    sha = hashlib.sha256()
    done = 0
    with opener(urllib.request.Request(info["url"], headers=UA), timeout=30) as r, open(part, "wb") as f:
        total = int(r.headers.get("Content-Length") or info.get("size") or 0)
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            sha.update(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    if info.get("size") and done != info["size"]:
        os.remove(part)
        raise RuntimeError("Файл обновления скачался не полностью.")
    if info.get("sha_url"):
        if not host_ok(info["sha_url"], hosts, require_https):
            os.remove(part)
            raise RuntimeError("Недопустимый адрес контрольной суммы.")
        with opener(urllib.request.Request(info["sha_url"], headers=UA), timeout=20) as r:
            expected = r.read().decode("utf-8", "ignore").strip().split()[0].lower()
        if expected != sha.hexdigest():
            os.remove(part)
            raise RuntimeError("Контрольная сумма не совпала — обновление отклонено.")
    os.replace(part, path)
    return path


def launch_installer(path):
    """Запускает установщик в тихом режиме; приложение после этого должно закрыться."""
    flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS", "/NORESTART"], close_fds=True, creationflags=flags)
