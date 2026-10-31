import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from montagne_monitor.api import DashboardApi
from montagne_monitor.db import MonitorDatabase
from montagne_monitor.models import CatalogProduct


class DashboardApiTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = MonitorDatabase(Path(self.tempdir.name) / "monitor.db")
        self.db.apply_catalog_snapshot(
            [
                CatalogProduct(
                    product_id="a",
                    collection="fragrance",
                    name="Product A",
                    url_path="/fragrance/a",
                    image_url="https://images.example/a.jpg",
                    category="unisex",
                    status="in_stock",
                    price_cents=4500,
                )
            ],
            observed_at="2026-10-29T22:00:00Z",
        )
        self.api = DashboardApi(self.db, token="secret-token-with-adequate-length")

    def tearDown(self):
        self.db.close()
        self.tempdir.cleanup()

    def test_rejects_missing_token(self):
        response = self.api.route("GET", "/api/state", {})
        self.assertEqual(response.status, 401)

    def test_returns_public_state_with_cache_metadata(self):
        response = self.api.route(
            "GET", "/api/state", {"authorization": "Bearer secret-token-with-adequate-length"}
        )
        payload = json.loads(response.body)

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["summary"]["total_products"], 1)
        self.assertEqual(payload["products"][0]["product_id"], "a")
        self.assertNotIn("is_active", payload["products"][0])
        self.assertIn("revision", payload)

    def test_returns_product_history_and_404_for_unknown_product(self):
        found = self.api.route(
            "GET", "/api/products/a", {"authorization": "Bearer secret-token-with-adequate-length"}
        )
        missing = self.api.route(
            "GET", "/api/products/missing", {"authorization": "Bearer secret-token-with-adequate-length"}
        )

        self.assertEqual(found.status, 200)
        self.assertEqual(json.loads(found.body)["product"]["name"], "Product A")
        self.assertEqual(missing.status, 404)

    def test_full_event_history_and_seven_day_activity_are_not_truncated(self):
        started_at = datetime.now(timezone.utc) - timedelta(hours=10)
        for index in range(275):
            observed_at = (started_at + timedelta(minutes=index)).isoformat().replace(
                "+00:00", "Z"
            )
            self.db.apply_catalog_snapshot(
                [
                    CatalogProduct(
                        product_id="a",
                        collection="fragrance",
                        name="Product A",
                        url_path="/fragrance/a",
                        image_url="https://images.example/a.jpg",
                        category="unisex",
                        status="in_stock",
                        price_cents=4600 + index,
                    )
                ],
                observed_at=observed_at,
            )

        for index in range(202):
            observed_at = (
                started_at + timedelta(minutes=275 + index)
            ).isoformat().replace("+00:00", "Z")
            self.db.apply_catalog_snapshot(
                [
                    CatalogProduct(
                        product_id="a",
                        collection="fragrance",
                        name="Product A",
                        url_path="/fragrance/a",
                        image_url="https://images.example/a.jpg",
                        category="unisex",
                        status="out_of_stock" if index % 2 == 0 else "in_stock",
                        price_cents=4874,
                    )
                ],
                observed_at=observed_at,
            )

        headers = {"authorization": "Bearer secret-token-with-adequate-length"}
        state = json.loads(self.api.route("GET", "/api/state", headers).body)
        history = json.loads(self.api.route("GET", "/api/events", headers).body)
        product_history = json.loads(
            self.api.route("GET", "/api/products/a", headers).body
        )

        self.assertEqual(len(state["events"]), 60)
        self.assertEqual(len(state["activity_events"]), 477)
        self.assertEqual(len(history["events"]), 477)
        self.assertEqual(len(product_history["events"]), 477)
        self.assertEqual(len(product_history["periods"]), 102)
        self.assertEqual(product_history["product"]["restock_count"], 101)


if __name__ == "__main__":
    unittest.main()
