import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from rmrp import textutil as T  # noqa: E402

FORUM = """
Содержание
Глава 1. Общие положения
Статья 1. Задачи кодекса
Статья 2. Принципы
Глава 2. Преступления против личности
Статья 12. Принципы уголовного законодательства
Глава 1. Общие положения
Статья 1. Задачи кодекса
1. Задачами настоящего Кодекса являются охрана прав и свобод человека и гражданина.
2. Для осуществления задач применяется наказание.
Статья 2. Принципы
Принципы законодательства основываются на равенстве граждан перед законом и справедливости.
Глава 2
Преступления против личности
Статья 12. Принципы уголовного законодательства
Уголовное законодательство основывается на принципах законности и гуманизма в отношении лиц.
Статья 228.1. Незаконный сбыт наркотических средств
Незаконный сбыт наказывается штрафом до 300 000 рублей либо лишением свободы на срок до 3 лет.
Статья 319. Оскорбление представителя власти
Публичное оскорбление представителя власти наказывается штрафом до 40 000 рублей.
"""


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.arts = T.parse_articles(T.html_to_lines(FORUM.replace("\n", "<br>")))
        self.by = {a["article_number"]: a for a in self.arts}

    def test_toc_is_dropped(self):
        self.assertEqual([a["article_number"] for a in self.arts], ["1", "2", "12", "228.1", "319"])

    def test_chapters(self):
        self.assertEqual(self.by["1"]["chapter"], "Глава 1. Общие положения")
        self.assertEqual(self.by["12"]["chapter"], "Глава 2. Преступления против личности")
        self.assertEqual(self.by["319"]["chapter"], "Глава 2. Преступления против личности")

    def test_content_does_not_swallow_chapter_heading(self):
        self.assertNotIn("Глава 2", self.by["2"]["content"])

    def test_html(self):
        lines = T.html_to_lines("<p>Статья&nbsp;5. Тест</p><div>Текст   статьи &amp; ещё</div><script>x</script>")
        self.assertEqual(lines, ["Статья 5. Тест", "Текст статьи & ещё"])


class SearchTests(unittest.TestCase):
    def test_stem_matches_forms(self):
        self.assertEqual(T.stem("задержанного"), T.stem("задержание"))
        self.assertEqual(T.stem("неповиновение"), T.stem("неповиновения"))
        self.assertEqual(T.stem("оскорбление"), T.stem("оскорбления"))

    def test_terms_skip_stopwords(self):
        terms = T.query_terms("Что грозит за неповиновение?")
        self.assertIn(T.stem("неповиновение"), terms)
        self.assertNotIn("что", terms)

    def test_article_ref(self):
        self.assertEqual(T.parse_article_ref("статья 12"), ("12", None))
        self.assertEqual(T.parse_article_ref("ст. 228.1 УК"), ("228.1", "УК РФ"))
        self.assertEqual(T.parse_article_ref("ук 319"), ("319", "УК РФ"))
        self.assertIsNone(T.parse_article_ref("права задержанного"))
        self.assertEqual(T.parse_article_ref("89 ук рф"), ("89", "УК РФ"))
        self.assertEqual(T.parse_article_ref("ук рф 89"), ("89", "УК РФ"))
        self.assertEqual(T.parse_article_ref("11.2 УПК РФ"), ("11.2", "ПК РФ"))
        self.assertEqual(T.parse_article_ref("ст 5 74-фз"), ("5", "74-ФЗ"))
        self.assertEqual(T.parse_article_ref("89"), ("89", None))
        self.assertIsNone(T.parse_article_ref("74-фз"))
        self.assertIsNone(T.parse_article_ref("уклонение от службы"))

    def test_smalltalk(self):
        for q in ("привет", "Привет!", "как дела", "привет, как дела?", "спасибо", "кто ты", "что ты умеешь", "пока"):
            self.assertTrue(T.smalltalk(q), q)
        for q in ("89 ук рф", "привет, что грозит за оскорбление", "оскорбление сотрудника", "права задержанного"):
            self.assertIsNone(T.smalltalk(q), q)
        self.assertEqual(T.strip_greeting("Привет, что грозит за оскорбление"), "что грозит за оскорбление")
        self.assertEqual(T.strip_greeting("ст. 228.1 УК"), "ст. 228.1 УК")

    def test_followup_and_relevance(self):
        self.assertTrue(T.is_followup("подробнее"))
        self.assertFalse(T.is_followup("подробнее про оскорбление"))
        row = {"title": "Оскорбление власти", "content": "штраф за оскорбление"}
        self.assertTrue(T.is_relevant(row, T.query_terms("оскорбление власти")))
        self.assertFalse(T.is_relevant(row, T.query_terms("рецепт борща")))

    def test_or_filter(self):
        self.assertEqual(T.or_filter(["абв"], ("title",)), "(title.ilike.*абв*)")

    def test_ranking_prefers_title(self):
        rows = [{"article_number": "1", "title": "Другое", "content": "оскорблен " * 3},
                {"article_number": "2", "title": "Оскорбление власти", "content": "текст"}]
        terms = T.query_terms("оскорбление власти")
        ranked = T.rank_articles(rows, terms, "оскорбление власти")
        self.assertEqual(ranked[0][1]["article_number"], "2")

    def test_best_sentences(self):
        txt = "Общее положение о праве. Оскорбление представителя власти наказывается штрафом до 40 000 рублей. Иное."
        out = T.best_sentences(txt, T.query_terms("наказание за оскорбление"))
        self.assertIn("штрафом", out)

    def test_natural_sort(self):
        nums = ["10", "2", "2.1", "228-1", "1"]
        self.assertEqual(sorted(nums, key=T.natural_key), ["1", "2", "2.1", "10", "228-1"])

    def test_admin_helpers(self):
        from datetime import datetime, timedelta, timezone
        now = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
        iso = lambda d: (now - timedelta(days=d)).isoformat()
        users = [{"username": "kinzec", "role": "FOUNDER", "status": "ACTIVE", "last_seen_at": iso(0), "created_at": iso(30)},
                 {"username": "alex", "role": "USER", "status": "BLOCKED", "last_seen_at": iso(5), "created_at": iso(2)},
                 {"username": "bob", "display_name": "Боб", "role": "USER", "status": "ACTIVE", "last_seen_at": iso(5), "created_at": iso(3)}]
        self.assertEqual(T.count_since(users, "created_at", 7, now), 2)
        self.assertEqual([u["username"] for u in T.filter_users(users, "", "USER")], ["alex", "bob"])
        self.assertEqual([u["username"] for u in T.filter_users(users, "боб")], ["bob"])
        self.assertEqual([u["username"] for u in T.filter_users(users, "", "", "BLOCKED")], ["alex"])
        self.assertEqual([u["username"] for u in T.filter_users(users, "", "", "ACTIVE", True, 180, now)], ["kinzec"])
        self.assertEqual(T.top_items([{"q": "Статья 12"}, {"q": "статья 12!"}, {"q": "а"}, {"q": "штраф"}], "q"), [("Статья 12", 2), ("штраф", 1)])
        reports = [{"reason": "Баг", "description": "не открывается", "status": "NEW", "author": {"username": "alex"}},
                   {"reason": "Идея", "description": "темная тема", "status": "RESOLVED", "author": {"username": "bob"}}]
        self.assertEqual(len(T.filter_reports(reports, "", "NEW")), 1)
        self.assertEqual(T.filter_reports(reports, "bob")[0]["reason"], "Идея")
        logs = [{"created_at": iso(0), "action": "Удалён закон", "profiles": {"username": "kinzec"}},
                {"created_at": iso(20), "action": "Статус жалобы", "profiles": {"username": "alex"}}]
        self.assertEqual(len(T.filter_audit(logs, days=7, now=now)), 1)
        self.assertEqual(T.filter_audit(logs, "alex")[0]["action"], "Статус жалобы")
        self.assertEqual(len(T.filter_audit(logs, "", "Удалён закон", now=now)), 1)
        self.assertEqual(T.in_filter(["a", 2]), "in.(a,2)")

    def test_online(self):
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        self.assertTrue(T.is_online((now - timedelta(seconds=30)).isoformat(), 180, now))
        self.assertFalse(T.is_online((now - timedelta(minutes=10)).isoformat(), 180, now))
        self.assertFalse(T.is_online(None))

    def test_plural(self):
        self.assertEqual(T.plural(1, "закон", "закона", "законов"), "закон")
        self.assertEqual(T.plural(3, "закон", "закона", "законов"), "закона")
        self.assertEqual(T.plural(11, "закон", "закона", "законов"), "законов")
        self.assertEqual(T.plural(30, "закон", "закона", "законов"), "законов")


if __name__ == "__main__":
    unittest.main()
