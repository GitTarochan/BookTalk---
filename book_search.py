"""Cached book search with alternatives when Google Books is unavailable."""

import re
import threading
import time
import xml.etree.ElementTree as ET

import requests
import streamlit as st


USER_AGENT = "BookTalk/1.0 (https://github.com/GitTarochan/BookTalk---)"
TIMEOUT = (3, 10)
_open_library_lock = threading.Lock()
_open_library_last_request = 0.0
_ndl_lock = threading.Lock()


class BookSearchError(Exception):
    """Search services are temporarily unavailable."""


def _google_books(query, api_key):
    response = requests.get(
        "https://www.googleapis.com/books/v1/volumes",
        params={"q": query, "country": "JP", "maxResults": 5, "key": api_key},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    if (not isinstance(data, dict) or "error" in data
            or not isinstance(data.get("items", []), list)):
        raise ValueError("Invalid Google Books response")
    items = []
    seen = set()
    for item in data.get("items", []):
        if not isinstance(item, dict):
            continue
        book_id = item.get("id", "")
        book = item.get("volumeInfo")
        if (not isinstance(book, dict) or not re.fullmatch(r"[A-Za-z0-9_-]+", book_id)
                or book_id in seen):
            continue
        seen.add(book_id)
        items.append({"id": book_id, "volumeInfo": book})
    return items


def _open_library(query):
    # Open Library allows one request/second for unidentified clients.
    global _open_library_last_request
    with _open_library_lock:
        time.sleep(max(0, 1 - (time.monotonic() - _open_library_last_request)))
        _open_library_last_request = time.monotonic()
        response = requests.get(
            "https://openlibrary.org/search.json",
            params={"q": query, "lang": "ja", "limit": 5,
                    "fields": "key,title,author_name,cover_i"},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get("docs"), list):
        raise ValueError("Invalid Open Library response")
    items = []
    seen = set()
    for doc in data["docs"]:
        if not isinstance(doc, dict):
            continue
        work_id = doc.get("key", "").rsplit("/", 1)[-1]
        if not re.fullmatch(r"OL\d+W", work_id) or work_id in seen:
            continue
        seen.add(work_id)
        book = {"title": doc.get("title", "タイトル不明"),
                "authors": doc.get("author_name") or ["著者不明"],
                "sourceUrl": f"https://openlibrary.org/works/{work_id}"}
        cover_id = doc.get("cover_i")
        if isinstance(cover_id, int) and cover_id > 0:
            book["imageLinks"] = {
                "thumbnail": f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"}
        items.append({"id": f"ol-{work_id}", "volumeInfo": book})
    return items


def _ndl_search(query):
    # Use the NDL's own bibliographic records; requests must be serialized.
    with _ndl_lock:
        response = requests.get(
            "https://ndlsearch.ndl.go.jp/api/opensearch",
            params={"any": query, "cnt": 5, "dpid": "iss-ndl-opac", "mediatype": "books"},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    if root.tag != "rss" or root.find("channel") is None:
        raise ValueError("Invalid NDL response")
    items = []
    seen = set()
    for item in root.findall("./channel/item"):
        url = item.findtext("link", "")
        match = re.fullmatch(r"https://ndlsearch\.ndl\.go\.jp/books/([A-Za-z0-9_-]+)", url)
        if not match or url in seen:
            continue
        seen.add(url)
        authors = [node.text for node in item.findall("{http://purl.org/dc/elements/1.1/}creator")
                   if node.text]
        items.append({"id": f"ndl-{match.group(1)}", "volumeInfo": {
            "title": item.findtext("title") or "タイトル不明",
            "authors": authors or ["著者不明"], "sourceUrl": url}})
    return items


@st.cache_data(ttl=3600, max_entries=128, show_spinner=False)
def search_books(query, api_key=""):
    """Return (books, source). Cache successful results, never service failures."""
    if not query:
        return [], ""
    providers = []
    if api_key:
        providers.append(("Google Books", lambda: _google_books(query, api_key)))
    providers.extend([("Open Library", lambda: _open_library(query)),
                      ("国立国会図書館サーチ", lambda: _ndl_search(query))])
    had_success = False
    for source, search in providers:
        try:
            items = search()
        except (requests.RequestException, ValueError, ET.ParseError):
            # HTTP errors may contain the API key. Never display the raw error.
            continue
        had_success = True
        if items:
            return items, source
    if had_success:
        return [], ""
    raise BookSearchError("書籍検索サービスに接続できませんでした。少し時間をおいて再検索してください。")
