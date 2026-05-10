import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

function backendBase(): string {
  const raw =
    process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return raw.replace(/\/$/, "");
}

async function proxy(req: NextRequest, segments: string[]): Promise<NextResponse> {
  const sub = segments.length ? segments.join("/") : "";
  const targetUrl = new URL(req.url);
  const dest = `${backendBase()}/api/v1/${sub}${targetUrl.search}`;

  const headers = new Headers();
  const ct = req.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  const auth = req.headers.get("authorization");
  if (auth) headers.set("authorization", auth);

  const init: RequestInit = {
    method: req.method,
    headers,
    redirect: "manual",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  const res = await fetch(dest, init);
  const outHeaders = new Headers(res.headers);
  return new NextResponse(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers: outHeaders,
  });
}

type RouteCtx = { params: { path?: string[] } };

export async function GET(req: NextRequest, { params }: RouteCtx) {
  return proxy(req, params.path ?? []);
}

export async function POST(req: NextRequest, { params }: RouteCtx) {
  return proxy(req, params.path ?? []);
}

export async function DELETE(req: NextRequest, { params }: RouteCtx) {
  return proxy(req, params.path ?? []);
}

export async function PATCH(req: NextRequest, { params }: RouteCtx) {
  return proxy(req, params.path ?? []);
}

export async function PUT(req: NextRequest, { params }: RouteCtx) {
  return proxy(req, params.path ?? []);
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204 });
}
