import type { Product } from "./types";


export type ProductStatusFilter = "all" | "in_stock" | "out_of_stock" | "low_stock";
export type ProductSort = "recent" | "name" | "quantity" | "price";

export interface ProductFilters {
  query: string;
  status: ProductStatusFilter;
  category: string;
}

export function filterProducts(products: Product[], filters: ProductFilters): Product[] {
  const query = filters.query.trim().toLocaleLowerCase();
  return products.filter((product) => {
    const matchesQuery =
      !query ||
      product.name.toLocaleLowerCase().includes(query) ||
      (product.sku ?? "").toLocaleLowerCase().includes(query);
    const matchesCategory = filters.category === "all" || product.category === filters.category;
    const matchesStatus =
      filters.status === "all" ||
      (filters.status === "low_stock"
        ? product.current_status === "in_stock" &&
          product.observed_quantity !== null &&
          product.observed_quantity >= 1 &&
          product.observed_quantity <= 5
        : product.current_status === filters.status);
    return matchesQuery && matchesCategory && matchesStatus;
  });
}

export function sortProducts(products: Product[], sort: ProductSort): Product[] {
  return [...products].sort((left, right) => {
    if (sort === "name") return left.name.localeCompare(right.name);
    if (sort === "quantity") {
      return (right.observed_quantity ?? -1) - (left.observed_quantity ?? -1);
    }
    if (sort === "price") return (left.price_cents ?? Number.MAX_SAFE_INTEGER) - (right.price_cents ?? Number.MAX_SAFE_INTEGER);
    return new Date(right.last_changed_at).getTime() - new Date(left.last_changed_at).getTime();
  });
}
