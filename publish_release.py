"""Публикует Windows-релиз в Supabase Storage.

Требуемые переменные окружения:
  SUPABASE_URL
  SUPABASE_SERVICE_ROLE_KEY

Файлы загружаются в bucket app-releases: сначала EXE, затем latest.json.
Секретный ключ не записывается в исходники и не выводится в лог.
"""
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUCKET = "app-releases"


def _storage_url(base_url: str, object_name: str) -> str:
    base = base_url.rstrip("/")
    parsed = urllib.parse.urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".supabase.co"):
        raise RuntimeError("SUPABASE_URL должен быть HTTPS-адресом проекта *.supabase.co")
    return f"{base}/storage/v1/object/{BUCKET}/{urllib.parse.quote(object_name, safe='')}"


def upload_file(base_url: str, service_key: str, path: Path, object_name: str, content_type: str):
    url = _storage_url(base_url, object_name)
    request = urllib.request.Request(
        url,
        data=path.read_bytes(),
        headers={
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
            "Content-Type": content_type,
            "x-upsert": "true",
            "Cache-Control": "no-cache" if object_name == "latest.json" else "public, max-age=31536000, immutable",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        if response.status not in (200, 201):
            raise RuntimeError(f"Supabase Storage вернул HTTP {response.status}")


def main():
    base_url = os.environ.get("SUPABASE_URL", "").strip()
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not base_url or not service_key:
        raise SystemExit("Задайте GitHub Secrets SUPABASE_URL и SUPABASE_SERVICE_ROLE_KEY.")

    manifest_path = ROOT / "release" / "latest.json"
    if not manifest_path.is_file():
        raise SystemExit("Не найден release/latest.json. Сначала выполните build_windows.bat.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(manifest.get("version", ""))
    installer = manifest.get("installer") or {}
    name = str(installer.get("name", ""))
    expected = f"RMRP-Pomoshnik-Setup-{version}.exe"
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or name != expected:
        raise SystemExit("Версия или имя установщика в latest.json некорректны.")
    tag = os.environ.get("GITHUB_REF_NAME", "")
    if tag.startswith("v") and tag[1:] != version:
        raise SystemExit(f"Тег {tag} не совпадает с версией приложения {version}.")

    installer_path = ROOT / "installer" / "output" / name
    if not installer_path.is_file():
        raise SystemExit(f"Не найден установщик: {installer_path}")
    if installer_path.stat().st_size != int(installer.get("size") or -1):
        raise SystemExit("Размер установщика не совпадает с latest.json.")
    digest = hashlib.sha256(installer_path.read_bytes()).hexdigest()
    if digest != str(installer.get("sha256", "")).lower():
        raise SystemExit("SHA-256 установщика не совпадает с latest.json.")

    # Публикуем бинарник первым. Манифест — только после успешной загрузки EXE.
    upload_file(base_url, service_key, installer_path, name, "application/vnd.microsoft.portable-executable")
    upload_file(base_url, service_key, manifest_path, "latest.json", "application/json")
    print(f"Релиз {version} опубликован в Supabase Storage.")


if __name__ == "__main__":
    main()
