import { NextRequest, NextResponse } from "next/server";

function getBackendUrl(): string {
  return (
    process.env.API_URL_INTERNAL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000"
  );
}

export async function POST(req: NextRequest) {
  try {
    const payload = await req.json();
    const res = await fetch(`${getBackendUrl()}/api/v1/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    });

    let data: unknown = null;
    try {
      data = await res.json();
    } catch {
      data = null;
    }

    if (!res.ok) {
      return NextResponse.json(
        data ?? { detail: `API error ${res.status}` },
        { status: res.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Không kết nối được máy chủ. Vui lòng thử lại sau." },
      { status: 502 }
    );
  }
}
