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
