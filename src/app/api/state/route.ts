import { NextResponse } from "next/server";

import { fetchBackend } from "@/lib/backend";


export async function GET() {
  try {
    const response = await fetchBackend("/api/state");
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, s-maxage=5, stale-while-revalidate=15",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "dashboard_data_unavailable" },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
}
