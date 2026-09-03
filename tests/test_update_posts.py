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
