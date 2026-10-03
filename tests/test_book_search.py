import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import book_search
from streamlit.testing.v1 import AppTest


def response(data=None, status=200, content=b""):
    result = Mock(status_code=status, content=content)
    result.json.return_value = data
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError("private-key-in-url")
    return result


OL_BOOK = {"key": "/works/OL16087935W", "title": "こころ",
           "author_name": ["夏目漱石"], "cover_i": 6910184}


class BookSearchTests(unittest.TestCase):
    def setUp(self):
        book_search.search_books.clear()

    @patch("book_search.requests.get")
    def test_daily_quota_429_falls_back_with_title_author_and_cover(self, get):
        get.side_effect = [response(status=429), response({"docs": [OL_BOOK]})]
        items, source = book_search.search_books("こころ & 夏目漱石", "test-key")
        self.assertEqual(source, "Open Library")
        self.assertEqual(items[0]["id"], "ol-OL16087935W")
        self.assertEqual(items[0]["volumeInfo"]["authors"], ["夏目漱石"])
        self.assertTrue(items[0]["volumeInfo"]["imageLinks"]["thumbnail"].startswith("https://"))
        self.assertEqual(get.call_args_list[0].kwargs["params"]["q"], "こころ & 夏目漱石")
        self.assertEqual(get.call_args_list[0].kwargs["params"]["key"], "test-key")

    @patch("book_search.requests.get")
    def test_no_key_skips_google_and_repeated_query_uses_cache(self, get):
        get.return_value = response({"docs": [OL_BOOK]})
        book_search.search_books("こころ")
        book_search.search_books("こころ")
        self.assertEqual(get.call_count, 1)
        self.assertEqual(get.call_args.args[0], "https://openlibrary.org/search.json")

    @patch("book_search.requests.get")
    def test_configured_google_preserves_existing_room_id(self, get):
        get.return_value = response({"items": [{"id": "google-volume_1", "volumeInfo": {
            "title": "こころ", "authors": ["夏目漱石"]}}]})
        items, source = book_search.search_books("こころ", "test-key")
        self.assertEqual(source, "Google Books")
        self.assertEqual(items[0]["id"], "google-volume_1")
        self.assertEqual(get.call_count, 1)

    @patch("book_search.requests.get")
    def test_empty_open_library_results_fall_back_to_ndl(self, get):
        xml = Path(__file__).with_name("ndl_response.xml").read_bytes()
        get.side_effect = [response({"docs": []}), response(content=xml)]
        items, source = book_search.search_books("こころ 夏目漱石")
        self.assertEqual(source, "国立国会図書館サーチ")
        self.assertEqual(len(items), 5)
        self.assertTrue(items[0]["id"].startswith("ndl-R100000002-"))
        self.assertTrue(items[0]["volumeInfo"]["authors"])
        self.assertEqual(get.call_args.kwargs["params"]["mediatype"], "books")

    @patch("book_search.requests.get")
    def test_all_services_unavailable_hide_details_and_are_not_cached(self, get):
        get.side_effect = requests.Timeout("private-key-in-url")
        for _ in range(2):
            with self.assertRaises(book_search.BookSearchError) as error:
                book_search.search_books("こころ", "test-key")
            self.assertNotIn("private-key", str(error.exception))
        self.assertEqual(get.call_count, 6)

    @patch("book_search.requests.get")
    def test_no_results_is_distinct_from_service_failure(self, get):
        get.side_effect = [response({"docs": []}), response(content=b"<rss><channel/></rss>")]
        self.assertEqual(book_search.search_books("no matches"), ([], ""))

    @patch("book_search.requests.get")
    def test_blank_query_makes_no_requests(self, get):
        self.assertEqual(book_search.search_books(""), ([], ""))
        get.assert_not_called()


class AppFlowTests(unittest.TestCase):
    @patch("book_search.search_books")
    def test_search_room_and_back(self, search):
        search.return_value = ([{"id": "ol-OL16087935W", "volumeInfo": {
            "title": "こころ", "authors": ["夏目漱石"]}}], "Open Library")
        app = AppTest.from_file("app.py").run()
        self.assertEqual(len(app.exception), 0)
        app.text_input[0].set_value("  こころ　 夏目漱石  ")
        app.button[0].click().run()
        self.assertEqual(search.call_args.args[0], "こころ 夏目漱石")
        self.assertEqual(len(app.error), 0)
        self.assertEqual(app.success[0].value, "1 件見つかりました！")
        app.button[1].click().run()
        self.assertEqual(app.session_state["page"], "room")
        self.assertIn("BookTalk-Room-ol-OL16087935W", app.info[0].value)
        app.sidebar.button[0].click().run()
        self.assertEqual(app.session_state["page"], "search")
        self.assertEqual(len(app.exception), 0)

    @patch("book_search.search_books")
    def test_failed_new_search_clears_old_results(self, search):
        search.side_effect = [([{"id": "ol-OL16087935W", "volumeInfo": {
            "title": "こころ"}}], "Open Library"), book_search.BookSearchError("再検索してください")]
        app = AppTest.from_file("app.py").run()
        app.text_input[0].set_value("こころ")
        app.button[0].click().run()
        app.text_input[0].set_value("別の本")
        app.button[0].click().run()
        self.assertIsNone(app.session_state["search_results"])
        self.assertEqual(app.error[0].value, "再検索してください")
        self.assertEqual(len(app.exception), 0)


if __name__ == "__main__":
    unittest.main()
