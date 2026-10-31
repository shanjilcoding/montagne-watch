import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from .models import CatalogProduct


@dataclass(frozen=True)
class SnapshotResult:
    baseline_created: bool
    events_created: int


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _event_key(product_id: str, event_type: str, observed_at: str, suffix: str = "") -> str:
    return f"{product_id}:{event_type}:{observed_at}:{suffix}"


class MonitorDatabase:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=10000")
        self._initialize()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                variant_id TEXT,
                sku TEXT,
                collection_name TEXT NOT NULL,
                name TEXT NOT NULL,
                url_path TEXT NOT NULL,
                image_url TEXT NOT NULL,
                category TEXT NOT NULL,
                price_cents INTEGER,
                current_status TEXT NOT NULL,
                observed_quantity INTEGER,
                quantity_observed_at TEXT,
                first_seen_at TEXT NOT NULL,
                last_checked_at TEXT NOT NULL,
                last_changed_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_key TEXT NOT NULL UNIQUE,
                product_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                previous_status TEXT,
                new_status TEXT,
                previous_quantity INTEGER,
                new_quantity INTEGER,
                previous_price_cents INTEGER,
                new_price_cents INTEGER,
                duration_seconds INTEGER,
                observed_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(product_id)
            );

            CREATE TABLE IF NOT EXISTS availability_periods (
                period_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds INTEGER,
                ending_reason TEXT,
                starting_quantity INTEGER,
                UNIQUE(product_id, started_at),
                FOREIGN KEY(product_id) REFERENCES products(product_id)
            );

            CREATE INDEX IF NOT EXISTS idx_events_observed_at ON events(observed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_product ON events(product_id, observed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_products_status ON products(is_active, current_status);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def _metadata(self, key: str) -> Optional[str]:
        row = self.connection.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def _set_metadata(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO metadata(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def _insert_product(self, item: CatalogProduct, observed_at: str) -> None:
        self.connection.execute(
            """
            INSERT INTO products(
                product_id, collection_name, name, url_path, image_url, category,
                price_cents, current_status, first_seen_at, last_checked_at,
                last_changed_at, is_active
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                item.product_id,
                item.collection,
                item.name,
                item.url_path,
                item.image_url,
                item.category,
                item.price_cents,
                item.status,
                observed_at,
                observed_at,
                observed_at,
            ),
        )

    def _insert_event(
        self,
        *,
        product_id: str,
        event_type: str,
        observed_at: str,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None,
        previous_quantity: Optional[int] = None,
        new_quantity: Optional[int] = None,
        previous_price_cents: Optional[int] = None,
        new_price_cents: Optional[int] = None,
        duration_seconds: Optional[int] = None,
        suffix: str = "",
    ) -> int:
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO events(
                event_key, product_id, event_type, previous_status, new_status,
                previous_quantity, new_quantity, previous_price_cents,
                new_price_cents, duration_seconds, observed_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _event_key(product_id, event_type, observed_at, suffix),
                product_id,
                event_type,
                previous_status,
                new_status,
                previous_quantity,
                new_quantity,
                previous_price_cents,
                new_price_cents,
                duration_seconds,
                observed_at,
            ),
        )
        return cursor.rowcount

    def _open_period(self, product_id: str, observed_at: str, quantity: Optional[int] = None) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO availability_periods(product_id, started_at, starting_quantity) "
            "VALUES(?, ?, ?)",
            (product_id, observed_at, quantity),
        )

    def _close_period(self, product_id: str, observed_at: str, reason: str) -> Optional[int]:
        row = self.connection.execute(
            "SELECT period_id, started_at FROM availability_periods "
            "WHERE product_id = ? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
            (product_id,),
        ).fetchone()
        if not row:
            return None
        duration = max(0, int((_parse_time(observed_at) - _parse_time(row["started_at"])).total_seconds()))
        self.connection.execute(
            "UPDATE availability_periods SET ended_at = ?, duration_seconds = ?, ending_reason = ? "
            "WHERE period_id = ?",
            (observed_at, duration, reason, row["period_id"]),
        )
        return duration

    def apply_catalog_snapshot(
        self, products: Iterable[CatalogProduct], observed_at: str
    ) -> SnapshotResult:
        items = list(products)
        ids = [item.product_id for item in items]
        if len(ids) != len(set(ids)):
            raise ValueError("Catalog snapshot contains duplicate product IDs")
        baseline = self._metadata("baseline_created_at") is None
        events_created = 0

        with self.connection:
            existing = {
                row["product_id"]: row
                for row in self.connection.execute("SELECT * FROM products WHERE is_active = 1")
            }

            if baseline:
                for item in items:
                    self._insert_product(item, observed_at)
                    if item.status == "in_stock":
                        self._open_period(item.product_id, observed_at)
                self._set_metadata("baseline_created_at", observed_at)
                self._set_metadata("last_successful_check", observed_at)
                self._set_metadata("last_product_count", str(len(items)))
                return SnapshotResult(baseline_created=True, events_created=0)

            current_ids = set(ids)
            for item in items:
                old = existing.get(item.product_id)
                if old is None:
                    inactive = self.connection.execute(
                        "SELECT * FROM products WHERE product_id = ?", (item.product_id,)
                    ).fetchone()
                    if inactive:
                        self.connection.execute(
                            """
                            UPDATE products SET collection_name=?, name=?, url_path=?, image_url=?,
                                category=?, price_cents=?, current_status=?, last_checked_at=?,
                                last_changed_at=?, is_active=1
                            WHERE product_id=?
                            """,
                            (
                                item.collection,
                                item.name,
                                item.url_path,
                                item.image_url,
                                item.category,
                                item.price_cents,
                                item.status,
                                observed_at,
                                observed_at,
                                item.product_id,
                            ),
                        )
                    else:
                        self._insert_product(item, observed_at)
                    events_created += self._insert_event(
                        product_id=item.product_id,
                        event_type="new_product",
                        observed_at=observed_at,
                        new_status=item.status,
                        new_price_cents=item.price_cents,
                    )
                    if item.status == "in_stock":
                        self._open_period(item.product_id, observed_at)
                    continue

                changed_at = old["last_changed_at"]
                if old["price_cents"] != item.price_cents:
                    events_created += self._insert_event(
                        product_id=item.product_id,
                        event_type="price_change",
                        observed_at=observed_at,
                        previous_price_cents=old["price_cents"],
                        new_price_cents=item.price_cents,
                    )
                    changed_at = observed_at

                if old["current_status"] != item.status:
                    event_type = "restock" if item.status == "in_stock" else "sold_out"
                    duration = None
                    if event_type == "restock":
                        self._open_period(item.product_id, observed_at)
                    else:
                        duration = self._close_period(item.product_id, observed_at, "sold_out")
                    events_created += self._insert_event(
                        product_id=item.product_id,
                        event_type=event_type,
                        observed_at=observed_at,
                        previous_status=old["current_status"],
                        new_status=item.status,
                        previous_quantity=old["observed_quantity"],
                        duration_seconds=duration,
                    )
                    changed_at = observed_at

                self.connection.execute(
                    """
                    UPDATE products SET collection_name=?, name=?, url_path=?, image_url=?,
                        category=?, price_cents=?, current_status=?, last_checked_at=?,
                        last_changed_at=?, is_active=1
                    WHERE product_id=?
                    """,
                    (
                        item.collection,
                        item.name,
                        item.url_path,
                        item.image_url,
                        item.category,
                        item.price_cents,
                        item.status,
                        observed_at,
                        changed_at,
                        item.product_id,
                    ),
                )

            for product_id, old in existing.items():
                if product_id in current_ids:
                    continue
                duration = None
                if old["current_status"] == "in_stock":
                    duration = self._close_period(product_id, observed_at, "removed")
                events_created += self._insert_event(
                    product_id=product_id,
                    event_type="removed",
                    observed_at=observed_at,
                    previous_status=old["current_status"],
                    duration_seconds=duration,
                )
                self.connection.execute(
                    "UPDATE products SET is_active=0, last_checked_at=?, last_changed_at=? WHERE product_id=?",
                    (observed_at, observed_at, product_id),
                )

            self._set_metadata("last_successful_check", observed_at)
            self._set_metadata("last_product_count", str(len(items)))

        return SnapshotResult(baseline_created=False, events_created=events_created)

    def enrich_product(
        self,
        *,
        product_id: str,
        variant_id: str,
        sku: str,
        quantity: Optional[int],
        price_cents: int,
        observed_at: str,
    ) -> None:
        with self.connection:
            existing = self.connection.execute(
                "SELECT price_cents, last_changed_at FROM products WHERE product_id=?",
                (product_id,),
            ).fetchone()
            if existing is None:
                return
            price_changed = (
                existing["price_cents"] is not None
                and existing["price_cents"] != price_cents
            )
            if price_changed:
                self._insert_event(
                    product_id=product_id,
                    event_type="price_change",
                    observed_at=observed_at,
                    previous_price_cents=existing["price_cents"],
                    new_price_cents=price_cents,
                )
            self.connection.execute(
                """
                UPDATE products SET variant_id=?, sku=?, observed_quantity=?,
                    quantity_observed_at=?, price_cents=?, last_changed_at=?
                WHERE product_id=?
                """,
                (
                    variant_id,
                    sku,
                    quantity,
                    observed_at,
                    price_cents,
                    observed_at if price_changed else existing["last_changed_at"],
                    product_id,
                ),
            )
            self.connection.execute(
                "UPDATE availability_periods SET starting_quantity=COALESCE(starting_quantity, ?) "
                "WHERE product_id=? AND ended_at IS NULL",
                (quantity, product_id),
            )

    def get_product(self, product_id: str) -> Optional[dict]:
        row = self.connection.execute(
            """
            SELECT p.*,
                   (SELECT MAX(e.observed_at) FROM events e
                    WHERE e.product_id=p.product_id AND e.event_type='restock') AS last_restock_at,
                   (SELECT MAX(e.observed_at) FROM events e
                    WHERE e.product_id=p.product_id AND e.event_type='sold_out') AS last_sold_out_at,
                   (SELECT ap.started_at FROM availability_periods ap
                    WHERE ap.product_id=p.product_id AND ap.ended_at IS NULL
                    ORDER BY ap.started_at DESC LIMIT 1) AS current_in_stock_since,
                   (SELECT ap.duration_seconds FROM availability_periods ap
                    WHERE ap.product_id=p.product_id AND ap.duration_seconds IS NOT NULL
                    ORDER BY ap.ended_at DESC LIMIT 1) AS last_in_stock_duration_seconds,
                   (SELECT CAST(ROUND(AVG(ap.duration_seconds)) AS INTEGER)
                    FROM availability_periods ap
                    WHERE ap.product_id=p.product_id AND ap.duration_seconds IS NOT NULL)
                    AS average_in_stock_duration_seconds,
                   (SELECT COUNT(*) FROM events e
                    WHERE e.product_id=p.product_id AND e.event_type='restock') AS restock_count
            FROM products p WHERE p.product_id = ?
            """,
            (product_id,),
        ).fetchone()
        return dict(row) if row else None

    def list_products(self, active_only: bool = True) -> list[dict]:
        where = "WHERE p.is_active = 1" if active_only else ""
        rows = self.connection.execute(
            f"""
            SELECT p.*,
                   (SELECT MAX(e.observed_at) FROM events e
                    WHERE e.product_id=p.product_id AND e.event_type='restock') AS last_restock_at,
                   (SELECT MAX(e.observed_at) FROM events e
                    WHERE e.product_id=p.product_id AND e.event_type='sold_out') AS last_sold_out_at,
                   (SELECT ap.started_at FROM availability_periods ap
                    WHERE ap.product_id=p.product_id AND ap.ended_at IS NULL
                    ORDER BY ap.started_at DESC LIMIT 1) AS current_in_stock_since,
                   (SELECT ap.duration_seconds FROM availability_periods ap
                    WHERE ap.product_id=p.product_id AND ap.duration_seconds IS NOT NULL
                    ORDER BY ap.ended_at DESC LIMIT 1) AS last_in_stock_duration_seconds,
                   (SELECT CAST(ROUND(AVG(ap.duration_seconds)) AS INTEGER)
                    FROM availability_periods ap
                    WHERE ap.product_id=p.product_id AND ap.duration_seconds IS NOT NULL)
                    AS average_in_stock_duration_seconds,
                   (SELECT COUNT(*) FROM events e
                    WHERE e.product_id=p.product_id AND e.event_type='restock') AS restock_count
            FROM products p {where}
            ORDER BY p.name COLLATE NOCASE
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def list_events(
        self, limit: Optional[int] = 100, product_id: Optional[str] = None
    ) -> list[dict]:
        params: list[object] = []
        where = ""
        if product_id:
            where = "WHERE e.product_id = ?"
            params.append(product_id)
        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT ?"
            params.append(limit)
        rows = self.connection.execute(
            f"""
            SELECT e.*, p.name, p.url_path, p.image_url, p.price_cents, p.category
            FROM events e JOIN products p ON p.product_id = e.product_id
            {where}
            ORDER BY e.observed_at DESC, e.event_id DESC {limit_clause}
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def list_events_since(self, observed_since: str) -> list[dict]:
        rows = self.connection.execute(
            """
            SELECT e.*, p.name, p.url_path, p.image_url, p.price_cents, p.category
            FROM events e JOIN products p ON p.product_id = e.product_id
            WHERE e.observed_at >= ?
            ORDER BY e.observed_at DESC, e.event_id DESC
            """,
            (observed_since,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_periods(self, product_id: str, limit: Optional[int] = 50) -> list[dict]:
        params: list[object] = [product_id]
        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT ?"
            params.append(limit)
        rows = self.connection.execute(
            f"SELECT * FROM availability_periods WHERE product_id=? "
            f"ORDER BY started_at DESC {limit_clause}",
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def get_summary(self) -> dict:
        counts = self.connection.execute(
            """
            SELECT COUNT(*) AS total_products,
                   SUM(CASE WHEN current_status='in_stock' THEN 1 ELSE 0 END) AS in_stock,
                   SUM(CASE WHEN current_status='out_of_stock' THEN 1 ELSE 0 END) AS sold_out,
                   SUM(CASE WHEN observed_quantity BETWEEN 1 AND 5 THEN 1 ELSE 0 END) AS low_stock
            FROM products WHERE is_active=1
            """
        ).fetchone()
        now = datetime.now(timezone.utc)
        cutoff_24h = (now - timedelta(hours=24)).isoformat().replace("+00:00", "Z")
        cutoff_7d = (now - timedelta(days=7)).isoformat().replace("+00:00", "Z")
        event_counts = self.connection.execute(
            """
            SELECT
                SUM(CASE WHEN event_type='restock' AND observed_at>=? THEN 1 ELSE 0 END) AS restocks_24h,
                SUM(CASE WHEN event_type='sold_out' AND observed_at>=? THEN 1 ELSE 0 END) AS sellouts_24h,
                SUM(CASE WHEN event_type='restock' AND observed_at>=? THEN 1 ELSE 0 END) AS restocks_7d
            FROM events
            """,
            (cutoff_24h, cutoff_24h, cutoff_7d),
        ).fetchone()
        durations = self.connection.execute(
            "SELECT AVG(duration_seconds) AS average_in_stock_seconds FROM availability_periods "
            "WHERE duration_seconds IS NOT NULL"
        ).fetchone()
        result = dict(counts)
        result.update(dict(event_counts))
        result.update(dict(durations))
        result["last_successful_check"] = self._metadata("last_successful_check")
        result["tracking_started_at"] = self._metadata("baseline_created_at")
        nullable = {"last_successful_check", "tracking_started_at", "average_in_stock_seconds"}
        return {
            key: (0 if value is None and key not in nullable else value)
            for key, value in result.items()
        }

    def public_state(self, event_limit: int = 50) -> dict:
        return {
            "summary": self.get_summary(),
            "products": self.list_products(),
            "events": self.list_events(limit=event_limit),
        }

    def product_payload(self, product_id: str) -> Optional[dict]:
        product = self.get_product(product_id)
        if product is None:
            return None
        return {
            "product": product,
            "events": self.list_events(limit=None, product_id=product_id),
            "periods": self.list_periods(product_id, limit=None),
        }
