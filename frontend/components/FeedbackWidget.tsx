"use client";

import { useCallback, useEffect, useId, useState } from "react";
import { submitFeedback } from "@/lib/api";

const MAX_MESSAGE = 5000;

export function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const titleId = useId();
  const descId = useId();

  const close = useCallback(() => {
    setOpen(false);
    setError(null);
    setSuccess(false);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, close]);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    const trimmed = message.trim();
    if (!trimmed) {
      setError("Vui lòng nhập nội dung góp ý.");
      return;
    }
    setSending(true);
    try {
      const page_url =
        typeof window !== "undefined" ? window.location.href : "/";
      await submitFeedback({
        message: trimmed,
        name: name.trim() || undefined,
        contact: contact.trim() || undefined,
        page_url,
      });
      setSuccess(true);
      setMessage("");
      setName("");
      setContact("");
      setTimeout(() => {
        close();
      }, 1600);
    } catch (err) {
      if (err instanceof Error && err.message === "Failed to fetch") {
        setError("Không kết nối được máy chủ. Vui lòng thử lại sau.");
      } else {
        setError(err instanceof Error ? err.message : "Gửi thất bại, thử lại sau.");
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setOpen(true);
          setError(null);
          setSuccess(false);
        }}
        className="fixed bottom-5 right-5 z-[100] flex h-12 w-12 items-center justify-center rounded-full border border-tv-border bg-tv-accent text-white shadow-lg transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-tv-accent focus:ring-offset-2 focus:ring-offset-tv-bg"
        aria-label="Gửi góp ý"
        title="Gửi góp ý"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-[110] flex items-end justify-center p-4 sm:items-center"
          role="presentation"
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/50"
            aria-label="Đóng"
            onClick={close}
          />
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            aria-describedby={descId}
            className="tv-panel relative z-10 w-full max-w-lg p-5 shadow-xl"
          >
            <h2 id={titleId} className="text-lg font-semibold text-tv-text">
              Góp ý cho ViiStock
            </h2>
            <p id={descId} className="mt-1 text-sm text-tv-muted">
              Ý kiến của bạn giúp chúng tôi cải thiện sản phẩm. Trang hiện tại sẽ được gửi kèm.
            </p>
            <form onSubmit={handleSubmit} className="mt-4 space-y-3">
              <div>
                <label htmlFor="fb-message" className="tv-section-title mb-1 block">
                  Nội dung <span className="text-tv-down">*</span>
                </label>
                <textarea
                  id="fb-message"
                  rows={4}
                  maxLength={MAX_MESSAGE}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  className="w-full rounded-md border border-tv-border bg-tv-bg px-3 py-2 text-sm text-tv-text placeholder:text-tv-muted focus:outline-none focus:ring-2 focus:ring-tv-accent/40"
                  placeholder="Mô tả góp ý hoặc lỗi bạn gặp..."
                  required
                />
                <p className="mt-0.5 text-right text-xs text-tv-muted">
                  {message.length}/{MAX_MESSAGE}
                </p>
              </div>
              <div>
                <label htmlFor="fb-name" className="tv-section-title mb-1 block">
                  Tên (tuỳ chọn)
                </label>
                <input
                  id="fb-name"
                  type="text"
                  maxLength={200}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-md border border-tv-border bg-tv-bg px-3 py-2 text-sm text-tv-text placeholder:text-tv-muted focus:outline-none focus:ring-2 focus:ring-tv-accent/40"
                  placeholder="Tên hoặc biệt danh"
                />
              </div>
              <div>
                <label htmlFor="fb-contact" className="tv-section-title mb-1 block">
                  Email / SĐT liên hệ (tuỳ chọn)
                </label>
                <input
                  id="fb-contact"
                  type="text"
                  maxLength={200}
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  className="w-full rounded-md border border-tv-border bg-tv-bg px-3 py-2 text-sm text-tv-text placeholder:text-tv-muted focus:outline-none focus:ring-2 focus:ring-tv-accent/40"
                  placeholder="Để chúng tôi phản hồi khi cần"
                />
              </div>
              {error && (
                <p className="text-sm text-tv-down" role="alert">
                  {error}
                </p>
              )}
              {success && (
                <p className="text-sm text-tv-up" role="status">
                  Đã gửi góp ý. Cảm ơn bạn!
                </p>
              )}
              <div className="flex flex-wrap justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={close}
                  className="rounded-md border border-tv-border bg-tv-panel px-4 py-2 text-sm font-medium text-tv-text hover:bg-tv-panel-hover"
                >
                  Huỷ
                </button>
                <button
                  type="submit"
                  disabled={sending}
                  className="rounded-md border border-transparent bg-tv-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
                >
                  {sending ? "Đang gửi…" : "Gửi góp ý"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
