"""Đọc số tiếng Việt (mọi cách đọc thường gặp) — dùng để kiểm "số trên hình phải có trong lời đọc".

doc("2026")   → {"hai nghìn không trăm hai mươi sáu", "hai ngàn không trăm hai mươi sáu", …}
doc("77,9")   → {"bảy mươi bảy phẩy chín", …};  doc("0,36") → {"không phẩy ba sáu", "không phẩy ba mươi sáu", …}
Biến thể: lăm/năm, tư/bốn, mốt/một, linh/lẻ, nghìn/ngàn, phần lẻ đọc từng chữ số hoặc cả số.
"""
import re
from itertools import product

DV = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _chuc(t, co_truoc):
    """0..99; co_truoc = phía trước đã có chữ (trăm/nghìn…) → 1..9 đọc 'linh/lẻ'."""
    if t == 0:
        return [""]
    if t < 10:
        return [f"linh {DV[t]}", f"lẻ {DV[t]}"] if co_truoc else [DV[t]]
    c, u = divmod(t, 10)
    goc = "mười" if c == 1 else f"{DV[c]} mươi"
    if u == 0:
        return [goc]
    if u == 5:
        return [f"{goc} lăm"] + ([f"{goc} năm"] if c > 1 else [])
    if u == 1 and c > 1:
        return [f"{goc} mốt", f"{goc} một"]
    if u == 4 and c > 1:
        return [f"{goc} tư", f"{goc} bốn"]
    return [f"{goc} {DV[u]}"]


def _ba(n, co_truoc):
    """0..999 trong một nhóm; co_truoc = có nhóm lớn hơn phía trước."""
    h, t = divmod(n, 100)
    if h:
        dau = [f"{DV[h]} trăm"]
    elif co_truoc and t:
        dau = ["không trăm"]
    else:
        dau = [""]
    return [" ".join(x for x in (a, b) if x) for a in dau for b in _chuc(t, bool(h) or co_truoc)]


def doc_nguyen(n):
    if n == 0:
        return ["không"]
    nhom = []
    for ten in ([""], ["nghìn", "ngàn"], ["triệu"], ["tỷ"]):
        n, r = divmod(n, 1000)
        nhom.append((r, ten))
        if not n:
            break
    nhom.reverse()
    phan, co_truoc = [], False
    for r, ten in nhom:
        if r == 0:
            continue
        cach = [" ".join(x for x in (a, t) if x) for a in _ba(r, co_truoc) for t in ten]
        phan.append(cach)
        co_truoc = True
    return [" ".join(p) for p in product(*phan)]


def doc(chuoi):
    """Chuỗi số trên hình (vd. '1.500.000', '77,9', '2.2', '0,042') → tập cách đọc."""
    s = chuoi.strip()
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        return set(doc_nguyen(int(s.replace(".", ""))))
    m = re.fullmatch(r"(\d+)[.,](\d+)", s)
    if m:
        a, b = m.groups()
        sau = {" ".join(DV[int(c)] for c in b)} | set(doc_nguyen(int(b)) if not b.startswith("0") else [])
        out = {f"{x} phẩy {y}" for x in doc_nguyen(int(a)) for y in sau}
        if b == "5" and int(a) > 0:                     # 7,5 → "bảy rưỡi"
            out |= {f"{x} ~ rưỡi" for x in doc_nguyen(int(a))}    # "~" = 0–2 chữ chen giữa ("bảy tỷ rưỡi")
        return out
    if s.isdigit():
        return set(doc_nguyen(int(s)))
    return set()


SO = re.compile(r"(?<!\w)\d+(?:[.,]\d+)*(?![^\W\d_])")   # bỏ số dính chữ cái: a16z, gpt-4o, H100
