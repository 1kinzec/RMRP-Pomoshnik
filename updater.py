"""Автообновление RMRP Помощника через публичный манифест Supabase Storage.

Манифест latest.json содержит version, installer, sha256, size и notes.
Клиент не зависит от GitHub API или GitHub Releases.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

from .config import APP_VERSION, UPDATE_MANIFEST_URL

ALLOWED_HOSTS = ("supabase.co",)
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
    """Читает манифест с cache-busting, чтобы CDN не отдавал предыдущий релиз."""
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    query.append(("_rmrp_check", str(int(time.time()))))
    fresh_url = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urllib.parse.urlencode(query), parsed.fragment)
    )
    headers = dict(UA, Accept="application/json")
    headers["Cache-Control"] = "no-cache, no-store, max-age=0"
    headers["Pragma"] = "no-cache"
    req = urllib.request.Request(fresh_url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def can_self_update():
    return bool(getattr(sys, "frozen", False)) and os.name == "nt"


def check_manifest(manifest_url=None, current=None, fetch=None):
    """Проверяет latest.json и возвращает безопасные данные новой версии либо None."""
    manifest_url = manifest_url or UPDATE_MANIFEST_URL
    if not manifest_url or not host_ok(manifest_url):
        return None
    data = json.loads((fetch or _get)(manifest_url).decode("utf-8"))
    version = str(data.get("version", "")).strip().lstrip("vV")
    installer = data.get("installer") or {}
    name = str(installer.get("name", ""))
    url = str(installer.get("url", ""))
    sha256 = str(installer.get("sha256", "")).lower()
    size = int(installer.get("size") or 0)
    if not version or parse_version(version) <= parse_version(current or APP_VERSION):
        return None
    if not ASSET_RE.fullmatch(name) or not host_ok(url):
        return None
    if not re.fullmatch(r"[a-f0-9]{64}", sha256) or size <= 0:
        return None
    return {"version": version, "notes": str(data.get("notes") or ""), "name": name,
            "url": url, "size": size, "sha256": sha256,
            "page": str(data.get("release_page") or manifest_url)}


def check_latest(repo=None, current=None, fetch=None, manifest_url=None):
    """Совместимая точка входа: проверяет только собственный Supabase-манифест."""
    return check_manifest(manifest_url, current, fetch)


def download(info, dest_dir=None, progress=None, hosts=ALLOWED_HOSTS, require_https=True, opener=None):
    """Скачивает EXE, проверяет HTTPS-хост, размер и SHA-256 до запуска."""
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
    expected_sha = info.get("sha256")
    if expected_sha:
        if not re.fullmatch(r"[a-fA-F0-9]{64}", str(expected_sha)) or expected_sha.lower() != sha.hexdigest():
            os.remove(part)
            raise RuntimeError("Контрольная сумма не совпала — обновление отклонено.")
    elif info.get("sha_url"):
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
    flags = 0x00000008 | 0x00000200 if os.name == "nt" else 0
    subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS", "/NORESTART"], close_fds=True, creationflags=flags)
