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
