"""Chuẩn hoá nhãn ngành từ Fireant profile/ICB → nhóm gần với prompt Balanced (TOP 9 + bonus)."""

from __future__ import annotations

import unicodedata
from typing import Any

# Chuỗi con (không dấu / lower) → tên hiển thị thống nhất (tiếng Việt như example-result)
_KEYWORD_SECTOR: list[tuple[str, str]] = [
    ("vien thong", "Viễn thông"),
    ("telecom", "Viễn thông"),
    ("tai nguyen co ban", "Tài nguyên cơ bản"),
    ("basic material", "Tài nguyên cơ bản"),
    ("thuc pham", "Thực phẩm và đồ uống"),
    ("food", "Thực phẩm và đồ uống"),
    ("beverage", "Thực phẩm và đồ uống"),
    ("y te", "Y tế"),
    ("health", "Y tế"),
    ("dau khi", "Dầu khí"),
    ("oil", "Dầu khí"),
    ("gas", "Dầu khí"),
    ("hoa chat", "Hóa chất"),
    ("chemical", "Hóa chất"),
    ("xay dung", "Xây dựng và vật liệu"),
    ("construction", "Xây dựng và vật liệu"),
    ("building", "Xây dựng và vật liệu"),
    ("ngan hang", "Ngân hàng"),
    ("bank", "Ngân hàng"),
    ("bat dong san", "Bất động sản"),
    ("real estate", "Bất động sản"),
    ("property", "Bất động sản"),
    ("cong nghe", "Công nghệ"),
    ("technology", "Công nghệ"),
    ("software", "Công nghệ"),
    ("ban le", "Bán lẻ"),
    ("retail", "Bán lẻ"),
    ("tai chinh", "Tài chính"),
    ("finance", "Tài chính"),
    ("bao hiem", "Bảo hiểm"),
    ("insurance", "Bảo hiểm"),
    ("hang khong", "Hàng không"),
    ("airline", "Hàng không"),
    ("thep", "Thép và kim loại"),
    ("steel", "Thép và kim loại"),
    ("dien", "Điện"),
    ("power", "Điện"),
    ("utilities", "Tiện ích"),
]


def _strip_accents_lower(s: str) -> str:
    """Bỏ dấu tiếng Việt (và tương tự) để so khớp keyword — tránh maketrans lệch độ dài."""
    s = s.lower().strip()
    nfkd = unicodedata.normalize("NFD", s)
    out = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return out.replace("\u0111", "d")  # đ / Đ (sau lower) → d


def extract_sector_display(profile: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """
    Trả (sector_display, icb_code).
    Ưu tiên các key thường gặp trên object profile Fireant.
    """
    if not profile or not isinstance(profile, dict):
        return None, None

    icb = profile.get("icbCode") or profile.get("icb_code") or profile.get("ICBCode")
    icb_code = str(icb).strip() if icb is not None else None

    candidates: list[str] = []
    for key in (
        "industryName",
        "industry",
        "sectorName",
        "sector",
        "icbName",
        "icbIndustryName",
        "companyIndustry",
    ):
        v = profile.get(key)
        if isinstance(v, str) and v.strip():
            candidates.append(v.strip())
        elif isinstance(v, dict):
            for sub in ("name", "title", "label", "industryName"):
                s = v.get(sub)
                if isinstance(s, str) and s.strip():
                    candidates.append(s.strip())
                    break

    raw = candidates[0] if candidates else None
    if not raw:
        return None, icb_code

    norm = _strip_accents_lower(raw)
    for needle, label in _KEYWORD_SECTOR:
        if needle in norm:
            return label, icb_code
    return raw, icb_code


def sector_flow_bucket(sector_display: str | None) -> str:
    """Nhóm thô cho aggregate khi thiếu map chi tiết."""
    if not sector_display:
        return "Khác"
    s = _strip_accents_lower(sector_display)
    for needle, label in _KEYWORD_SECTOR:
        if needle in s:
            return label
    return sector_display.strip() or "Khác"
