import hmac
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Mapping, Optional
from urllib.parse import unquote, urlparse

from .db import MonitorDatabase


PUBLIC_PRODUCT_FIELDS = (
    "product_id",
    "variant_id",
    "sku",
    "collection_name",
    "name",
    "url_path",
    "image_url",
    "category",
    "price_cents",
    "current_status",
    "observed_quantity",
    "quantity_observed_at",
    "first_seen_at",
    "last_checked_at",
    "last_changed_at",
    "last_restock_at",
    "last_sold_out_at",
    "current_in_stock_since",
    "last_in_stock_duration_seconds",
    "average_in_stock_duration_seconds",
    "restock_count",
)
PUBLIC_EVENT_FIELDS = (
    "event_id",
    "product_id",
    "event_type",
    "previous_status",
    "new_status",
    "previous_quantity",
    "new_quantity",
    "previous_price_cents",
    "new_price_cents",
    "duration_seconds",
    "observed_at",
    "name",
    "url_path",
    "image_url",
    "price_cents",
    "category",
)
PUBLIC_PERIOD_FIELDS = (
    "period_id",
    "product_id",
    "started_at",
    "ended_at",
    "duration_seconds",
    "ending_reason",
    "starting_quantity",
)


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: str
    headers: dict[str, str]


def _public_row(row: dict, fields: tuple[str, ...]) -> dict:
    return {field: row.get(field) for field in fields}


class DashboardApi:
    def __init__(self, database: MonitorDatabase, token: str) -> None:
        if len(token) < 24:
            raise ValueError("Dashboard API token must contain at least 24 characters")
        self.database = database
        self.token = token

    def _json(self, status: int, payload: dict) -> ApiResponse:
        return ApiResponse(
            status=status,
            body=json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
            },
        )

    def _authorized(self, headers: Mapping[str, str]) -> bool:
        authorization = headers.get("authorization", "")
        expected = f"Bearer {self.token}"
        return hmac.compare_digest(authorization, expected)

    def route(self, method: str, raw_path: str, headers: Mapping[str, str]) -> ApiResponse:
        path = urlparse(raw_path).path.rstrip("/") or "/"
        normalized_headers = {key.lower(): value for key, value in headers.items()}

        if method != "GET":
            return self._json(405, {"error": "method_not_allowed"})

        if path == "/health":
            summary = self.database.get_summary()
            return self._json(
                200,
                {
                    "status": "ok" if summary.get("last_successful_check") else "starting",
                    "last_successful_check": summary.get("last_successful_check"),
                },
            )

        if not self._authorized(normalized_headers):
            return self._json(401, {"error": "unauthorized"})

        if path == "/api/state":
            raw = self.database.public_state(event_limit=60)
            products = [_public_row(row, PUBLIC_PRODUCT_FIELDS) for row in raw["products"]]
            events = [_public_row(row, PUBLIC_EVENT_FIELDS) for row in raw["events"]]
            activity_cutoff = (
                datetime.now(timezone.utc) - timedelta(days=7)
            ).isoformat().replace("+00:00", "Z")
            activity_events = [
                _public_row(row, PUBLIC_EVENT_FIELDS)
                for row in self.database.list_events_since(activity_cutoff)
            ]
            revision = raw["summary"].get("last_successful_check") or "starting"
            return self._json(
                200,
                {
                    "revision": revision,
                    "summary": raw["summary"],
                    "products": products,
                    "events": events,
                    "activity_events": activity_events,
                },
            )

        if path == "/api/events":
            events = [
                _public_row(row, PUBLIC_EVENT_FIELDS)
                for row in self.database.list_events(limit=None)
            ]
            return self._json(200, {"events": events})

        prefix = "/api/products/"
        if path.startswith(prefix):
            product_id = unquote(path[len(prefix) :])
            payload = self.database.product_payload(product_id)
            if payload is None:
                return self._json(404, {"error": "product_not_found"})
            return self._json(
                200,
                {
                    "product": _public_row(payload["product"], PUBLIC_PRODUCT_FIELDS),
                    "events": [
                        _public_row(row, PUBLIC_EVENT_FIELDS) for row in payload["events"]
                    ],
                    "periods": [
                        _public_row(row, PUBLIC_PERIOD_FIELDS) for row in payload["periods"]
                    ],
                },
            )

        return self._json(404, {"error": "not_found"})


def make_handler(api: DashboardApi):
    class Handler(BaseHTTPRequestHandler):
        server_version = "MontagneDashboard/1.0"

        def do_GET(self) -> None:
            response = api.route("GET", self.path, dict(self.headers.items()))
            self.send_response(response.status)
            for key, value in response.headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(response.body.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(response.body.encode("utf-8"))

        def do_POST(self) -> None:
            response = api.route("POST", self.path, dict(self.headers.items()))
            self.send_response(response.status)
            for key, value in response.headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response.body.encode("utf-8"))

        def log_message(self, format_string: str, *args) -> None:
            return

    return Handler


def start_api_server(
    database: MonitorDatabase,
    token: str,
    host: str = "127.0.0.1",
    port: int = 8791,
) -> ThreadingHTTPServer:
    api = DashboardApi(database, token)
    server = ThreadingHTTPServer((host, port), make_handler(api))
    thread = threading.Thread(target=server.serve_forever, name="dashboard-api", daemon=True)
    thread.start()
    return server
