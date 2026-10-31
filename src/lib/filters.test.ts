import { describe, expect, it } from "vitest";

import { filterProducts, sortProducts } from "./filters";
import type { Product } from "./types";


const products: Product[] = [
  {
    product_id: "a",
    variant_id: null,
    sku: null,
    collection_name: "fragrance",
    name: "Pineapple Musk Inspired by Creed Aventus",
    url_path: "/fragrance/a",
    image_url: "",
    category: "men",
    price_cents: 6000,
    current_status: "in_stock",
    observed_quantity: 2,
    quantity_observed_at: "2026-10-29T22:00:00Z",
    first_seen_at: "2026-10-29T20:00:00Z",
    last_checked_at: "2026-10-29T23:00:00Z",
    last_changed_at: "2026-10-29T22:00:00Z",
    last_restock_at: "2026-10-29T22:00:00Z",
    last_sold_out_at: null,
    current_in_stock_since: "2026-10-29T22:00:00Z",
    last_in_stock_duration_seconds: null,
    average_in_stock_duration_seconds: null,
    restock_count: 1,
  },
  {
    product_id: "b",
    variant_id: null,
    sku: null,
    collection_name: "fragrance",
    name: "Vetiver Rush Inspired by Creed Wild Vetiver",
    url_path: "/fragrance/b",
    image_url: "",
    category: "unisex",
    price_cents: 4500,
    current_status: "out_of_stock",
    observed_quantity: 0,
    quantity_observed_at: "2026-10-29T22:00:00Z",
    first_seen_at: "2026-10-29T20:00:00Z",
    last_checked_at: "2026-10-29T23:00:00Z",
    last_changed_at: "2026-10-29T21:00:00Z",
    last_restock_at: null,
    last_sold_out_at: "2026-10-29T21:00:00Z",
    current_in_stock_since: null,
    last_in_stock_duration_seconds: 3600,
    average_in_stock_duration_seconds: 3600,
    restock_count: 0,
  },
];


describe("catalog filtering", () => {
  it("filters by stock status and case-insensitive search", () => {
    expect(
      filterProducts(products, { query: "pineapple", status: "in_stock", category: "all" }),
    ).toEqual([products[0]]);
  });

  it("supports low-stock and category filters", () => {
    expect(
      filterProducts(products, { query: "", status: "low_stock", category: "men" }),
    ).toEqual([products[0]]);
  });

  it("sorts recently changed products first", () => {
    expect(sortProducts(products, "recent").map((product) => product.product_id)).toEqual([
      "a",
      "b",
    ]);
  });
});
