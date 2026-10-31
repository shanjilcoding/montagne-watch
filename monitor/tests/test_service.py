import tempfile
import unittest
from pathlib import Path

from montagne_monitor.db import MonitorDatabase
from montagne_monitor.service import CatalogMonitor, CatalogSourceError


CARD = """
<div class="ProductList-item hentry category-all-fragrance category-unisex post-type-store-item {sold} clear"
     id="thumb-{slug}" data-item-id="{id}">
  <a href="/{collection}/{slug}" class="ProductList-item-link"></a>
  <img data-src="https://images.example/{slug}.jpg">
  <h1 class="ProductList-title">{name}</h1>
  <div class="product-price">${price}</div>
</div>
"""


def catalog_card(product_id: str, collection: str, sold_out: bool = False) -> str:
    return CARD.format(
        sold="sold-out" if sold_out else "",
        slug=product_id,
        id=product_id,
        collection=collection,
        name=product_id.upper(),
        price="45.00",
    )


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __call__(self, url: str) -> str:
        self.calls.append(url)
        for key, value in self.pages.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                return value
        raise AssertionError(f"Unexpected URL: {url}")


class CatalogMonitorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = MonitorDatabase(Path(self.tempdir.name) / "monitor.db")

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    def test_successful_cycle_fetches_all_collections_and_builds_baseline(self):
        fetcher = FakeFetcher(
            {
                "/fragrance?": catalog_card("frag-1", "fragrance"),
                "/discovery?": catalog_card("sample-1", "discovery", sold_out=True),
                "/maison?": catalog_card("candle-1", "maison", sold_out=True),
            }
        )
        monitor = CatalogMonitor(
            self.db,
            fetcher=fetcher,
            minimum_counts={"fragrance": 1, "discovery": 1, "maison": 1},
        )

        result = monitor.run_cycle(observed_at="2026-10-29T22:00:00Z")

        self.assertEqual(result.product_count, 3)
        self.assertEqual(result.events_created, 0)
        self.assertEqual(len(fetcher.calls), 3)
        self.assertTrue(all("monitor=" in url for url in fetcher.calls))

    def test_incomplete_collection_preserves_last_known_state(self):
        good = FakeFetcher(
            {
                "/fragrance?": catalog_card("frag-1", "fragrance"),
                "/discovery?": catalog_card("sample-1", "discovery"),
                "/maison?": catalog_card("candle-1", "maison"),
            }
        )
        monitor = CatalogMonitor(
            self.db,
            fetcher=good,
            minimum_counts={"fragrance": 1, "discovery": 1, "maison": 1},
        )
        monitor.run_cycle(observed_at="2026-10-29T22:00:00Z")

        bad = FakeFetcher(
            {
                "/fragrance?": "<html>challenge</html>",
                "/discovery?": catalog_card("sample-1", "discovery"),
                "/maison?": catalog_card("candle-1", "maison"),
            }
        )
        monitor.fetcher = bad

        with self.assertRaises(CatalogSourceError):
            monitor.run_cycle(observed_at="2026-10-29T22:01:00Z")

        self.assertEqual(self.db.get_summary()["total_products"], 3)
        self.assertEqual(self.db.get_summary()["last_successful_check"], "2026-10-29T22:00:00Z")

    def test_large_collection_drop_preserves_last_known_state(self):
        full_fragrance = "".join(
            catalog_card(f"frag-{index}", "fragrance") for index in range(110)
        )
        partial_fragrance = "".join(
            catalog_card(f"frag-{index}", "fragrance") for index in range(100)
        )
        fetcher = FakeFetcher(
            {
                "/fragrance?": full_fragrance,
                "/discovery?": catalog_card("sample-1", "discovery"),
                "/maison?": catalog_card("candle-1", "maison"),
            }
        )
        monitor = CatalogMonitor(
            self.db,
            fetcher=fetcher,
            minimum_counts={"fragrance": 100, "discovery": 1, "maison": 1},
        )
        monitor.run_cycle(observed_at="2026-10-29T22:00:00Z")
        fetcher.pages["/fragrance?"] = partial_fragrance

        with self.assertRaises(CatalogSourceError):
            monitor.run_cycle(observed_at="2026-10-29T22:01:00Z")

        self.assertEqual(self.db.get_summary()["total_products"], 112)
        self.assertEqual(self.db.list_events(), [])


if __name__ == "__main__":
    unittest.main()
