import { existsSync } from "node:fs";

const DEFAULT_BACKEND = "http://127.0.0.1:8000";

/** Tránh treo kết nối tới [::1] trên một số máy Windows khi backend chỉ lắng nghe IPv4. */
function loopbackToIPv4(url: string): string {
  try {
    const u = new URL(url);
    if (u.hostname === "localhost") u.hostname = "127.0.0.1";
    return u.toString();
  } catch {
    return url;
  }
}

function stripTrailingSlash(s: string): string {
  return s.replace(/\/+$/, "") || s;
}

/** Cổng dev của Next — nếu dùng làm "API URL" sẽ ra HTTP 404 (không có /api/v1/... trên Next). */
function looksLikeNextDevUrl(url: string): boolean {
  try {
    const u = new URL(url);
    const port = u.port || (u.protocol === "https:" ? "443" : "80");
    return port === "3000" || port === "3001";
  } catch {
    return false;
  }
}

/**
 * URL gọi FastAPI từ Server Components / server actions.
 * - Bỏ qua API_URL_INTERNAL trỏ tới hostname Docker `backend` khi chạy ngoài container.
 * - Không dùng URL cổng 3000/3001 (thường là nhầm với Next).
 */
export function getServerBackendUrl(): string {
  let pub = stripTrailingSlash(
    process.env.NEXT_PUBLIC_API_URL?.trim() || DEFAULT_BACKEND
  );
  if (looksLikeNextDevUrl(pub)) {
    pub = DEFAULT_BACKEND;
  }

  const internalRaw = process.env.API_URL_INTERNAL?.trim();
  let chosen: string;
  if (!internalRaw) {
    chosen = pub;
  } else {
    const inDocker = existsSync("/.dockerenv");
    if (/:\/\/backend(?::|\/|$)/i.test(internalRaw) && !inDocker) {
      chosen = pub;
    } else {
      chosen = stripTrailingSlash(internalRaw);
    }
  }

  if (looksLikeNextDevUrl(chosen)) {
    chosen = pub;
  }
  if (looksLikeNextDevUrl(chosen)) {
    chosen = DEFAULT_BACKEND;
  }

  return stripTrailingSlash(loopbackToIPv4(chosen));
}
