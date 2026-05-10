const STORAGE_KEY = "viistock_newsfeed_commenter_id";

/** UUID cố định trên trình duyệt — dùng làm danh tính ẩn danh cho mọi bài newsfeed. */
export function getNewsfeedCommenterId(): string {
  if (typeof window === "undefined") return "";
  try {
    let id = localStorage.getItem(STORAGE_KEY);
    if (!id || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id)) {
      id = crypto.randomUUID();
      localStorage.setItem(STORAGE_KEY, id);
    }
    return id;
  } catch {
    return "";
  }
}
