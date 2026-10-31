import type { Metadata } from "next";

import { CatalogDashboard } from "@/components/catalog-dashboard";

export const metadata: Metadata = { title: "Catalog" };

export default function CatalogPage() {
  return <CatalogDashboard />;
}
