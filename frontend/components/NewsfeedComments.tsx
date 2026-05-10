"use client";

import { useCallback, useEffect, useState } from "react";
import {
  deleteNewsfeedComment,
  getNewsfeedCommenterIdentity,
  getNewsfeedComments,
  postNewsfeedComment,
  type NewsfeedComment,
} from "@/lib/api";
import { getNewsfeedCommenterId } from "@/lib/newsfeedCommenterId";

function formatCommentTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return iso;
  }
}

type Props = {
  entryId: number;
  isAdmin: boolean;
};

export function NewsfeedComments({ entryId, isAdmin }: Props) {
  const [comments, setComments] = useState<NewsfeedComment[]>([]);
  const [myName, setMyName] = useState<string>("");
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const res = await getNewsfeedComments(entryId);
    setComments(res.items);
  }, [entryId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        await refresh();
        const cid = getNewsfeedCommenterId();
        if (cid) {
          const idRes = await getNewsfeedCommenterIdentity(cid);
          if (!cancelled) setMyName(idRes.display_name);
        }
      } catch {
        if (!cancelled) setError("Không tải được bình luận.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [entryId, refresh]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cid = getNewsfeedCommenterId();
    const text = body.trim();
    if (!cid || !text) return;
    setSaving(true);
    setError(null);
    try {
      const created = await postNewsfeedComment(entryId, { commenter_id: cid, body: text });
      setComments((prev) => [...prev, created]);
      setMyName(created.display_name);
      setBody("");
    } catch {
      setError("Gửi bình luận thất bại.");
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(commentId: number) {
    if (!isAdmin) return;
    if (!confirm("Xóa bình luận này?")) return;
    setError(null);
    try {
      await deleteNewsfeedComment(commentId);
      await refresh();
    } catch {
      setError("Xóa thất bại.");
    }
  }

  return (
    <div className="mt-4 border-t border-tv-border pt-4">
      <p className="text-sm font-medium text-tv-text">Bình luận</p>
      {myName ? (
        <p className="mt-1 text-xs text-tv-muted">
          Tên hiển thị của bạn: <span className="font-medium text-tv-text">{myName}</span>
        </p>
      ) : null}
      {error ? <p className="mt-2 text-xs text-tv-down">{error}</p> : null}

      {loading ? (
        <p className="mt-2 text-xs text-tv-muted">Đang tải bình luận…</p>
      ) : comments.length === 0 ? (
        <p className="mt-2 text-xs text-tv-muted">Chưa có bình luận.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {comments.map((c) => (
            <li key={c.id} className="rounded-md border border-tv-border bg-tv-bg/40 px-3 py-2 text-sm">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <span className="font-medium text-tv-text">{c.display_name}</span>
                  <span className="ml-2 text-xs text-tv-muted">{formatCommentTime(c.created_at)}</span>
                </div>
                {isAdmin ? (
                  <button
                    type="button"
                    onClick={() => onDelete(c.id)}
                    className="text-xs text-tv-down hover:underline"
                  >
                    Xóa
                  </button>
                ) : null}
              </div>
              <p className="mt-1 whitespace-pre-wrap text-tv-text">{c.body}</p>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={onSubmit} className="mt-3 space-y-2">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          maxLength={2000}
          rows={3}
          placeholder="Viết bình luận…"
          className="w-full rounded-md border border-tv-border bg-tv-bg px-3 py-2 text-sm text-tv-text placeholder:text-tv-muted focus:outline-none focus:ring-1 focus:ring-tv-accent"
        />
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-tv-muted">{body.trim().length}/2000</span>
          <button
            type="submit"
            disabled={saving || !body.trim() || typeof window === "undefined" || !getNewsfeedCommenterId()}
            className="rounded-md bg-tv-accent px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          >
            {saving ? "Đang gửi…" : "Gửi"}
          </button>
        </div>
      </form>
    </div>
  );
}
