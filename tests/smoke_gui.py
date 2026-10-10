"""Дымовой тест интерфейса без Tk: подставляет заглушку tkinter и фейковую БД, обходит все страницы.

Запуск: python3 -I tests/smoke_gui.py   (ловит NameError/KeyError/неверные вызовы в логике страниц)
Не заменяет проверку на реальном Windows — только логику.
"""
import os
import sys
import threading
import time
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app"))


# ----------------------------------------------------------------------------- заглушка tkinter
class W:
    def __init__(self, *a, **k):
        self._opts = dict(k)
        self.master = a[0] if a and isinstance(a[0], W) else None
        self._children = []
        if self.master is not None:
            self.master._children.append(self)

    def __getitem__(self, k):
        return self._opts.get(k, "#101010")

    def __setitem__(self, k, v):
        self._opts[k] = v

    def keys(self):
        return list(self._opts)

    def cget(self, k):
        return self._opts.get(k, "#101010")

    def configure(self, *a, **k):
        self._opts.update(k)

    config = configure

    def winfo_children(self):
        return list(self._children)

    def destroy(self):
        if self.master is not None and self in self.master._children:
            self.master._children.remove(self)

    def winfo_exists(self):
        return 1

    def winfo_width(self):
        return 800

    winfo_height = winfo_reqwidth = winfo_reqheight = winfo_screenwidth = winfo_screenheight = winfo_rootx = winfo_rooty = winfo_x = winfo_y = winfo_width

    def winfo_pointerxy(self):
        return (0, 0)

    def winfo_containing(self, x, y):
        return None

    def winfo_ismapped(self):
        return True

    def winfo_id(self):
        return 1

    def after(self, ms, fn=None, *a):
        if fn and ms == 0:
            fn(*a)
        return "id"

    def after_cancel(self, i):
        pass

    def search(self, *a, **k):
        return ""

    def curselection(self):
        return ()

    def selection(self):
        return ()

    def get_children(self, *a):
        return ()

    def state(self, *a):
        return "normal"

    def current(self, i=None):
        return 0

    def bbox(self, *a):
        return None

    def __getattr__(self, name):
        if name.startswith("create_"):
            return lambda *a, **k: 1
        return lambda *a, **k: None


class Var:
    def __init__(self, master=None, value=None, **k):
        self.v = "" if value is None else value

    def get(self):
        return self.v

    def set(self, v):
        self.v = v

    def trace_add(self, *a):
        pass


class Font:
    def __init__(self, **k):
        pass

    def measure(self, t):
        return len(t) * 7


tk = types.ModuleType("tkinter")
for n in ("Tk", "Toplevel", "Frame", "Canvas", "Label", "Entry", "Text", "Listbox", "Checkbutton", "Scale", "Misc"):
    setattr(tk, n, type(n, (W,), {}))
tk.StringVar = tk.BooleanVar = tk.IntVar = Var
tk.TclError = type("TclError", (Exception,), {})
ttk = types.ModuleType("tkinter.ttk")
for n in ("Style", "Treeview", "Combobox", "Scrollbar", "Progressbar", "Notebook"):
    setattr(ttk, n, type(n, (W,), {}))
fnt = types.ModuleType("tkinter.font")
fnt.Font = Font
tk.ttk, tk.font = ttk, fnt
sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk, "tkinter.font": fnt})


# ----------------------------------------------------------------------------- фейковая БД
class FakeDB:
    access_token = "t"

    def __init__(self):
        self.calls = []
        self.data = {
            "laws": [{"id": 1, "name": "Уголовный Кодекс", "short_name": "УК РФ", "law_number": "УК РФ", "description": "d", "source_url": "http://x", "is_active": True,
                      "created_at": "2026-01-01T00:00:00+00:00", "updated_at": "2026-01-02T00:00:00+00:00"},
                     {"id": 2, "name": "ФЗ О полиции", "short_name": "ФЗ «О полиции»", "law_number": "74-ФЗ", "is_active": True}],
            "law_stats": [{"law_id": 1, "articles": 3, "chapters": 2}],
            "law_articles": [
                {"id": 10, "law_id": 1, "article_number": "12", "title": "Принципы", "chapter": "Глава 1. Общие", "position": 1, "content": "Принципы законности и гуманизма в отношении лиц."},
                {"id": 11, "law_id": 1, "article_number": "319", "title": "Оскорбление представителя власти", "chapter": "Глава 2. Власть", "position": 2,
                 "content": "Публичное оскорбление представителя власти наказывается штрафом до 40 000 рублей."}],
            "favorites": [], "article_views": [{"viewed_at": "2026-01-01T00:00:00+00:00", "law_articles": {"id": 10, "law_id": 1, "article_number": "12", "title": "T", "laws": {"short_name": "УК РФ"}}}],
            "announcements": [{"id": 1, "title": "Обновление", "content": "Текст", "type": "UPDATE", "created_at": "2026-01-01T00:00:00+00:00", "is_active": True}],
            "tests": [{"id": 1, "title": "УК РФ", "category": "УК", "description": "", "difficulty": "MEDIUM", "question_count": 1, "is_active": True}],
            "questions": [{"id": 1, "question": "Q?", "answer_a": "a", "answer_b": "b", "answer_c": "c", "answer_d": "d", "correct_answer": "A", "explanation": "e"}],
            "test_results": [{"test_id": 1, "score": 80, "correct_answers": 4, "total_questions": 5, "completed_at": "2026-01-01T00:00:00+00:00", "tests": {"title": "УК"}}],
            "profiles": [{"id": "u1", "username": "kinzec", "display_name": "Kinzec", "role": "FOUNDER", "status": "ACTIVE", "premium": True, "allow_pranks": True,
                          "created_at": "2026-01-01T00:00:00+00:00", "last_seen_at": "2026-10-10T00:00:00+00:00"},
                         {"id": "u2", "username": "alex", "display_name": "Alex", "role": "USER", "status": "ACTIVE", "premium": False, "allow_pranks": True}],
            "reports": [{"id": 1, "reason": "R", "description": "D", "status": "NEW", "created_at": "2026-01-01T00:00:00+00:00", "author": {"username": "alex"}, "target": None}],
            "audit_logs": [{"created_at": "2026-01-01T00:00:00+00:00", "action": "A", "target_type": "t", "target_id": "1", "profiles": {"username": "kinzec"}}],
            "search_history": [{"query": "статья 12", "created_at": "2026-01-01T00:00:00+00:00"}],
            "ai_history": [{"question": "q", "answer": "a", "created_at": "2026-01-01T00:00:00+00:00", "law_article_id": 1}],
            "app_settings": [], "law_versions": [{"version": "1", "change_description": "d", "created_at": "2026-01-01T00:00:00+00:00"}],
            "test_favorites": [], "prank_events": [],
        }

    def table(self, name, select="*", filters=None, order=None, limit=None, offset=None):
        self.calls.append(("table", name, filters))
        rows = list(self.data.get(name, []))
        for k, v in (filters or {}).items():
            if k == "or" or not isinstance(v, str) or not v.startswith("eq."):
                continue
            want = v[3:]
            rows = [r for r in rows if str(r.get(k)) == want] if any(k in r for r in rows) else rows
        return rows[:limit] if limit else rows

    def table_all(self, name, select="*", filters=None, order=None, max_rows=0):
        return self.table(name, select, filters, order)

    def insert(self, name, rows, select="*", upsert_on=None, ignore_duplicates=False):
        self.calls.append(("insert", name, rows))
        rows = rows if isinstance(rows, list) else [rows]
        return [dict(r, id=99) for r in rows]

    def update(self, name, filters, values, select="*"):
        self.calls.append(("update", name, values))
        return [values]

    def delete(self, name, filters):
        self.calls.append(("delete", name, filters))
        return {}

    def rpc(self, fn, payload=None):
        return "a@b.c"

    def auth_logout(self):
        pass


def wait_threads():
    for _ in range(40):
        time.sleep(0.05)
        if threading.active_count() <= 1:
            break
    time.sleep(0.1)


def main():
    import tempfile
    os.environ["APPDATA"] = tempfile.mkdtemp()
    from rmrp.app import App
    errors = []
    app = App()
    app.db = FakeDB()
    orig = app.notify

    def notify(title, message="", kind="info", duration=None):
        if kind == "error":
            errors.append((title, message))
    app.notify = notify
    app.show_login()
    app.show_login("register")
    app.do_guest()
    app.user = {"id": "u1", "email": "k@x.y"}
    app.prof = dict(app.db.data["profiles"][0], bio="")
    app.guest = False
    app.show_main()
    pages = [("home", {}), ("laws", {}), ("law", {"law_id": 1}), ("law", {"law_id": 1, "article_id": 11, "highlight": ["оскорблен"]}), ("search", {}), ("search", {"q": "статья 12"}),
             ("ai", {}), ("ai", {"preset": "Что грозит за оскорбление?"}), ("tests", {}), ("favorites", {}), ("history", {}), ("reports", {}), ("profile", {}), ("settings", {}),
             ("admin", {}), ("admin", {"section": "users"}), ("admin", {"section": "roles"}), ("admin", {"section": "reports"}), ("admin", {"section": "tests"}),
             ("admin", {"section": "laws"}), ("admin", {"section": "ann"}), ("admin", {"section": "audit"}), ("admin", {"section": "screamer"})]
    for key, kw in pages:
        app.navigate(key, **kw)
        wait_threads()
    # прохождение теста и разбор результата
    app.start_test(app.db.data["tests"][0])
    wait_threads()
    qs = app.db.data["questions"]
    app._finish_test(app.db.data["tests"][0], qs, {1: "B"})
    wait_threads()
    # поиск, помощник, статья-ссылка
    rows = app.search_articles("оскорбление власти", 5)
    assert rows and rows[0]["article_number"] == "319", rows
    rows = app.search_articles("статья 12", 5)
    assert rows and rows[0]["article_number"] == "12", rows
    ans, src = app._compose("наказание за оскорбление", app.search_articles("наказание за оскорбление", 5))
    assert "штраф" in ans and src, ans
    ans, src = app._compose("zzzz", [])
    assert "не буду придумывать" in ans
    app.show_screamer()
    app.discord_dialog()
    app.sync_laws()
    wait_threads()
    app.add_law_dialog()
    app.create_report()
    app.add_test()
    app.add_announcement()
    app.overlay.show()
    app.logout()
    wait_threads()
    if errors:
        print("ОШИБКИ:")
        for e in errors:
            print("  ", e)
        sys.exit(1)
    print("OK: страницы обработаны без ошибок:", len(pages), "+ диалоги")


if __name__ == "__main__":
    main()
