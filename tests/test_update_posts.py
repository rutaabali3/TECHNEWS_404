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
