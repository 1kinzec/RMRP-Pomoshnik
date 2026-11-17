"""Готовит latest.json для публикации релиза в Supabase Storage.

Использование после build_windows.bat:
  python installer/prepare_release.py --notes-file RELEASE_NOTES.md
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Подготовка манифеста обновлений RMRP")
    parser.add_argument("--notes-file", default="RELEASE_NOTES.md")
    parser.add_argument("--base-url", default="https://cyihqnquxaxnonjbshm.supabase.co/storage/v1/object/public/app-releases")
    args = parser.parse_args()

    version_text = (ROOT / "app/rmrp/version.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)', version_text)
    if not match:
        raise SystemExit("Не удалось определить версию приложения")
    version = match.group(1)
    installer = ROOT / "installer/output" / f"RMRP-Pomoshnik-Setup-{version}.exe"
    if not installer.is_file():
        raise SystemExit(f"Не найден установщик: {installer}\nСначала запустите build_windows.bat")

    digest = hashlib.sha256()
    with installer.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    notes_path = ROOT / args.notes_file
    notes = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""
    base_url = args.base_url.rstrip("/")
    manifest = {
        "version": version,
        "published_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "notes": notes,
        "installer": {
            "name": installer.name,
            "url": f"{base_url}/{installer.name}",
            "size": installer.stat().st_size,
            "sha256": digest.hexdigest(),
        },
        "release_page": base_url,
    }
    out = ROOT / "release" / "latest.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Манифест создан: {out}")
    print(f"Версия: {version}; размер: {installer.stat().st_size:,} байт; SHA-256: {digest.hexdigest()}")
    print("Загрузите EXE и latest.json в публичный bucket app-releases (EXE сначала, latest.json последним).")


if __name__ == "__main__":
    main()
