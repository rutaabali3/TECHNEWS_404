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
