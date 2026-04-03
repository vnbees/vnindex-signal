import { NextResponse } from "next/server";

export async function GET() {
  // Server-side route handler — đọc được env vars runtime
  const backendUrl =
    process.env.API_URL_INTERNAL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";

  try {
    const res = await fetch(`${backendUrl}/api/v1/runs?limit=1`, {
      cache: "no-store",
    });
    if (!res.ok) return NextResponse.json({ run_date: null });
    const data = await res.json();
    const items = data.items ?? data;
    return NextResponse.json({ run_date: items[0]?.run_date ?? null });
  } catch {
    return NextResponse.json({ run_date: null });
  }
}
