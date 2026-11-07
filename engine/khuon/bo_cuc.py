"""Bố cục theo ô (slot) trên khung 1920×1080 + bảng màu theo vai trò. Template đọc từ đây, storyboard không gõ toạ độ.

Số mặc định lấy từ các cảnh đã dựng tay trong videos/jev.py và bo_nao_thu_hai_v2.py (vị trí lặp lại nhiều nhất).
"""
from whiteboard import INK, INK2, ORANGE, GREEN, RED, BLUE, YELLOW

W, H = 1920, 1080

MAU = {"orange": ORANGE, "cam": ORANGE, "blue": BLUE, "xanh": BLUE, "green": GREEN, "xanh-la": GREEN, "red": RED, "do": RED,
       "ink": INK, "den": INK, "muted": INK2, "xam": INK2, "yellow": YELLOW, "vang": YELLOW}


def mau(c, mac_dinh=INK):
    if not c:
        return mac_dinh
    return MAU.get(c, c)        # cho phép mã màu #RRGGBB


# ô: (tâm x, tâm y, rộng tối đa)
O = {
    "tieu-de": (960, 80, 1700),
    "trai": (480, 520, 820),
    "phai": (1380, 500, 860),
    "giua": (960, 520, 1500),
    "duoi-rong": (960, 735, 1500),
    "day": (960, 900, 1600),          # dòng chú thích / kết luận dưới cùng
    "duoi": (960, 760, 1600),         # dòng chữ phía dưới, trên hộp kết luận
    "cot-phai": (1560, 330, 640),     # cột số liệu bên phải (y = dòng đầu)
    "cot-trai": (460, 200, 900),      # ghi chú bên trái (y = dòng đầu)
    "hang-tren": (960, 290, 1800),    # hàng thẻ phía trên
    "duoi-phai": (1360, 860, 860),    # vài dòng dưới ảnh bên phải
}

CO_CHU = {"tieu-de": 52, "lon": 56, "vua": 40, "nho": 34, "nguon": 26, "the-tieu-de": 60, "the-than": 34}


def chia_ngang(n, rong=1800, tam=960):
    """Tâm x của n ô chia đều trên một hàng rộng `rong` (n=3, rong=1800 → 360, 960, 1560)."""
    buoc = rong / n
    return [round(tam - rong / 2 + buoc * (i + 0.5)) for i in range(n)]


def chia_doc(n, tam=500, buoc=200):
    """Tâm y của n ô xếp dọc quanh `tam` (n=3 → 300, 500, 700)."""
    return [round(tam + buoc * (i - (n - 1) / 2)) for i in range(n)]
