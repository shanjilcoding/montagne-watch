import tempfile
import unittest
from pathlib import Path

from montagne_monitor.db import MonitorDatabase
from montagne_monitor.models import CatalogProduct


def product(product_id: str, status: str, price_cents: int = 4500) -> CatalogProduct:
    return CatalogProduct(
        product_id=product_id,
        collection="fragrance",
        name=f"Product {product_id}",
        url_path=f"/fragrance/{product_id}",
        image_url=f"https://images.example/{product_id}.jpg",
        category="unisex",
        status=status,
        price_cents=price_cents,
    )


class MonitorDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = MonitorDatabase(Path(self.tempdir.name) / "monitor.db")

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    def test_initial_snapshot_is_a_silent_baseline(self):
        result = self.db.apply_catalog_snapshot(
            [product("a", "out_of_stock"), product("b", "in_stock")],
            observed_at="2026-10-29T22:00:00Z",
        )

        self.assertTrue(result.baseline_created)
        self.assertEqual(result.events_created, 0)
        self.assertEqual(self.db.get_summary()["total_products"], 2)
        self.assertEqual(self.db.list_events(), [])

    def test_status_transitions_create_events_and_availability_periods(self):
        self.db.apply_catalog_snapshot(
            [product("a", "out_of_stock"), product("b", "in_stock")],
            observed_at="2026-10-29T22:00:00Z",
        )
        self.db.enrich_product(
            product_id="a",
            variant_id="variant-a",
            sku="SKU A",
            quantity=0,
            price_cents=4500,
            observed_at="2026-10-29T22:01:00Z",
        )

        result = self.db.apply_catalog_snapshot(
            [product("a", "in_stock"), product("b", "out_of_stock")],
            observed_at="2026-10-29T22:10:00Z",
        )

        self.assertEqual(result.events_created, 2)
        events = self.db.list_events(limit=10)
        self.assertEqual({event["event_type"] for event in events}, {"restock", "sold_out"})
        sold_out = next(event for event in events if event["event_type"] == "sold_out")
        self.assertEqual(sold_out["duration_seconds"], 600)

        self.db.enrich_product(
            product_id="a",
            variant_id="variant-a",
            sku="SKU A",
            quantity=7,
            price_cents=4500,
            observed_at="2026-10-29T22:11:00Z",
        )
        self.assertEqual(self.db.list_periods("a")[0]["starting_quantity"], 7)

        products = {item["product_id"]: item for item in self.db.list_products()}
        self.assertEqual(products["a"]["last_restock_at"], "2026-10-29T22:10:00Z")
        self.assertEqual(products["a"]["current_in_stock_since"], "2026-10-29T22:10:00Z")
        self.assertEqual(products["a"]["restock_count"], 1)
        self.assertEqual(products["b"]["last_sold_out_at"], "2026-10-29T22:10:00Z")
        self.assertEqual(products["b"]["last_in_stock_duration_seconds"], 600)
        self.assertEqual(products["b"]["average_in_stock_duration_seconds"], 600)

    def test_new_removed_and_price_change_events_are_deduplicated(self):
        self.db.apply_catalog_snapshot(
            [product("a", "in_stock")],
            observed_at="2026-10-29T22:00:00Z",
        )
        changed = [product("a", "in_stock", 5000), product("b", "out_of_stock")]

        first = self.db.apply_catalog_snapshot(changed, observed_at="2026-10-29T22:05:00Z")
        second = self.db.apply_catalog_snapshot(changed, observed_at="2026-10-29T22:05:00Z")
        removed = self.db.apply_catalog_snapshot(
            [product("b", "out_of_stock")],
            observed_at="2026-10-29T22:06:00Z",
        )

        self.assertEqual(first.events_created, 2)
        self.assertEqual(second.events_created, 0)
        self.assertEqual(removed.events_created, 1)
        self.assertEqual(
            {event["event_type"] for event in self.db.list_events(limit=10)},
            {"new_product", "price_change", "removed"},
        )

    def test_product_detail_enrichment_updates_quantity_without_fake_restock(self):
        self.db.apply_catalog_snapshot(
            [product("a", "in_stock")],
            observed_at="2026-10-29T22:00:00Z",
        )

        self.db.enrich_product(
            product_id="a",
            variant_id="variant-a",
            sku="SKU A",
            quantity=9,
            price_cents=4500,
            observed_at="2026-10-29T22:01:00Z",
        )

        item = self.db.get_product("a")
        self.assertEqual(item["observed_quantity"], 9)
        self.assertEqual(item["sku"], "SKU A")
        self.assertEqual(self.db.list_events(), [])

    def test_product_detail_price_change_creates_event(self):
        self.db.apply_catalog_snapshot(
            [product("a", "in_stock")],
            observed_at="2026-10-29T22:00:00Z",
        )

        self.db.enrich_product(
            product_id="a",
            variant_id="variant-a",
            sku="SKU A",
            quantity=9,
            price_cents=5000,
            observed_at="2026-10-29T22:02:00Z",
        )

        events = self.db.list_events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "price_change")
        self.assertEqual(events[0]["previous_price_cents"], 4500)
        self.assertEqual(events[0]["new_price_cents"], 5000)


if __name__ == "__main__":
    unittest.main()
