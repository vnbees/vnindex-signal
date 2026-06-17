"use server";

import { revalidatePath } from "next/cache";
import { fetchWithTimeout } from "@/lib/serverFetch";
import { getServerBackendUrl } from "@/lib/serverBackendUrl";

const FETCH_MS = 120_000;

export async function publishReviewV2SignalsAction(formData: FormData): Promise<void> {
  const symbols = formData
    .getAll("symbols")
    .map((v) => String(v || "").trim().toUpperCase())
    .filter(Boolean);
  if (symbols.length === 0) {
    throw new Error("Cần chọn ít nhất 1 mã để publish.");
  }

  const base = getServerBackendUrl();
  const res = await fetchWithTimeout(`${base}/api/v1/review-v2/publish`, {
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
    throw new Error(detail);
  }

  revalidatePath("/review-signal-entries-v2");
  revalidatePath("/thong-ke-tin-hieu-co-phieu-hom-nay");
}
