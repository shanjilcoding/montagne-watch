import type { StockStatus } from "@/lib/types";


export function StatusBadge({ status }: { status: StockStatus }) {
  return (
    <span className={`status-badge ${status}`}>
      <span className="status-dot" aria-hidden="true" />
      {status === "in_stock" ? "In stock" : "Sold out"}
    </span>
  );
}
