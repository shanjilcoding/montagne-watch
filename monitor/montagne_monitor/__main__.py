import signal
import sys
import threading
import time
from pathlib import Path

from .api import start_api_server
from .config import load_settings
from .db import MonitorDatabase
from .service import CatalogMonitor, CatalogSourceError, utc_now


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def run() -> int:
    settings = load_settings(PROJECT_ROOT)
    database = MonitorDatabase(settings.database_path)
    monitor = CatalogMonitor(database)
    server = start_api_server(
        database,
        settings.api_token,
        host=settings.api_host,
        port=settings.api_port,
    )
    stop_event = threading.Event()

    def stop(*_args) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    log(
        "monitor_started "
        f"api={settings.api_host}:{settings.api_port} "
        f"catalog_interval={settings.catalog_interval_seconds}s "
        f"detail_interval={settings.detail_interval_seconds}s"
    )

    next_catalog = 0.0
    next_detail = 0.0
    cycle = 0
    try:
        while not stop_event.is_set():
            now = time.monotonic()
            if now >= next_catalog:
                cycle += 1
                try:
                    result = monitor.run_cycle()
                    log(
                        "catalog_cycle_ok "
                        f"cycle={cycle} products={result.product_count} "
                        f"events={result.events_created} baseline={result.baseline_created} "
                        f"elapsed={result.elapsed_seconds:.3f}s"
                    )
                except Exception as exc:
                    log(f"catalog_cycle_failed cycle={cycle} error={type(exc).__name__}: {exc}")
                next_catalog = time.monotonic() + settings.catalog_interval_seconds

            now = time.monotonic()
            if now >= next_detail:
                try:
                    product_id = monitor.enrich_next_product()
                    if product_id:
                        log(f"detail_refresh_ok product_id={product_id}")
                except (CatalogSourceError, ValueError) as exc:
                    log(f"detail_refresh_failed error={type(exc).__name__}: {exc}")
                next_detail = time.monotonic() + settings.detail_interval_seconds

            stop_event.wait(0.5)
    finally:
        server.shutdown()
        server.server_close()
        database.close()
        log("monitor_stopped")
    return 0


if __name__ == "__main__":
    sys.exit(run())
