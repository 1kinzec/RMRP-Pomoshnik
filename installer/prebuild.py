"""Вспомогательный скрипт для build_windows.bat.

  python installer/prebuild.py version        -> печатает версию из app/rmrp/version.py
  python installer/prebuild.py repo owner/rep -> пишет app/rmrp/build_info.py (адрес репозитория для автообновления)
"""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
VERSION_PY = os.path.join(ROOT, "app", "rmrp", "version.py")
BUILD_INFO = os.path.join(ROOT, "app", "rmrp", "build_info.py")


def read_version():
    with open(VERSION_PY, encoding="utf-8") as f:
        m = re.search(r'"([^"]+)"', f.read())
    if not m:
        sys.exit("Не удалось прочитать версию из version.py")
    return m.group(1)


def main(argv):
    if len(argv) >= 2 and argv[1] == "version":
        print(read_version())
    elif len(argv) >= 3 and argv[1] == "repo":
        repo = argv[2].strip()
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            sys.exit("Репозиторий нужно указать как владелец/репозиторий")
        with open(BUILD_INFO, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"GITHUB_REPO = '{repo}'\n")
        print("build_info.py:", repo)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
