import os
import sys
import unittest
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))
from rmrp import config  # noqa: E402


class ConfigTest(unittest.TestCase):
    def test_api_and_update_manifest_use_same_supabase_host(self):
        self.assertEqual(urlparse(config.SUPABASE_URL).netloc, urlparse(config.UPDATE_MANIFEST_URL).netloc)


if __name__ == "__main__":
    unittest.main()
