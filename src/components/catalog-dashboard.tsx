"use client";

import Link from "next/link";
import { ArrowSquareOut, Funnel, GridFour, Heart, List, MagnifyingGlass } from "@phosphor-icons/react";
import { useMemo, useState } from "react";

import { ProductCard } from "@/components/product-card";
import { StatusBadge } from "@/components/status-badge";
import { DashboardSkeleton, ErrorNotice } from "@/components/system-states";
import { useDashboardState } from "@/hooks/use-dashboard-state";
import { useWatchlist } from "@/hooks/use-watchlist";
import { filterProducts, sortProducts, type ProductSort, type ProductStatusFilter } from "@/lib/filters";
import { formatDateTime, formatDuration, formatMoney, formatRelativeTime, productSourceUrl } from "@/lib/format";
import type { Product } from "@/lib/types";

type CatalogView = "table" | "grid";

function currentStockDuration(product: Product): number | null {
  if (product.current_status !== "in_stock" || !product.current_in_stock_since) return null;
  return Math.max(0, Math.floor((new Date(product.last_checked_at).getTime() - new Date(product.current_in_stock_since).getTime()) / 1000));
}

function StockDurationCell({ product }: { product: Product }) {
  const currentDuration = currentStockDuration(product);
  const primaryDuration = currentDuration ?? product.last_in_stock_duration_seconds;

  return (
    <div className="duration-cell">
      <strong>{primaryDuration === null ? "Not enough data" : formatDuration(primaryDuration)}</strong>
      <span>
        {currentDuration !== null
          ? product.last_restock_at
            ? "Current in-stock period"
            : "At least — tracking baseline"
          : "Last completed period"}
      </span>
      {product.average_in_stock_duration_seconds !== null ? (
        <small>Avg. {formatDuration(product.average_in_stock_duration_seconds)}</small>
      ) : null}
    </div>
  );
}

export function CatalogDashboard() {
  const { data, error, loading, refresh } = useDashboardState();
  const { watched, toggle } = useWatchlist();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<ProductStatusFilter>("all");
  const [category, setCategory] = useState("all");
  const [sort, setSort] = useState<ProductSort>("recent");
  const [watchlistOnly, setWatchlistOnly] = useState(false);
  const [view, setView] = useState<CatalogView>("table");

  const visibleProducts = useMemo(() => {
    if (!data) return [];
    const filtered = filterProducts(data.products, { query, status, category }).filter(
      (product) => !watchlistOnly || watched.has(product.product_id),
    );
    return sortProducts(filtered, sort);
  }, [data, query, status, category, sort, watchlistOnly, watched]);

  if (loading && !data) return <DashboardSkeleton />;
  if (!data) return <main className="page-shell"><ErrorNotice message={error ?? "No catalog data loaded."} onRetry={refresh} /></main>;

  return (
    <main className="page-shell">
      <section className="page-heading">
        <div><p className="section-label">Complete catalog</p><h1>Track every product.</h1><p>Scan availability, observed restocks, and stock duration without storefront clutter.</p></div>
        <div className="result-count"><strong>{visibleProducts.length}</strong><span>products shown</span></div>
      </section>
      {error ? <ErrorNotice message={error} onRetry={refresh} /> : null}

      <section className="filter-bar" aria-label="Catalog filters">
        <label className="search-field"><MagnifyingGlass size={19} /><span className="sr-only">Search products</span><input id="catalog-search" name="catalog-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search name or SKU" /></label>
        <label><span className="sr-only">Stock status</span><select id="catalog-status" name="catalog-status" value={status} onChange={(event) => setStatus(event.target.value as ProductStatusFilter)}><option value="all">All availability</option><option value="in_stock">In stock</option><option value="out_of_stock">Sold out</option><option value="low_stock">Low stock</option></select></label>
        <label><span className="sr-only">Category</span><select id="catalog-category" name="catalog-category" value={category} onChange={(event) => setCategory(event.target.value)}><option value="all">All categories</option><option value="men">Men</option><option value="women">Women</option><option value="unisex">Unisex</option><option value="other">Other</option></select></label>
        <label><span className="sr-only">Sort products</span><select id="catalog-sort" name="catalog-sort" value={sort} onChange={(event) => setSort(event.target.value as ProductSort)}><option value="recent">Recently changed</option><option value="name">Name</option><option value="quantity">Observed quantity</option><option value="price">Price</option></select></label>
        <button className={watchlistOnly ? "filter-button active" : "filter-button"} onClick={() => setWatchlistOnly((value) => !value)}><Heart size={18} weight={watchlistOnly ? "fill" : "regular"} />Watchlist</button>
      </section>

      <div className="catalog-toolbar">
        <p><strong>{visibleProducts.length}</strong> products · Quantities and times are observed, not guaranteed inventory.</p>
        <div className="view-toggle" aria-label="Catalog view">
          <button className={view === "table" ? "active" : ""} onClick={() => setView("table")} aria-pressed={view === "table"}><List size={18} />Table</button>
          <button className={view === "grid" ? "active" : ""} onClick={() => setView("grid")} aria-pressed={view === "grid"}><GridFour size={18} />Cards</button>
        </div>
      </div>

      {visibleProducts.length ? view === "table" ? (
        <div className="catalog-table-wrap">
          <table className="catalog-table">
            <thead>
              <tr>
                <th className="watch-column"><span className="sr-only">Watch</span></th>
                <th>Product</th>
                <th>Status</th>
                <th className="numeric-column">Observed qty.</th>
                <th className="price-column">Price</th>
                <th>Restocked at</th>
                <th>Stock duration</th>
                <th className="history-column">Last sold out</th>
                <th className="numeric-column history-column">Restocks</th>
                <th className="checked-column">Last checked</th>
                <th className="source-column"><span className="sr-only">Source</span></th>
              </tr>
            </thead>
            <tbody>
              {visibleProducts.map((product) => (
                <tr key={product.product_id}>
                  <td className="watch-column mobile-row-action"><button className={watched.has(product.product_id) ? "table-watch watched" : "table-watch"} onClick={() => toggle(product.product_id)} aria-label={watched.has(product.product_id) ? `Remove ${product.name} from watchlist` : `Add ${product.name} to watchlist`}><Heart size={18} weight={watched.has(product.product_id) ? "fill" : "regular"} /></button></td>
                  <td className="table-product" data-label="Product"><Link href={`/products/${encodeURIComponent(product.product_id)}`}>{product.name}</Link><span>{product.collection_name} · {product.category}</span></td>
                  <td className="status-column" data-label="Status"><StatusBadge status={product.current_status} /></td>
                  <td className="numeric-column quantity-column" data-label="Observed quantity"><strong>{product.observed_quantity ?? "—"}</strong></td>
                  <td className="price-column table-price" data-label="Price">{formatMoney(product.price_cents)}</td>
                  <td className="time-cell restock-column" data-label="Restocked at" title={formatDateTime(product.last_restock_at)}>{product.last_restock_at ? <><strong>{formatRelativeTime(product.last_restock_at)}</strong><span>{formatDateTime(product.last_restock_at)}</span></> : <span>No observed restock</span>}</td>
                  <td className="duration-column" data-label="Stock duration"><StockDurationCell product={product} /></td>
                  <td className="time-cell history-column" data-label="Last sold out" title={formatDateTime(product.last_sold_out_at)}>{product.last_sold_out_at ? <><strong>{formatRelativeTime(product.last_sold_out_at)}</strong><span>{formatDateTime(product.last_sold_out_at)}</span></> : <span>Not observed</span>}</td>
                  <td className="numeric-column history-column" data-label="Observed restocks"><strong>{product.restock_count}</strong></td>
                  <td className="time-cell checked-column" data-label="Last checked" title={formatDateTime(product.last_checked_at)}><strong>{formatRelativeTime(product.last_checked_at)}</strong></td>
                  <td className="source-column mobile-row-action"><a className="table-source" href={productSourceUrl(product.url_path)} target="_blank" rel="noreferrer" aria-label={`Open ${product.name} on Montagne Parfums`}><ArrowSquareOut size={18} /></a></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <section className="product-grid">
          {visibleProducts.map((product) => <ProductCard key={product.product_id} product={product} watched={watched.has(product.product_id)} onToggleWatch={toggle} />)}
        </section>
      ) : (
        <div className="empty-state catalog-empty"><Funnel size={30} /><h2>No products match</h2><p>Clear a filter or search for another fragrance.</p></div>
      )}
    </main>
  );
}
