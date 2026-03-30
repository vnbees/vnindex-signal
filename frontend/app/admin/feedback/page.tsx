import type { Metadata } from "next";
import type { FeedbackItem } from "@/lib/api";

export const metadata: Metadata = {
  title: "Admin — Góp ý | ViiStock",
  robots: { index: false, follow: false },
};

/** Luôn fetch tại runtime (ADMIN_API_KEY / API URL từ môi trường deploy). */
export const dynamic = "force-dynamic";

function getBackendUrl(): string {
  return (
    process.env.API_URL_INTERNAL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000"
  );
}

async function loadFeedback(): Promise<
  | { status: "ok"; items: FeedbackItem[] }
  | { status: "no_key" }
  | { status: "error"; message: string }
> {
  const key = process.env.ADMIN_API_KEY;
  if (!key) {
    return { status: "no_key" };
  }
  const base = getBackendUrl();
  try {
    const res = await fetch(`${base}/api/v1/admin/feedback?limit=200`, {
      headers: { Authorization: `Bearer ${key}` },
      cache: "no-store",
    });
    if (!res.ok) {
      return {
        status: "error",
        message: `Không tải được dữ liệu (HTTP ${res.status}). Kiểm tra ADMIN_API_KEY và quyền API.`,
      };
    }
    const items = (await res.json()) as FeedbackItem[];
    return { status: "ok", items };
  } catch {
    return {
      status: "error",
      message: "Lỗi kết nối backend. Kiểm tra API_URL_INTERNAL / NEXT_PUBLIC_API_URL.",
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

  if (data.status === "no_key") {
    return (
      <div className="tv-panel p-6">
        <h1 className="text-xl font-semibold text-tv-text">Góp ý từ người dùng</h1>
        <p className="mt-3 text-sm text-tv-muted">
          Để xem danh sách, cấu hình biến môi trường{" "}
          <code className="rounded bg-tv-panel-hover px-1 py-0.5 text-tv-text">ADMIN_API_KEY</code>{" "}
          trên server frontend (Railway: service frontend → Variables). Giá trị là chuỗi key thô{" "}
          <code className="rounded bg-tv-panel-hover px-1 py-0.5 text-xs">sk-vnindex-…</code> trùng
          với một API key đang có trong backend (tạo bằng{" "}
          <code className="rounded bg-tv-panel-hover px-1 py-0.5 text-xs">
            backend/scripts/create_api_key.py
          </code>{" "}
          nếu chưa có), rồi redeploy frontend.
        </p>
      </div>
    );
  }

  if (data.status === "error") {
    return (
      <div className="tv-panel p-6">
        <h1 className="text-xl font-semibold text-tv-text">Góp ý từ người dùng</h1>
        <p className="mt-3 text-sm text-tv-down" role="alert">
          {data.message}
        </p>
      </div>
    );
  }

  const { items } = data;

  return (
    <div>
      <h1 className="text-xl font-semibold text-tv-text">Góp ý từ người dùng</h1>
      <p className="mt-1 text-sm text-tv-muted">
        Tối đa 200 mục mới nhất. Trang chỉ dùng nội bộ (cần{" "}
        <code className="rounded bg-tv-panel px-1 py-0.5 text-xs">ADMIN_API_KEY</code>).
      </p>

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
                    {new Date(row.created_at).toLocaleString("vi-VN", {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
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
