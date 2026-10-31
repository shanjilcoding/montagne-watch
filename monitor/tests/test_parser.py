import unittest

from montagne_monitor.parser import parse_catalog_html, parse_product_context


CATALOG_HTML = """
<section class="ProductList products-collection-v2">
  <div class="ProductList-item hentry category-all-fragrance category-unisex post-type-store-item article-index-1 featured sold-out clear"
       id="thumb-vetiver-rush" data-item-id="product-1">
    <a href="/fragrance/vetiver-rush" class="ProductList-item-link"></a>
    <img data-src="https://images.example/vetiver.jpg" alt="Vetiver Rush">
    <h1 class="ProductList-title">VETIVER RUSH INSPIRED BY CREED WILD VETIVER</h1>
    <div class="product-price">$45.00</div>
  </div>
  <div class="ProductList-item hentry category-all-fragrance category-men post-type-store-item article-index-2 featured clear"
       id="thumb-pineapple-musk" data-item-id="product-2">
    <a href="/fragrance/pineapple-musk" class="ProductList-item-link"></a>
    <img data-src="https://images.example/pineapple.jpg" alt="Pineapple Musk">
    <h1 class="ProductList-title">PINEAPPLE MUSK INSPIRED BY CREED AVENTUS</h1>
    <div class="product-price"><span class="sqs-money-native">$60.00</span></div>
  </div>
</section>
"""

PRODUCT_HTML = """
<script data-name="static-context">Static = window.Static || {}; Static.SQUARESPACE_CONTEXT = {"item":{"id":"product-2","title":"PINEAPPLE MUSK INSPIRED BY CREED AVENTUS","fullUrl":"/fragrance/pineapple-musk"},"product":{"variantAttributeNames":[],"variants":[{"id":"variant-2","sku":"P. MUSK 50ML","price":{"currencyCode":"USD","value":6000,"decimalValue":"60.00","fractionalDigits":2},"salePrice":{"currencyCode":"USD","value":0,"decimalValue":"0.00","fractionalDigits":2},"onSale":false,"stock":{"unlimited":false,"quantity":7},"attributes":{}}],"productType":1}};</script>
"""


class CatalogParserTests(unittest.TestCase):
    def test_parses_all_products_and_stock_status(self):
        products = parse_catalog_html(CATALOG_HTML, "fragrance")

        self.assertEqual(len(products), 2)
        sold_out, available = products
        self.assertEqual(sold_out.product_id, "product-1")
        self.assertEqual(sold_out.status, "out_of_stock")
        self.assertEqual(sold_out.category, "unisex")
        self.assertEqual(sold_out.price_cents, 4500)
        self.assertEqual(available.status, "in_stock")
        self.assertEqual(available.category, "men")
        self.assertEqual(available.image_url, "https://images.example/pineapple.jpg")

    def test_parses_exact_variant_quantity_from_product_context(self):
        detail = parse_product_context(PRODUCT_HTML)

        self.assertEqual(detail.product_id, "product-2")
        self.assertEqual(detail.variant_id, "variant-2")
        self.assertEqual(detail.sku, "P. MUSK 50ML")
        self.assertEqual(detail.quantity, 7)
        self.assertEqual(detail.price_cents, 6000)
        self.assertEqual(detail.status, "in_stock")


if __name__ == "__main__":
    unittest.main()
