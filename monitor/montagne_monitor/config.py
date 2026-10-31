import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    api_token: str
    api_host: str
    api_port: int
    catalog_interval_seconds: int
    detail_interval_seconds: int


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_settings(project_root: Path) -> Settings:
    _load_env_file(project_root / ".env")
    token = os.environ.get("MONTAGNE_API_TOKEN", "")
    if len(token) < 24:
        raise RuntimeError("MONTAGNE_API_TOKEN must be configured with at least 24 characters")
    return Settings(
        database_path=Path(
            os.environ.get("MONTAGNE_DATABASE_PATH", project_root / "data" / "monitor.db")
        ),
        api_token=token,
        api_host=os.environ.get("MONTAGNE_API_HOST", "127.0.0.1"),
        api_port=int(os.environ.get("MONTAGNE_API_PORT", "8791")),
        catalog_interval_seconds=max(
            15, int(os.environ.get("MONTAGNE_CATALOG_INTERVAL_SECONDS", "30"))
        ),
        detail_interval_seconds=max(
            30, int(os.environ.get("MONTAGNE_DETAIL_INTERVAL_SECONDS", "60"))
        ),
    )
