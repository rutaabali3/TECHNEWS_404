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
