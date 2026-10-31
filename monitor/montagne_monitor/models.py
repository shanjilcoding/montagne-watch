from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CatalogProduct:
    product_id: str
    collection: str
    name: str
    url_path: str
    image_url: str
    category: str
    status: str
    price_cents: Optional[int]


@dataclass(frozen=True)
class ProductDetail:
    product_id: str
    variant_id: str
    sku: str
    quantity: Optional[int]
    unlimited: bool
    price_cents: int
    status: str
