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
