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
    ("phan mem", "Công nghệ"),
    ("dien toan", "Công nghệ"),
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


def _iter_strings(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, str):
        txt = value.strip()
        if txt:
            out.append(txt)
        return out
    if isinstance(value, dict):
        for v in value.values():
            out.extend(_iter_strings(v))
        return out
    if isinstance(value, list):
        for item in value:
            out.extend(_iter_strings(item))
    return out


def _looks_like_sector_text(value: str) -> bool:
    """Loại các giá trị dạng code số (vd. 1353) khỏi candidate ngành."""
    s = value.strip()
    if not s:
        return False
    norm = _strip_accents_lower(s)
    # Phải có ít nhất một chữ cái để coi là tên ngành.
    return any(("a" <= ch <= "z") for ch in norm)


def _collect_sector_candidates(profile: dict[str, Any]) -> tuple[list[str], str | None]:
    candidates: list[str] = []

    icb = profile.get("icbCode") or profile.get("icb_code") or profile.get("ICBCode")
    icb_code = str(icb).strip() if icb is not None else None

    direct_keys = (
        "industryName",
        "industry",
        "sectorName",
        "sector",
        "icbName",
        "icbIndustryName",
        "companyIndustry",
        "groupName",
        "subIndustry",
        "sectorDisplay",
    )
    for key in direct_keys:
        if key in profile:
            candidates.extend(_iter_strings(profile.get(key)))

    # Nhiều profile Fireant để ICB dạng object/list lồng nhau.
    for key, value in profile.items():
        k = _strip_accents_lower(str(key))
        if any(tag in k for tag in ("industry", "sector", "icb", "group")):
            candidates.extend(_iter_strings(value))

    # Dedup giữ thứ tự.
    seen: set[str] = set()
    dedup: list[str] = []
    for c in candidates:
        if not _looks_like_sector_text(c):
            continue
        if c not in seen:
            seen.add(c)
            dedup.append(c)
    return dedup, icb_code


def extract_sector_display(profile: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """
    Trả (sector_display, icb_code).
    Ưu tiên các key thường gặp trên object profile Fireant.
    """
    if not profile or not isinstance(profile, dict):
        return None, None

    candidates, icb_code = _collect_sector_candidates(profile)
    if not candidates:
        # Không có text ngành: vẫn trả nhãn ICB để không dồn toàn bộ vào "Khác".
        if icb_code:
            return f"ICB_{icb_code}", icb_code
        return None, icb_code

    # Ưu tiên candidate match keyword sớm nhất.
    for raw in candidates:
        norm = _strip_accents_lower(raw)
        for needle, label in _KEYWORD_SECTOR:
            if needle in norm:
                return label, icb_code
    # Không match keyword: trả candidate đầu tiên (để không dồn về "Khác")
    return candidates[0], icb_code


def sector_flow_bucket(sector_display: str | None) -> str:
    """Nhóm thô cho aggregate khi thiếu map chi tiết."""
    if not sector_display:
        return "Khác"
    s = _strip_accents_lower(sector_display)
    for needle, label in _KEYWORD_SECTOR:
        if needle in s:
            return label
    return sector_display.strip() or "Khác"
