import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil
from typing import Callable, Optional

from .db import MonitorDatabase
from .parser import parse_catalog_html, parse_product_context


BASE_URL = "https://www.montagneparfums.com"
COLLECTIONS = {
    "fragrance": "/fragrance",
    "discovery": "/discovery",
    "maison": "/maison",
}
DEFAULT_MINIMUM_COUNTS = {"fragrance": 100, "discovery": 1, "maison": 1}


class CatalogSourceError(RuntimeError):
    pass


@dataclass(frozen=True)
class CycleResult:
    product_count: int
    events_created: int
    baseline_created: bool
    elapsed_seconds: float


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def fetch_text(url: str, timeout: float = 30) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise CatalogSourceError(f"Source returned HTTP {response.status}")
            return response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise CatalogSourceError(f"Source request failed: {exc}") from exc


class CatalogMonitor:
    def __init__(
        self,
        database: MonitorDatabase,
        *,
        fetcher: Callable[[str], str] = fetch_text,
        minimum_counts: Optional[dict[str, int]] = None,
    ) -> None:
        self.database = database
        self.fetcher = fetcher
        self.minimum_counts = minimum_counts or DEFAULT_MINIMUM_COUNTS
        self._detail_cursor = 0

    def _collection_url(self, path: str) -> str:
        separator = "&" if "?" in path else "?"
        return f"{BASE_URL}{path}{separator}monitor={int(time.time() * 1000)}"

    def run_cycle(self, observed_at: Optional[str] = None) -> CycleResult:
        started = time.perf_counter()
        timestamp = observed_at or utc_now()
        all_products = []
        previous_counts: dict[str, int] = {}
        for product in self.database.list_products():
            collection = product["collection_name"]
            previous_counts[collection] = previous_counts.get(collection, 0) + 1

        for collection, path in COLLECTIONS.items():
            source = self.fetcher(self._collection_url(path))
            products = parse_catalog_html(source, collection)
            minimum = self.minimum_counts.get(collection, 1)
            if len(products) < minimum:
                raise CatalogSourceError(
                    f"{collection} parsed {len(products)} products; expected at least {minimum}"
                )
            previous_count = previous_counts.get(collection, 0)
            safe_previous_floor = ceil(previous_count * 0.95)
            if previous_count and len(products) < safe_previous_floor:
                raise CatalogSourceError(
                    f"{collection} parsed {len(products)} products; previous complete snapshot "
                    f"contained {previous_count}, below the 95% safety floor of "
                    f"{safe_previous_floor}"
                )
            all_products.extend(products)

        product_ids = [product.product_id for product in all_products]
        if len(product_ids) != len(set(product_ids)):
            raise CatalogSourceError("Catalog contained duplicate product IDs")

        result = self.database.apply_catalog_snapshot(all_products, timestamp)
        return CycleResult(
            product_count=len(all_products),
            events_created=result.events_created,
            baseline_created=result.baseline_created,
            elapsed_seconds=time.perf_counter() - started,
        )

    def enrich_product(self, product_id: str, observed_at: Optional[str] = None) -> bool:
        product = self.database.get_product(product_id)
        if not product or not product.get("url_path"):
            return False
        source = self.fetcher(self._collection_url(product["url_path"]))
        detail = parse_product_context(source)
        if detail.product_id != product_id:
            raise CatalogSourceError(
                f"Product detail identity mismatch: expected {product_id}, got {detail.product_id}"
            )
        self.database.enrich_product(
            product_id=product_id,
            variant_id=detail.variant_id,
            sku=detail.sku,
            quantity=detail.quantity,
            price_cents=detail.price_cents,
            observed_at=observed_at or utc_now(),
        )
        return True

    def enrich_next_product(self, observed_at: Optional[str] = None) -> Optional[str]:
        products = self.database.list_products()
        if not products:
            return None
        self._detail_cursor %= len(products)
        product_id = products[self._detail_cursor]["product_id"]
        self._detail_cursor = (self._detail_cursor + 1) % len(products)
        self.enrich_product(product_id, observed_at=observed_at)
        return product_id
