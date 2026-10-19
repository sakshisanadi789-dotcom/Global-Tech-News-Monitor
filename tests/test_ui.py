"""Browser UI test for the Flask news dashboard."""

import os
import threading
import unittest
from unittest.mock import MagicMock

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

from main import create_app


class Cursor:
    """A small iterable stand-in for the PyMongo cursor used by the UI."""

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def __iter__(self):
        return iter(
            [
                {
                    "_id": "test-id",
                    "title": "Python tools for technology teams",
                    "description": "A sample article shown in the dashboard.",
                    "source": "Example News",
                    "author": None,
                    "url": "https://example.com/python-tools",
                    "category": "Developer Tools",
                }
            ]
        )


@unittest.skipUnless(
    os.getenv("RUN_BROWSER_TESTS") == "1",
    "Set RUN_BROWSER_TESTS=1 to run the Playwright browser test.",
)
class NewsDashboardBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.news_collection = MagicMock()
        cls.news_collection.find.return_value = Cursor()
        cls.database = {
            "news": cls.news_collection,
            "daily_briefings": MagicMock(),
        }
        cls.app = create_app(MagicMock(), cls.database)
        cls.server = make_server("127.0.0.1", 0, cls.app)
        cls.server_thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.shutdown()
        cls.server_thread.join(timeout=5)

    def test_dashboard_loads_and_search_shows_article(self):
        page = self.browser.new_page()
        try:
            page.goto(self.base_url, wait_until="networkidle")

            self.assertEqual(page.title(), "Daily Global Tech News")
            self.assertTrue(page.get_by_role("heading", name="Daily Global Tech News").is_visible())
            self.assertTrue(
                page.get_by_role("heading", name="Python tools for technology teams").is_visible()
            )
            self.assertIn("Showing 1 article", page.locator("#status").inner_text())
            self.assertTrue(
                page.get_by_label("Automatically collect news").is_visible()
            )
            self.assertTrue(
                page.get_by_role("button", name="Save schedule").is_visible()
            )

            page.get_by_label("Search keyword").fill("python")
            page.get_by_role("button", name="Search news").click()

            self.assertTrue(
                page.get_by_role("link", name="Read source article").is_visible()
            )
            self.assertEqual(
                page.get_by_role("link", name="Read source article").get_attribute("href"),
                "https://example.com/python-tools",
            )
        finally:
            page.close()


if __name__ == "__main__":
    unittest.main()
