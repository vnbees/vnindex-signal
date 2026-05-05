"use server";

import { revalidatePath } from "next/cache";
import { fetchWithTimeout } from "@/lib/serverFetch";
import { getServerBackendUrl } from "@/lib/serverBackendUrl";

const FETCH_MS = 12_000;

export type ReviewActionResult = { ok: true } | { ok: false; message: string };

export async function publishReviewedSignalsAction(
  entryId: number,
  formData: FormData
): Promise<ReviewActionResult> {
  const symbols = formData
    .getAll("symbols")
    .map((v) => String(v || "").trim().toUpperCase())
    .filter(Boolean);
  if (symbols.length === 0) {
    return { ok: false, message: "Cần chọn ít nhất 1 mã để publish." };
  }

  try {
    const base = getServerBackendUrl();
    const res = await fetchWithTimeout(`${base}/api/v1/review/signal-entries/${entryId}/publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbols }),
      cache: "no-store",
      timeoutMs: FETCH_MS,
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = (await res.json()) as { detail?: unknown };
        if (typeof err.detail === "string") detail = err.detail;
      } catch {
        // ignore decode errors
      }
      return { ok: false, message: detail };
    }
  } catch (e) {
    return { ok: false, message: e instanceof Error ? e.message : "Không thể publish." };
  }

  revalidatePath("/review-signal-entries");
  revalidatePath("/thong-ke-tin-hieu-co-phieu-hom-nay");
  return { ok: true };
}
