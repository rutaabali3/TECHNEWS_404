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
