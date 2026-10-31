export type StockStatus = "in_stock" | "out_of_stock";
export type EventType =
  | "restock"
  | "sold_out"
  | "new_product"
  | "removed"
  | "price_change";

export interface Product {
  product_id: string;
  variant_id: string | null;
  sku: string | null;
  collection_name: string;
  name: string;
  url_path: string;
  image_url: string;
  category: string;
  price_cents: number | null;
  current_status: StockStatus;
  observed_quantity: number | null;
  quantity_observed_at: string | null;
  first_seen_at: string;
  last_checked_at: string;
  last_changed_at: string;
  last_restock_at: string | null;
  last_sold_out_at: string | null;
  current_in_stock_since: string | null;
  last_in_stock_duration_seconds: number | null;
  average_in_stock_duration_seconds: number | null;
  restock_count: number;
}

export interface StockEvent {
  event_id: number;
  product_id: string;
  event_type: EventType;
  previous_status: StockStatus | null;
  new_status: StockStatus | null;
  previous_quantity: number | null;
  new_quantity: number | null;
  previous_price_cents: number | null;
  new_price_cents: number | null;
  duration_seconds: number | null;
  observed_at: string;
  name: string;
  url_path: string;
  image_url: string;
  price_cents: number | null;
  category: string;
}

export interface AvailabilityPeriod {
  period_id: number;
  product_id: string;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  ending_reason: string | null;
  starting_quantity: number | null;
}

export interface DashboardSummary {
  total_products: number;
  in_stock: number;
  sold_out: number;
  low_stock: number;
  restocks_24h: number;
  sellouts_24h: number;
  restocks_7d: number;
  average_in_stock_seconds: number | null;
  last_successful_check: string | null;
  tracking_started_at: string | null;
}

export interface DashboardState {
  revision: string;
  summary: DashboardSummary;
  products: Product[];
  events: StockEvent[];
  activity_events: StockEvent[];
}

export interface ProductPayload {
  product: Product;
  events: StockEvent[];
  periods: AvailabilityPeriod[];
}
