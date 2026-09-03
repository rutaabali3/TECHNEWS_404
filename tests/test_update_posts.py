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
