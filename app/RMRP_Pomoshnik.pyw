"""Точка входа RMRP Помощник 2.0."""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from rmrp.app import App
    App().mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        try:
            from rmrp.config import settings_dir
            d = settings_dir()
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "crash.log"), "a", encoding="utf-8") as f:
                f.write(traceback.format_exc() + "\n")
        except Exception:  # noqa: BLE001
            pass
        raise
