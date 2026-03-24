"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    fetch("/api/latest-run")
      .then((r) => r.json())
      .then((data) => {
        if (data.run_date) {
          router.replace(`/signals/${data.run_date}`);
        }
      })
      .catch(() => {});
  }, [router]);

  return (
    <div className="text-center py-20">
      <h1 className="text-2xl font-bold text-slate-700 mb-4">VNINDEX Signal</h1>
      <p className="text-slate-500">Đang tải dữ liệu...</p>
    </div>
  );
}
