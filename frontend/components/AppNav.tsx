"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/thong-ke-tin-hieu-co-phieu-hom-nay", label: "Thống kê" },
  { href: "/signals", label: "Tín hiệu" },
  { href: "/search-theo-ma", label: "Tìm kiếm theo mã" },
  { href: "/goi-y-vao-lenh", label: "Gợi ý vốn" },
];

function navClass(active: boolean) {
  return active
    ? "text-tv-text border-b-2 border-tv-accent pb-0.5 -mb-px"
    : "text-tv-muted hover:text-tv-text border-b-2 border-transparent pb-0.5 -mb-px";
}

export function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="flex items-center gap-8">
      <Link
        href="/thong-ke-tin-hieu-co-phieu-hom-nay"
        className="inline-flex items-center gap-2 font-semibold text-tv-text tracking-tight"
        aria-label="ViiStock"
      >
        <Image
          src="/logo/bmBDo.jpg"
          alt="ViiStock logo"
          width={1168}
          height={784}
          className="h-10 w-auto rounded-md object-contain"
          priority
        />
        <span>ViiStock</span>
      </Link>
      <div className="flex items-center gap-6 text-sm">
        {LINKS.map(({ href, label }) => {
          const active =
            href === "/signals"
              ? pathname === "/signals" || pathname?.startsWith("/signals/")
              : href === "/goi-y-vao-lenh"
                ? pathname === "/goi-y-vao-lenh" || pathname?.startsWith("/goi-y-vao-lenh/")
              : href === "/search-theo-ma"
                ? pathname === "/search-theo-ma" || pathname?.startsWith("/search-theo-ma/")
              : pathname === href || pathname?.startsWith(href);
          return (
            <Link key={href} href={href} className={navClass(!!active)}>
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
