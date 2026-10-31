import type { Metadata } from "next";

import { ProductDashboard } from "@/components/product-dashboard";

export const metadata: Metadata = { title: "Product history" };

export default async function ProductPage({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params;
  return <ProductDashboard productId={productId} />;
}
