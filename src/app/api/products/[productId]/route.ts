import { NextRequest, NextResponse } from "next/server";

import { fetchBackend } from "@/lib/backend";


export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ productId: string }> },
) {
  const { productId } = await context.params;
  try {
    const response = await fetchBackend(`/api/products/${encodeURIComponent(productId)}`);
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, s-maxage=10, stale-while-revalidate=30",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "product_data_unavailable" },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}
