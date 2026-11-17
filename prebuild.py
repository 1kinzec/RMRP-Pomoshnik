"""Читает версию приложения для локальной сборки Windows."""
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
VERSION_PY = os.path.join(ROOT, "app", "rmrp", "version.py")


def main(argv):
    if len(argv) >= 2 and argv[1] == "version":
        with open(VERSION_PY, encoding="utf-8") as f:
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)', f.read())
        if not match:
            sys.exit("Не удалось прочитать версию из version.py")
        print(match.group(1))
        return
    sys.exit("Использование: python installer/prebuild.py version")


if __name__ == "__main__":
    main(sys.argv)
