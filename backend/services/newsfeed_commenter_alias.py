"""Ẩn danh kiểu Facebook: tên cố định theo commenter_id (UUID trình duyệt)."""

from __future__ import annotations

import hashlib
from uuid import UUID

_ADJECTIVES = (
    "Vui", "Nhanh", "Hiền", "Tốt", "Xanh", "Đỏ", "Vàng", "Mới", "Hay", "Khỏe",
    "Nóng", "Mát", "Sáng", "Tươi", "Nhỏ", "To", "Nhanh", "Chậm", "Cao", "Thấp",
    "Ngon", "Đẹp", "Xinh", "Khoẻ", "Nhẹ", "Nặng", "Ấm", "Mát", "Tròn", "Vuông",
    "Lạ", "Quen", "Yên", "Vội", "Chậm", "Nhanh", "Khô", "Ướt", "Mềm", "Cứng",
    "Tím", "Cam", "Hồng", "Đen", "Trắng", "Xám", "Bạc", "Vàng", "Nâu", "Xanh",
)

_NOUNS = (
    "Cáo", "Gấu", "Hươu", "Sói", "Mèo", "Chim", "Cò", "Vịt", "Ngỗng", "Hạc",
    "Cá", "Tôm", "Cua", "Ốc", "Sư Tử", "Hổ", "Báo", "Ngựa", "Trâu", "Bò",
    "Dê", "Cừu", "Lợn", "Chó", "Mèo", "Thỏ", "Chuột", "Khỉ", "Vượn", "Voọc",
    "Đại Bàng", "Diều Hâu", "Cú", "Quạ", "Sếu", "Hạc", "Vịt", "Ngỗng", "Thiên nga", "Hồng hạc",
    "Rùa", "Rắn", "Ếch", "Nhái", "Cá sấu", "Cá heo", "Cá voi", "Mực", "Bạch tuộc", "Tôm hùm",
)


def display_name_for_commenter(commenter_id: UUID) -> str:
    h = hashlib.sha256(str(commenter_id).encode("utf-8")).hexdigest()
    ai = int(h[:8], 16) % len(_ADJECTIVES)
    ni = int(h[8:16], 16) % len(_NOUNS)
    return f"{_ADJECTIVES[ai]} {_NOUNS[ni]}"
