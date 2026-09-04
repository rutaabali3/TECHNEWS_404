from datetime import datetime, timezone
import pytest
from scripts.update_posts import parse_timestamp


def test_parse_timestamp_none_or_empty():
    assert parse_timestamp(None) is None
    assert parse_timestamp("") is None
    assert parse_timestamp([]) is None


def test_parse_timestamp_valid_iso_with_z():
    ts = "2025-01-01T12:00:00Z"
    expected = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert parse_timestamp(ts) == expected


def test_parse_timestamp_valid_iso_with_offset():
    ts = "2025-01-01T12:00:00+00:00"
    expected = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert parse_timestamp(ts) == expected


def test_parse_timestamp_invalid_format():
    assert parse_timestamp("invalid-date") is None
    assert parse_timestamp("2025-13-45") is None
    assert parse_timestamp("2025/01/01") is None


# Tests contributed by PR #11
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../scripts")))

import update_posts


class TestSummarizeHelpers(unittest.TestCase):

    def setUp(self):
        self.article = {
            "title": "Test Title",
            "author": "Test Author",
            "body": "Test Body Paragraph",
            "description": "Test Description",
            "feed_excerpt": "Test Feed Excerpt",
        }
        self.api_key = "gsk_testkey"

    def test_build_summary_prompt(self):
        prompt = update_posts._build_summary_prompt(self.article)
        self.assertIn("TITLE: Test Title", prompt)
        self.assertIn("AUTHOR: Test Author", prompt)
        self.assertIn("ARTICLE TEXT:\nTest Body Paragraph", prompt)

    @patch("update_posts.requests.post")
    def test_call_groq_api_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"summary": "OK"}'}}]
        }
        mock_post.return_value = mock_response

        content = update_posts._call_groq_api({"test": "payload"}, self.api_key)
        self.assertEqual(content, '{"summary": "OK"}')

    def test_parse_summary_response(self):
        res = update_posts._parse_summary_response('{"summary": "Parsed", "key_points": [], "topics": []}', self.article)
        self.assertEqual(res["summary"], "Parsed")

    @patch("update_posts.requests.post")
    def test_summarize_success_clean_json(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "A clean summary.", "key_points": ["Point 1"], "topics": ["tech"]}'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = update_posts.summarize(self.article, self.api_key)

        self.assertEqual(result["summary"], "A clean summary.")
        self.assertEqual(result["key_points"], ["Point 1"])
        self.assertEqual(result["topics"], ["tech"])

    @patch("update_posts.requests.post")
    def test_summarize_markdown_fences(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '```json\n{"summary": "Fenced summary.", "key_points": [], "topics": ["ai"]}\n```'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = update_posts.summarize(self.article, self.api_key)

        self.assertEqual(result["summary"], "Fenced summary.")

    @patch("update_posts.requests.post")
    def test_summarize_fallback_json_validation_error(self, mock_post):
        fail_response = MagicMock()
        fail_response.status_code = 400
        fail_response.json.return_value = {"error": {"code": "json_validate_failed", "message": "Failed"}}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "Fallback summary.", "key_points": [], "topics": []}'
                    }
                }
            ]
        }

        mock_post.side_effect = [fail_response, success_response]

        result = update_posts.summarize(self.article, self.api_key)

        self.assertEqual(result["summary"], "Fallback summary.")
        self.assertEqual(mock_post.call_count, 2)

    @patch("update_posts.requests.post")
    def test_summarize_bad_json_sub_string_extraction(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": 'Prefix commentary {"summary": "Extracted summary.", "key_points": [], "topics": ["t"]} Suffix commentary'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = update_posts.summarize(self.article, self.api_key)

        self.assertEqual(result["summary"], "Extracted summary.")

    @patch("update_posts.requests.post")
    def test_summarize_malformed_json_regex_fallback(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "Regex extracted summary", key_points: bad_json}'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = update_posts.summarize(self.article, self.api_key)

        self.assertEqual(result["summary"], "Regex extracted summary")

    @patch("update_posts.requests.post")
    def test_summarize_empty_summary_fallback_to_description(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"summary": "", "key_points": [], "topics": []}'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        result = update_posts.summarize(self.article, self.api_key)

        self.assertEqual(result["summary"], "Test Description")


if __name__ == "__main__":
    unittest.main()


# Tests contributed by PR #12
import json
import pytest
import sys
from pathlib import Path

# Add scripts directory to sys.path so update_posts can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from update_posts import load_json


def test_load_json_valid_dict(tmp_path):
    file_path = tmp_path / "valid_data.json"
    data = {"updated_at": "2023-01-01T00:00:00Z", "posts": [{"id": "1", "title": "Test"}]}
    file_path.write_text(json.dumps(data), encoding="utf-8")

    default = {"updated_at": None, "posts": []}
    result = load_json(file_path, default)
    assert result == data


def test_load_json_valid_list(tmp_path):
    file_path = tmp_path / "valid_list.json"
    data = [1, 2, 3]
    file_path.write_text(json.dumps(data), encoding="utf-8")

    default = []
    result = load_json(file_path, default)
    assert result == data


def test_load_json_file_not_found(tmp_path):
    non_existent_file = tmp_path / "does_not_exist.json"
    default = {"default_key": "default_val"}

    result = load_json(non_existent_file, default)
    assert result == default


def test_load_json_invalid_json(tmp_path):
    file_path = tmp_path / "invalid.json"
    file_path.write_text("{ malformed json: ", encoding="utf-8")
    default = {"updated_at": None, "items": []}

    result = load_json(file_path, default)
    assert result == default


def test_load_json_empty_file(tmp_path):
    file_path = tmp_path / "empty.json"
    file_path.write_text("", encoding="utf-8")
    default = []

    result = load_json(file_path, default)
    assert result == default


# Tests contributed by PR #13
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.update_posts import groq_keys


@pytest.fixture(autouse=True)
def clear_groq_env(monkeypatch):
    """Ensure all Groq API key environment variables are cleared before each test."""
    for i in range(1, 6):
        monkeypatch.delenv(f"GROQ_API_KEY_{i}", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)


def test_groq_keys_no_env_vars():
    """Test groq_keys returns an empty list when no env vars are set."""
    assert groq_keys() == []


def test_groq_keys_single_indexed_key(monkeypatch):
    """Test groq_keys extracts a single GROQ_API_KEY_1."""
    monkeypatch.setenv("GROQ_API_KEY_1", "gsk_key1")
    assert groq_keys() == ["gsk_key1"]


def test_groq_keys_multiple_indexed_keys(monkeypatch):
    """Test groq_keys extracts multiple indexed keys in order 1..5."""
    monkeypatch.setenv("GROQ_API_KEY_1", "gsk_key1")
    monkeypatch.setenv("GROQ_API_KEY_3", "gsk_key3")
    monkeypatch.setenv("GROQ_API_KEY_5", "gsk_key5")
    assert groq_keys() == ["gsk_key1", "gsk_key3", "gsk_key5"]


def test_groq_keys_strips_whitespace(monkeypatch):
    """Test groq_keys removes all whitespace from key values."""
    monkeypatch.setenv("GROQ_API_KEY_1", "  gsk_key1 \n")
    monkeypatch.setenv("GROQ_API_KEY_2", "gsk _ key2 \t")
    assert groq_keys() == ["gsk_key1", "gsk_key2"]


def test_groq_keys_legacy_fallback(monkeypatch):
    """Test groq_keys falls back to GROQ_API_KEY when no indexed keys exist."""
    monkeypatch.setenv("GROQ_API_KEY", "  gsk_legacy  ")
    assert groq_keys() == ["gsk_legacy"]


def test_groq_keys_indexed_takes_precedence_over_legacy(monkeypatch):
    """Test indexed keys take precedence over legacy GROQ_API_KEY."""
    monkeypatch.setenv("GROQ_API_KEY_1", "gsk_indexed")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_legacy")
    assert groq_keys() == ["gsk_indexed"]


def test_groq_keys_empty_or_whitespace_only(monkeypatch):
    """Test empty or whitespace-only env vars are ignored."""
    monkeypatch.setenv("GROQ_API_KEY_1", "   ")
    monkeypatch.setenv("GROQ_API_KEY_2", "")
    assert groq_keys() == []


# Tests contributed by PR #14
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch
import pytest
import requests

from scripts.update_posts import FEED_URL, clean_text, parse_feed


def test_clean_text_basic():
    assert clean_text("Hello World") == "Hello World"
    assert clean_text("  Hello   World  \n\t") == "Hello World"
    assert clean_text("Apple &amp; Banana") == "Apple & Banana"
    assert clean_text("&#8217;Quote&#8217;") == "’Quote’"
    assert clean_text(None) == ""
    assert clean_text("") == ""


def test_parse_feed_success():
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>TechCrunch</title>
            <item>
                <title>First Article &amp; Title</title>
                <link>https://techcrunch.com/2025/01/01/first-article/</link>
                <description>This is a &lt;b&gt;description&lt;/b&gt; of the article.</description>
                <pubDate>Wed, 01 Jan 2025 12:00:00 +0000</pubDate>
            </item>
            <item>
                <title>Second Article</title>
                <link>https://techcrunch.com/2025/01/02/second-article/</link>
                <description>Another excerpt.</description>
                <pubDate>Thu, 02 Jan 2025 14:30:00 +0000</pubDate>
            </item>
        </channel>
    </rss>
    """
    mock_response = MagicMock()
    mock_response.content = sample_xml.encode("utf-8")

    with patch("scripts.update_posts.get") as mock_get:
        mock_get.return_value = mock_response
        items = parse_feed()

        mock_get.assert_called_once_with(FEED_URL)
        assert len(items) == 2
        assert items[0] == {
            "title": "First Article & Title",
            "url": "https://techcrunch.com/2025/01/01/first-article/",
            "feed_excerpt": "This is a <b>description</b> of the article.",
            "published": "Wed, 01 Jan 2025 12:00:00 +0000",
        }
        assert items[1] == {
            "title": "Second Article",
            "url": "https://techcrunch.com/2025/01/02/second-article/",
            "feed_excerpt": "Another excerpt.",
            "published": "Thu, 02 Jan 2025 14:30:00 +0000",
        }


def test_parse_feed_missing_required_fields():
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <item>
                <title>Valid Title</title>
                <link>https://techcrunch.com/valid</link>
            </item>
            <item>
                <title>Missing Link</title>
                <description>No link element</description>
            </item>
            <item>
                <link>https://techcrunch.com/missing-title</link>
                <description>No title element</description>
            </item>
            <item>
                <title>   </title>
                <link>https://techcrunch.com/whitespace-title</link>
            </item>
        </channel>
    </rss>
    """
    mock_response = MagicMock()
    mock_response.content = sample_xml.encode("utf-8")

    with patch("scripts.update_posts.get") as mock_get:
        mock_get.return_value = mock_response
        items = parse_feed()

        assert len(items) == 1
        assert items[0]["title"] == "Valid Title"
        assert items[0]["url"] == "https://techcrunch.com/valid"


def test_parse_feed_limit_50_items():
    items_xml = "".join(
        f"<item><title>Item {i}</title><link>https://techcrunch.com/item-{i}</link></item>"
        for i in range(60)
    )
    sample_xml = f'<?xml version="1.0"?><rss version="2.0"><channel>{items_xml}</channel></rss>'

    mock_response = MagicMock()
    mock_response.content = sample_xml.encode("utf-8")

    with patch("scripts.update_posts.get") as mock_get:
        mock_get.return_value = mock_response
        items = parse_feed()

        assert len(items) == 50
        assert items[0]["title"] == "Item 0"
        assert items[49]["title"] == "Item 49"


def test_parse_feed_empty_xml():
    sample_xml = '<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
    mock_response = MagicMock()
    mock_response.content = sample_xml.encode("utf-8")

    with patch("scripts.update_posts.get") as mock_get:
        mock_get.return_value = mock_response
        items = parse_feed()

        assert items == []


def test_parse_feed_http_error():
    with patch("scripts.update_posts.get") as mock_get:
        mock_get.side_effect = requests.RequestException("Connection error")
        with pytest.raises(requests.RequestException):
            parse_feed()


# Tests contributed by PR #15
import unittest
from scripts.update_posts import clean_text


class TestCleanText(unittest.TestCase):
    def test_none_and_empty_string(self):
        self.assertEqual(clean_text(None), "")
        self.assertEqual(clean_text(""), "")

    def test_whitespace_stripping_and_normalization(self):
        self.assertEqual(clean_text("  hello   world  "), "hello world")
        self.assertEqual(clean_text("\n\thallo\r\n\t world\n"), "hallo world")
        self.assertEqual(clean_text("  "), "")

    def test_html_entity_unescaping(self):
        self.assertEqual(clean_text("TechCrunch &amp; News"), "TechCrunch & News")
        self.assertEqual(clean_text("&lt;div&gt; &quot;Quotes&quot; &#39;Single&#39;&lt;/div&gt;"), "<div> \"Quotes\" 'Single'</div>")
        self.assertEqual(clean_text("Space&nbsp;NonBreaking"), "Space NonBreaking")

    def test_combined_entities_and_whitespace(self):
        self.assertEqual(clean_text("  &lt;p&gt; Hello \n\t &amp; \r\n Welcome! &lt;/p&gt;  "), "<p> Hello & Welcome! </p>")
        self.assertEqual(clean_text("  &#128075;  Hello&#128512; "), "👋 Hello😀")


if __name__ == "__main__":
    unittest.main()


# Tests contributed by PR #16
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))

import update_posts


class TestUpdatePosts(unittest.TestCase):
    def test_process_item_mocked(self):
        item = {"title": "Test Title", "url": "https://techcrunch.com/test-article", "feed_excerpt": "Test excerpt", "published": "Wed, 01 Jan 2025 00:00:00 +0000"}

        with patch("update_posts.extract_article") as mock_extract, \
             patch("update_posts.summarize") as mock_summarize:

            mock_extract.return_value = {
                **item,
                "image": "https://techcrunch.com/image.jpg",
                "author": "Test Author",
                "description": "Test description",
                "body": "Test body text that is long enough."
            }
            mock_summarize.return_value = {
                "summary": "This is a summary.",
                "key_points": ["Point 1", "Point 2"],
                "topics": ["tech", "ai"]
            }

            result = update_posts.process_item(item, "gsk_dummy_key")

            self.assertEqual(result["title"], "Test Title")
            self.assertEqual(result["summary"], "This is a summary.")
            self.assertEqual(result["author"], "Test Author")
            self.assertIn("processed_at", result)

    def test_main_concurrent_processing(self):
        """Test main execution path with concurrent process_item calls."""
        fake_queue = {
            "updated_at": "2025-01-01T00:00:00+00:00",
            "items": [
                {"title": f"Article {i}", "url": f"https://techcrunch.com/article-{i}", "feed_excerpt": "excerpt", "published": "Wed, 01 Jan 2025 00:00:00 +0000"}
                for i in range(5)
            ]
        }
        fake_existing = {"updated_at": None, "source": "TechCrunch", "posts": []}

        with patch("update_posts.load_json") as mock_load_json, \
             patch("update_posts.save_json") as mock_save_json, \
             patch("update_posts.parse_feed") as mock_parse_feed, \
             patch("update_posts.groq_keys") as mock_groq_keys, \
             patch("update_posts.process_item") as mock_process_item:

            mock_load_json.side_effect = [fake_existing, fake_queue]
            mock_parse_feed.return_value = []
            mock_groq_keys.return_value = ["gsk_key1", "gsk_key2"]

            def side_effect_process(item, key):
                return {
                    "id": item["url"].split("/")[-1],
                    "title": item["title"],
                    "summary": "Summary",
                    "source_url": item["url"],
                    "published": item["published"]
                }

            mock_process_item.side_effect = side_effect_process

            update_posts.main()

            self.assertEqual(mock_process_item.call_count, 5)
            self.assertTrue(mock_save_json.called)

    def test_sequential_vs_concurrent_benchmark(self):
        """Benchmark showing speedup of parallel thread processing vs sequential processing."""
        items = [{"url": f"https://techcrunch.com/article-{i}", "title": f"Article {i}"} for i in range(10)]
        keys = ["gsk_key1", "gsk_key2"]

        def mock_process_item_slow(item, key):
            time.sleep(0.05)  # Simulate 50ms I/O latency per item
            return {"title": item["title"], "source_url": item["url"]}

        # 1. Sequential execution time
        start_seq = time.perf_counter()
        seq_results = []
        for i, item in enumerate(items):
            key = keys[i % len(keys)]
            seq_results.append(mock_process_item_slow(item, key))
        duration_seq = time.perf_counter() - start_seq

        # 2. Concurrent execution time using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed
        start_conc = time.perf_counter()
        conc_results = []
        with ThreadPoolExecutor(max_workers=len(items)) as executor:
            futures = {
                executor.submit(mock_process_item_slow, item, keys[i % len(keys)]): item
                for i, item in enumerate(items)
            }
            for future in as_completed(futures):
                conc_results.append(future.result())
        duration_conc = time.perf_counter() - start_conc

        print(f"\n[Benchmark] Sequential duration: {duration_seq:.4f}s")
        print(f"[Benchmark] Concurrent duration: {duration_conc:.4f}s")
        if duration_conc > 0:
            print(f"[Benchmark] Speedup factor: {duration_seq / duration_conc:.2f}x")

        self.assertEqual(len(seq_results), 10)
        self.assertEqual(len(conc_results), 10)
        self.assertLess(duration_conc, duration_seq / 2.5)  # Should be significantly faster


if __name__ == "__main__":
    unittest.main()


# Tests contributed by PR #17
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure scripts directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from update_posts import save_json


class TestSaveJson(unittest.TestCase):
    def test_save_json_creates_directories_and_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "nested", "dir", "output.json")
            data = {"title": "Test Article", "id": 123}

            save_json(file_path, data)

            self.assertTrue(os.path.exists(file_path))
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            self.assertEqual(loaded_data, data)

    def test_save_json_formatting_and_newline(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "test_format.json")
            data = {"key": "value", "list": [1, 2]}

            save_json(file_path, data)

            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            expected_content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
            self.assertEqual(raw_content, expected_content)
            self.assertTrue(raw_content.endswith("\n"))

    def test_save_json_unicode_preservation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "test_unicode.json")
            data = {"headline": "Café & Tech 🚀", "chinese": "科技新闻"}

            save_json(file_path, data)

            with open(file_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            self.assertIn("Café & Tech 🚀", raw_content)
            self.assertIn("科技新闻", raw_content)
            self.assertNotIn("\\u", raw_content)

            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            self.assertEqual(loaded_data, data)

    def test_save_json_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "data.json")
            initial_data = {"status": "old"}
            updated_data = {"status": "new", "count": 10}

            save_json(file_path, initial_data)
            save_json(file_path, updated_data)

            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            self.assertEqual(loaded_data, updated_data)

    def test_save_json_relative_path_current_directory(self):
        file_path = "tmp_test_save_json_relative.json"
        data = {"test": True}

        try:
            save_json(file_path, data)
            self.assertTrue(os.path.exists(file_path))
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            self.assertEqual(loaded_data, data)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)


if __name__ == "__main__":
    unittest.main()
