import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from rmrp import config as C  # noqa: E402
from rmrp import memo_util as M  # noqa: E402


class TagsTest(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(M.normalize_tags("важно, #суд; ГИБДД\nвАЖНО"), ["Важно", "Суд", "ГИБДД"])

    def test_limits(self):
        tags = M.normalize_tags(",".join(f"т{i}" for i in range(30)))
        self.assertEqual(len(tags), M.MAX_TAGS)
        self.assertTrue(all(len(t) <= M.MAX_TAG_LEN for t in M.normalize_tags("x" * 100)))
        self.assertEqual(M.normalize_tags(["", "  ", "#"]), [])

    def test_color_is_stable(self):
        self.assertEqual(M.tag_color("Важно"), "#ef4444")
        self.assertEqual(M.tag_color("свой тег"), M.tag_color("СВОЙ ТЕГ"))


class FilterTest(unittest.TestCase):
    rows = [
        {"id": 1, "title": "Задержание", "content": "Права при задержании", "tags": ["Полиция", "Важно"], "created_at": "2026-01-01", "pinned": False},
        {"id": 2, "title": "Штрафы ГИБДД", "content": "Размеры штрафов", "tags": ["Штрафы"], "created_at": "2026-02-01", "pinned": False},
        {"id": 3, "title": "Старая закреплённая", "content": "", "tags": [], "created_at": "2025-01-01", "pinned": True},
    ]

    def test_filter_by_tags_all_required(self):
        self.assertEqual([m["id"] for m in M.filter_memos(self.rows, "", ["полиция"])], [1])
        self.assertEqual(M.filter_memos(self.rows, "", ["Полиция", "Штрафы"]), [])

    def test_search(self):
        self.assertEqual([m["id"] for m in M.filter_memos(self.rows, "гибдд")], [2])
        self.assertEqual([m["id"] for m in M.filter_memos(self.rows, "важно")], [1])  # поиск и по тегам

    def test_sort_pinned_then_newest(self):
        self.assertEqual([m["id"] for m in M.sort_memos(self.rows)], [3, 2, 1])

    def test_all_tags_order(self):
        self.assertEqual([t for t, _ in M.all_tags(self.rows)], ["Важно", "Полиция", "Штрафы"])

    def test_validate(self):
        self.assertIsNotNone(M.validate_memo("", "текст", [], 0))
        self.assertIsNotNone(M.validate_memo("т", "", [], 0))
        self.assertIsNone(M.validate_memo("т", "", [], 1))  # только фото — допустимо
        self.assertIsNotNone(M.validate_memo("т", "x" * (M.MAX_CONTENT + 1), [], 0))
        self.assertIsNotNone(M.validate_memo("т", "x", [], M.MAX_IMAGES + 1))


class ImageTest(unittest.TestCase):
    def test_object_path(self):
        url = "https://x.supabase.co/storage/v1/object/public/memo-images/u1/a.jpg"
        self.assertEqual(M.object_path(url), "u1/a.jpg")
        self.assertEqual(M.object_path("u1/a.jpg"), "u1/a.jpg")
        p = M.new_object_path("u1", "png")
        self.assertTrue(p.startswith("u1/") and p.endswith(".png"))

    def test_rejects_non_image(self):
        d = tempfile.mkdtemp()
        f = os.path.join(d, "x.exe")
        open(f, "wb").write(b"MZ")
        with self.assertRaises(ValueError):
            M.prepare_image(f)

    @unittest.skipIf(M.Image is None, "нет Pillow")
    def test_big_photo_is_shrunk(self):
        d = tempfile.mkdtemp()
        f = os.path.join(d, "big.png")
        M.Image.effect_noise((3000, 2000), 40).convert("RGB").save(f)
        data, ctype, ext = M.prepare_image(f)
        self.assertEqual((ctype, ext), ("image/jpeg", "jpg"))
        self.assertLessEqual(len(data), M.MAX_UPLOAD_BYTES)
        import io
        self.assertLessEqual(max(M.Image.open(io.BytesIO(data)).size), 1600)

    @unittest.skipIf(M.Image is None, "нет Pillow")
    def test_transparent_png_stays_png(self):
        d = tempfile.mkdtemp()
        f = os.path.join(d, "a.png")
        M.Image.new("RGBA", (50, 50), (255, 0, 0, 80)).save(f)
        self.assertEqual(M.prepare_image(f)[1:], ("image/png", "png"))

    @unittest.skipIf(M.Image is None, "нет Pillow")
    def test_corrupt_image(self):
        d = tempfile.mkdtemp()
        f = os.path.join(d, "bad.jpg")
        open(f, "wb").write(b"not an image")
        with self.assertRaises(ValueError):
            M.prepare_image(f)


class RoleColorsTest(unittest.TestCase):
    def tearDown(self):
        C.set_role_colors({})

    def test_defaults_and_override(self):
        self.assertEqual(C.role_color("ADMIN"), C.default_role_color("ADMIN"))
        C.set_role_colors('{"ADMIN": "#00FF00", "FOUNDER": "red", "HACK": "#000000", "USER": "#12345"}')
        self.assertEqual(C.role_color("ADMIN"), "#00ff00")
        self.assertEqual(C.role_color("FOUNDER"), C.default_role_color("FOUNDER"))  # некорректный цвет отброшен
        self.assertNotIn("HACK", C.ROLE_COLOR_OVERRIDES)
        C.set_role_colors({})
        self.assertEqual(C.role_color("ADMIN"), C.default_role_color("ADMIN"))

    def test_garbage(self):
        self.assertEqual(C.parse_role_colors("не json"), {})
        self.assertEqual(C.parse_role_colors("[1,2]"), {})

    def test_all_default_colors_distinct(self):
        cols = [C.default_role_color(r) for r in C.ROLE_ORDER]
        self.assertEqual(len(set(cols)), len(cols))


if __name__ == "__main__":
    unittest.main()
