import type { Metadata } from "next";
import type { FeedbackItem } from "@/lib/api";
import { fetchWithTimeout } from "@/lib/serverFetch";
import { getServerBackendUrl } from "@/lib/serverBackendUrl";

export const metadata: Metadata = {
  title: "Admin — Góp ý | ViiStock",
  robots: { index: false, follow: false },
};

export const dynamic = "force-dynamic";

/**
 * Backend thường trả UTC; nếu chuỗi không có Z/offset, ECMAScript coi là *local*
 * → máy VN sẽ lệch 7h. Luôn gắn Z cho naive ISO để parse đúng UTC.
 */
function parseFeedbackInstant(iso: string): Date {
  const s = iso.trim();
  if (/Z$/i.test(s)) return new Date(s);
  if (/[+-]\d{2}:\d{2}$/.test(s)) return new Date(s);
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$/.test(s)) {
    return new Date(`${s}Z`);
  }
  return new Date(s);
}

function formatVietnamTime(iso: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  }).format(parseFeedbackInstant(iso));
}

const FETCH_MS = 12_000;

async function loadFeedback(): Promise<
  { status: "ok"; items: FeedbackItem[] } | { status: "error"; message: string }
> {
  const base = getServerBackendUrl();
  try {
    const res = await fetchWithTimeout(`${base}/api/v1/admin/feedback?limit=200`, {
      cache: "no-store",
      timeoutMs: FETCH_MS,
    });
    if (!res.ok) {
      const hint =
        res.status === 404
          ? " Restart process FastAPI sau khi cập nhật code."
          : "";
      return {
        status: "error",
        message: `Không tải được dữ liệu (HTTP ${res.status}).${hint}`,
      };
    }
    const items = (await res.json()) as FeedbackItem[];
    return { status: "ok", items };
  } catch (e) {
    const aborted =
      (e instanceof Error && (e.name === "AbortError" || e.name === "TimeoutError")) ||
      (typeof DOMException !== "undefined" &&
        e instanceof DOMException &&
        e.name === "AbortError");
    if (aborted) {
      return {
        status: "error",
        message: `Hết thời gian chờ backend (${FETCH_MS / 1000}s). Chạy API cổng 8000 hoặc sửa API_URL_INTERNAL khi dev trên máy.`,
      };
    }
    return {
      status: "error",
      message: "Lỗi kết nối backend. Kiểm tra NEXT_PUBLIC_API_URL và backend đang chạy.",
    };
  }
}

function PageUrlCell({ url }: { url: string }) {
  const isAbsolute = /^https?:\/\//i.test(url);
  if (isAbsolute) {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="break-all text-tv-accent hover:underline"
      >
        {url}
      </a>
    );
  }
  return (
    <a href={url} className="break-all text-tv-accent hover:underline">
      {url}
    </a>
  );
}

export default async function AdminFeedbackPage() {
  const data = await loadFeedback();

  if (data.status === "error") {
    const message = data.message;
    return (
      <div className="tv-panel p-6">
        <h1 className="text-xl font-semibold text-tv-text">Góp ý từ người dùng</h1>
        <p className="mt-3 text-sm text-tv-down" role="alert">
          {message}
        </p>
      </div>
    );
  }

  const { items } = data;

  return (
    <div>
      <h1 className="text-xl font-semibold text-tv-text">Góp ý từ người dùng</h1>
      <p className="mt-1 text-sm text-tv-muted">Tối đa 200 mục mới nhất.</p>

      {items.length === 0 ? (
        <p className="mt-6 text-sm text-tv-muted">Chưa có góp ý nào.</p>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border border-tv-border">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead className="tv-table-head">
              <tr>
                <th className="border-b border-tv-border px-3 py-2 font-medium">Thời gian</th>
                <th className="border-b border-tv-border px-3 py-2 font-medium">Trang</th>
                <th className="border-b border-tv-border px-3 py-2 font-medium">Nội dung</th>
                <th className="border-b border-tv-border px-3 py-2 font-medium">Tên</th>
                <th className="border-b border-tv-border px-3 py-2 font-medium">Liên hệ</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-b border-tv-border/80 last:border-0">
                  <td className="align-top px-3 py-2 text-tv-muted whitespace-nowrap">
                    {formatVietnamTime(row.created_at)}
                  </td>
                  <td className="align-top px-3 py-2">
                    <PageUrlCell url={row.page_url} />
                  </td>
                  <td className="align-top px-3 py-2 text-tv-text whitespace-pre-wrap">
                    {row.message}
                  </td>
                  <td className="align-top px-3 py-2 text-tv-muted">{row.name ?? "—"}</td>
                  <td className="align-top px-3 py-2 text-tv-muted whitespace-pre-wrap">
                    {row.contact ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
