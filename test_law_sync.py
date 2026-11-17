import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from rmrp.pages_laws import LawPages  # noqa: E402
from rmrp.pages_ai import AiPages  # noqa: E402


class FakeDB:
    def __init__(self, old_articles=None, law_exists=True):
        self.old_articles = list(old_articles or [])
        self.law_exists = law_exists
        self.calls = []

    def table(self, table, select="*", filters=None, order=None, limit=None):
        self.calls.append(("table", table, filters))
        if table == "laws" and self.law_exists:
            return [{"id": "law-1"}]
        return []

    def table_all(self, table, select="*", filters=None, order=None, max_rows=20000):
        self.calls.append(("table_all", table, filters))
        if table == "law_articles":
            return list(self.old_articles)
        return []

    def update(self, table, filters, values):
        self.calls.append(("update", table, filters, values))
        return [{"id": "law-1"}]

    def insert(self, table, rows, select="*", upsert_on=None, ignore_duplicates=False):
        self.calls.append(("insert", table, rows, upsert_on))
        if table == "laws":
            return [{"id": "law-new"}]
        return []

    def delete(self, table, filters):
        self.calls.append(("delete", table, filters))
        return []


def article(number, content=None):
    return {
        "article_number": str(number),
        "title": f"Тестовая статья {number}",
        "content": content or ("Полный текст тестовой статьи. " * 3),
        "chapter": "Глава 1",
        "position": int(number),
    }


class LawSyncSafetyTests(unittest.TestCase):
    def setUp(self):
        self.src = {
            "name": "Тестовый закон",
            "short_name": "ТЗ",
            "law_number": "ТЗ-1",
            "url": "https://forum.rmrp.ru/threads/test.123/",
        }

    def test_partial_download_does_not_change_existing_law_or_articles(self):
        old = [{"id": f"a{i}", "article_number": str(i)} for i in range(1, 11)]
        db = FakeDB(old_articles=old)
        page = object.__new__(LawPages)
        page.db = db

        with self.assertRaisesRegex(RuntimeError, "неполный документ"):
            page._store_law(self.src, [article(i) for i in range(1, 4)])

        changed = [call for call in db.calls if call[0] in ("update", "insert", "delete")]
        self.assertEqual(changed, [])

    def test_valid_sync_upserts_before_deleting_stale_articles(self):
        old = [{"id": f"a{i}", "article_number": str(i)} for i in range(1, 11)]
        db = FakeDB(old_articles=old)
        page = object.__new__(LawPages)
        page.db = db

        count = page._store_law(self.src, [article(i) for i in range(1, 10)])

        self.assertEqual(count, 9)
        kinds = [call[0] for call in db.calls]
        self.assertLess(kinds.index("insert"), kinds.index("delete"))
        delete_call = next(call for call in db.calls if call[0] == "delete")
        self.assertIn("a10", delete_call[2]["id"])

    def test_duplicate_article_numbers_are_rejected_before_database_changes(self):
        db = FakeDB(old_articles=[])
        page = object.__new__(LawPages)
        page.db = db

        with self.assertRaisesRegex(RuntimeError, "повторяющиеся"):
            page._store_law(self.src, [article(1), article(1), article(2)])

        self.assertFalse(any(call[0] in ("update", "insert", "delete") for call in db.calls))


class AiFullArticleTests(unittest.TestCase):
    def test_full_followup_returns_complete_article_text(self):
        content = "Полный текст нормы. " * 250
        result = AiPages._compose_article({
            "article_number": "12",
            "law_short": "УК РФ",
            "title": "Проверка полноты",
            "content": content,
        }, full=True)
        self.assertIn(content.strip(), result)

    def test_short_article_preview_remains_compact(self):
        content = "Полный текст нормы. " * 100
        result = AiPages._compose_article({
            "article_number": "12",
            "law_short": "УК РФ",
            "title": "Проверка превью",
            "content": content,
        }, full=False)
        self.assertLess(len(result), len(content) + 100)
        self.assertTrue(result.endswith("…"))


if __name__ == "__main__":
    unittest.main()
