import html
import json
import re
from html.parser import HTMLParser
from typing import Optional

from .models import CatalogProduct, ProductDetail


_PRICE_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]{1,2})?)")
_CATEGORY_RE = re.compile(r"\bcategory-(men|women|unisex)\b", re.IGNORECASE)


def _price_to_cents(text: str) -> Optional[int]:
    match = _PRICE_RE.search(text.replace(",", ""))
    if not match:
        return None
    return int(round(float(match.group(1)) * 100))


class _CatalogParser(HTMLParser):
    def __init__(self, collection: str) -> None:
        super().__init__(convert_charrefs=True)
        self.collection = collection
        self.products: list[CatalogProduct] = []
        self._card: Optional[dict] = None
        self._depth = 0
        self._capture_title = False
        self._price_depth: Optional[int] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        values = {key: value or "" for key, value in attrs}
        classes = values.get("class", "")

        if self._card is None and tag == "div" and "ProductList-item" in classes.split():
            category_match = _CATEGORY_RE.search(classes)
            self._card = {
                "product_id": values.get("data-item-id", ""),
                "classes": classes,
                "category": category_match.group(1).lower() if category_match else "other",
                "url_path": "",
                "image_url": "",
                "name_parts": [],
                "price_parts": [],
            }
            self._depth = 1
            return

        if self._card is None:
            return

        if tag == "div":
            self._depth += 1
        if tag == "a" and "ProductList-item-link" in classes.split():
            self._card["url_path"] = values.get("href", "")
        elif tag == "img" and not self._card["image_url"]:
            self._card["image_url"] = values.get("data-src") or values.get("src", "")
        elif tag in {"h1", "h2", "h3"} and "ProductList-title" in classes.split():
            self._capture_title = True
        elif tag == "div" and "product-price" in classes.split():
            self._price_depth = self._depth

    def handle_data(self, data: str) -> None:
        if self._card is None:
            return
        if self._capture_title:
            self._card["name_parts"].append(data)
        if self._price_depth is not None:
            self._card["price_parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._card is None:
            return

        if tag in {"h1", "h2", "h3"} and self._capture_title:
            self._capture_title = False

        if tag == "div":
            if self._price_depth == self._depth:
                self._price_depth = None
            self._depth -= 1
            if self._depth == 0:
                name = html.unescape(" ".join("".join(self._card["name_parts"]).split()))
                price_text = " ".join(self._card["price_parts"])
                self.products.append(
                    CatalogProduct(
                        product_id=self._card["product_id"],
                        collection=self.collection,
                        name=name,
                        url_path=self._card["url_path"],
                        image_url=self._card["image_url"],
                        category=self._card["category"],
                        status=(
                            "out_of_stock"
                            if "sold-out" in self._card["classes"].split()
                            else "in_stock"
                        ),
                        price_cents=_price_to_cents(price_text),
                    )
                )
                self._card = None


def parse_catalog_html(source: str, collection: str) -> list[CatalogProduct]:
    parser = _CatalogParser(collection)
    parser.feed(source)
    return parser.products


def parse_product_context(source: str) -> ProductDetail:
    marker = "Static.SQUARESPACE_CONTEXT = "
    start = source.find(marker)
    if start < 0:
        raise ValueError("Squarespace product context was not found")
    context, _ = json.JSONDecoder().raw_decode(source[start + len(marker) :])
    item = context.get("item") or {}
    variants = (context.get("product") or {}).get("variants") or []
    if not item.get("id") or not variants:
        raise ValueError("Product context did not contain an item and variant")
    variant = variants[0]
    stock = variant.get("stock") or {}
    unlimited = bool(stock.get("unlimited"))
    quantity = stock.get("quantity")
    if not unlimited and not isinstance(quantity, int):
        quantity = None
    price = variant.get("price") or {}
    price_cents = price.get("value")
    if not isinstance(price_cents, int):
        raise ValueError("Product variant did not contain a numeric price")
    status = "in_stock" if unlimited or (quantity is not None and quantity > 0) else "out_of_stock"
    return ProductDetail(
        product_id=item["id"],
        variant_id=variant.get("id", ""),
        sku=variant.get("sku", ""),
        quantity=quantity,
        unlimited=unlimited,
        price_cents=price_cents,
        status=status,
    )
