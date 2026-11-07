"""Các khối (template) dựng cảnh. Mỗi khối: hàm ve_<tên>(ctx, s, spec) → thêm phần tử vào cảnh `s` qua whiteboard.Board.

Storyboard chỉ ghi NỘI DUNG + cụm chữ mốc (`at`); toạ độ, cỡ chữ, màu theo vai trò, độ trễ lấy từ bo_cuc.py.
Thời gian của một mục:
  at: "cụm chữ"   → lúc đọc tới cụm chữ (+ lead, âm = sớm hơn)
  sau: 1.0        → sau mục trước 1,0 s
  (không ghi)     → sau mục trước `buoc` giây (mặc định theo khối)
Cách viết gọn một dòng (đỡ token, AI hay dùng):
  "chữ hiện @ cụm chữ đọc"          → {text, at}
  "chữ @ cụm chữ -0.5"              → lead -0.5 (số có dấu ở cuối)
  "chữ @ +1.0"                      → sau mục trước 1,0 s
  "Tiêu đề | thân thẻ @ … #cam"     → thẻ: title + body; #màu (#cam #xanh #xanh-la #do #xam…), #lon #nho #muted #tay
  "nhãn cột = 0.75 @ …"             → cột: label + value
  LUÔN đặt chuỗi gọn trong ngoặc kép: YAML coi ` #` là chú thích (mất màu) và `: ` là khoá (hỏng mục). Lint bắt cả hai.
Thêm khối mới: viết hàm ve_<tên> rồi đăng ký vào KHOI ở cuối file (và ghi vào khuon/README.md).
"""
import importlib, re
from .bo_cuc import O, CO_CHU, MAU as MAU_TEN, mau, chia_ngang, chia_doc, INK, INK2, ORANGE, BLUE, GREEN, RED


class Ctx:
    """Ngữ cảnh dựng: Board, bộ tìm mốc, bảng nguồn trích dẫn, cảnh hiện tại."""

    def __init__(self, B, moc, nguon):
        self.B, self.moc, self.nguon = B, moc, nguon
        self.canh, self.s = None, None

    def t(self, item, truoc=None, buoc=0.3, noi=""):
        """Thời điểm hiện của một mục (xem đầu file)."""
        if isinstance(item, dict) and item.get("at"):
            t, _ = self.moc.tim(item["at"], item.get("lan", 1), noi=f"{self.canh} · {noi}")
            return (t if t is not None else 0.0) + float(item.get("lead", 0))
        if isinstance(item, dict) and "sau" in item and truoc is not None:
            return truoc + float(item["sau"])
        if truoc is not None:
            return truoc + buoc
        return self.bat_dau + float(item.get("lead", 0) if isinstance(item, dict) else 0)

    @property
    def bat_dau(self):
        return self.s.d["start"]


def _ds(spec):
    """Khối nhận danh sách mục: cho phép viết thẳng list hoặc {items: [...], ...}."""
    if isinstance(spec, list):
        return spec, {}
    return spec.get("items", []), spec


KHOA = {"text", "title", "body", "label", "value", "at", "lead", "sau", "lan", "color", "lon", "nho", "muted", "tay", "size",
        "src", "extra", "id", "o", "x", "y", "w", "h", "khung", "tag", "img", "tier", "to", "suffix", "prefix", "items", "xong", "sai",
        "gach", "da_kiem", "chu", "ten", "muc", "hang", "ngay", "so", "fill", "khung", "dur", "mark"}


def _mark_kw(it):
    """`#khoanh` / `#gach-chan` (T4): khoanh tròn hoặc gạch chân bằng nét tay rough.js, truyền tiếp vào ctx.B.txt."""
    return {"mark": it["mark"]} if it.get("mark") else {}


def _chu(x):
    """Mục dạng dict giữ nguyên; dạng chuỗi gọn → dict (xem đầu file)."""
    if isinstance(x, dict):
        if len(x) == 1 and not set(x) & KHOA:
            raise ValueError(f"mục {x!r}: YAML hiểu nhầm thành 'khoá: giá trị' vì chuỗi có ': ' — đặt chuỗi gọn trong ngoặc kép")
        return x
    s, d = str(x), {}
    for tg in re.findall(r"\s#([\w-]+)", s):
        if tg in MAU_TEN:
            d["color"] = tg
        else:
            d[tg.replace("-", "_")] = True
    if d.pop("khoanh", None):          # #khoanh / #gach-chan: khoanh tròn hoặc gạch chân bằng nét tay (T4)
        d["mark"] = "khoanh"
    elif d.pop("gach_chan", None):
        d["mark"] = "gach_chan"
    s = re.sub(r"\s#[\w-]+", "", s).rstrip()          # giữ khoảng trắng đầu dòng (dòng code thụt lề)
    if s.startswith("@ "):                                # "@ cụm chữ" = chỉ có mốc, không có chữ
        s = " " + s
    if " @ " in s:
        s, at = s.split(" @ ", 1)
        s, at = s.rstrip(), at.strip()
        m = re.fullmatch(r"([+-])(\d+(?:\.\d+)?)", at)
        if m:                       # "@ +1.0" = sau mục trước; "@ -0.5" = sớm hơn mốc của khối 0,5 s
            d["sau" if m.group(1) == "+" else "lead"] = float(m.group(2)) * (1 if m.group(1) == "+" else -1)
        else:
            m = re.fullmatch(r"(.*?)\s+([+-]\d+(?:\.\d+)?)", at)
            d["at"], d["lead"] = (m.group(1), float(m.group(2))) if m else (at, 0.0)
    if " = " in s:
        s, v = s.rsplit(" = ", 1)
        d["value"] = float(v.replace(",", "."))
    if " | " in s:
        d["title"], d["body"] = (p.strip() for p in s.split(" | ", 1))
    d["text"] = d.setdefault("label", s)
    d.setdefault("title", s)
    return d


# ── khung ────────────────────────────────────────────────────────────────────
def ve_tieu_de(ctx, s, spec):
    spec = _chu(spec)
    x, y, mw = O["tieu-de"]
    if getattr(ctx, "hud", False):          # có HUD: tiêu đề xuống dưới dải định vị
        y = 160
    ctx.B.txt(s, "td", spec["text"], x, y, ctx.t(spec, noi="tieu_de"), size=spec.get("size", CO_CHU["tieu-de"]),
              color=mau(spec.get("color"), ORANGE), maxWidth=mw)


def ve_nguon(ctx, s, spec):
    """Dòng nguồn. Gọn: "BONN, §4.7 @ cụm chữ" — tên tắt đầu dòng (khai ở `nguon:` đầu storyboard) tự thay bằng nguồn đầy đủ."""
    spec = _chu(spec)
    goc = spec.get("src") or spec.get("text", "")
    dau, _, sau = goc.partition(", ")
    goc = ctx.nguon.get(dau, dau) + (", " + sau if sau else "") if not spec.get("src") else ctx.nguon.get(goc, goc)
    text = goc + (", " + spec["extra"] if spec.get("extra") else "")
    t = ctx.t(spec, noi="nguon") if spec.get("at") else ctx.bat_dau + 1.0
    ctx.B.cite(s, "nguon", text, t)


def ve_chu(ctx, s, spec):
    """Một dòng chữ (chú thích / kết luận) ở ô `o` (mặc định: dưới cùng)."""
    spec = _chu(spec)
    x, y, mw = O[spec.get("o", "day")]
    ctx.B.txt(s, spec.get("id", "chu"), spec["text"], x, y, ctx.t(spec, noi="chu"), size=spec.get("size", CO_CHU["vua"]),
              color=mau(spec.get("color"), INK), maxWidth=mw, hand=spec.get("tay", True), **_mark_kw(spec))


# ── liệt kê ──────────────────────────────────────────────────────────────────
def ve_the3(ctx, s, spec):
    """Hàng thẻ (thường 3): tiêu đề + thân, mỗi thẻ hiện lúc đọc tới cụm chữ của nó."""
    items, opt = _ds(spec)
    n = len(items)
    xs = chia_ngang(n, 1800)
    w = opt.get("w", 500 if n <= 3 else round(1800 / n) - 80)
    y, h = opt.get("y", O["hang-tren"][1]), opt.get("h", 250)
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 0.4, noi=f"the3[{i}]")
        ctx.B.card(s, f"the{i}", it["title"], xs[i], y, w, h, t, accent=mau(it.get("color"), BLUE), body=it.get("body"),
                   titleSize=opt.get("titleSize", CO_CHU["the-tieu-de"]), bodySize=opt.get("bodySize", CO_CHU["the-than"]))


def _cot_chu(ctx, s, prefix, items, x, y0, mw, co_mac_dinh, tay_mac_dinh):
    """Một cột các dòng chữ xếp dọc (dùng cho so_lieu / ghi_chu). Cảnh có thẻ tin → cột bắt đầu thấp hơn, không đè thẻ."""
    if getattr(ctx, "co_the_tin", False) and y0 < 380:
        y0 = 420
    t, y, co_truoc, lon_truoc = None, y0, None, False
    for i, it in enumerate(items):
        it = _chu(it)
        co = it.get("size", CO_CHU["lon"] if it.get("lon") else (CO_CHU["nho"] if it.get("nho") else co_mac_dinh))
        if co_truoc is not None:     # dòng nhấn (#lon) có thêm khoảng thở trước và sau
            y += round(co_truoc * 0.85 + co * 0.85 + 26 + (30 if (lon_truoc or it.get("lon")) else 0))
        lon_truoc = bool(it.get("lon"))
        t = ctx.t(it, t, 0.6, noi=f"{prefix}[{i}]")
        mac = INK2 if it.get("muted") else (ORANGE if it.get("lon") else INK)
        ctx.B.txt(s, f"{prefix}{i}", it["text"], x, y, t, size=co, color=mau(it.get("color"), mac), maxWidth=mw,
                  hand=it.get("tay", tay_mac_dinh and not it.get("muted")), **_mark_kw(it))
        co_truoc = co


def ve_so_lieu(ctx, s, spec):
    """Cột số liệu bên phải (2–5 dòng): `lon: true` = số nhấn to, `muted: true` = dòng phụ."""
    items, opt = _ds(spec)
    x, y, mw = O[opt.get("o", "cot-phai")]
    _cot_chu(ctx, s, "sl", items, opt.get("x", x), opt.get("y", y), mw, CO_CHU["vua"], True)


def ve_ghi_chu(ctx, s, spec):
    """Các dòng ghi chú bên trái phía trên (thường không vẽ tay)."""
    items, opt = _ds(spec)
    x, y, mw = O[opt.get("o", "cot-trai")]
    _cot_chu(ctx, s, "gc", items, opt.get("x", x), opt.get("y", y), mw, CO_CHU["vua"], False)


def ve_cap(ctx, s, spec):
    """Hai (vài) cụm chữ đặt ngang nhau ở đáy cảnh, ví dụ giá vào / giá ra."""
    items, opt = _ds(spec)
    xs = chia_ngang(len(items), 1480, 990)
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 0.5, noi=f"cap[{i}]")
        ctx.B.txt(s, f"cap{i}", it["text"], xs[i], opt.get("y", 960), t, size=it.get("size", 52), color=mau(it.get("color"), INK))


# ── số liệu ──────────────────────────────────────────────────────────────────
COT_TAM = {"trai": 410, "phai": 1380, "giua": 960}


def ve_cot(ctx, s, spec):
    """Cột so sánh (giá trị 0..1, hiện %): mỗi cột một mốc riêng."""
    items, opt = _ds(spec)
    w, gap, maxH, base = opt.get("w", 150), opt.get("gap", 90), opt.get("maxH", 360), opt.get("base", 720)
    tong = len(items) * w + (len(items) - 1) * gap
    x0 = opt.get("x0", COT_TAM[opt.get("o", "trai")] - tong / 2 + w / 2)
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 0.25, noi=f"cot[{i}]")
        col = mau(it.get("color"), INK2)
        x = x0 + i * (w + gap)
        s.add({"id": f"cot{i}", "type": "bar", "x": x, "y": base, "w": w, "maxH": maxH, "value": it["value"], "color": col,
               "label": "", "showValue": opt.get("hien_so", True), "valueColor": col, "enterAt": t, "growDuration": 0.9, "enter": "grow"})
        # hien_so: false → không hiện "%" (cột chỉ để so chiều cao; ghi số thật trong nhãn, vd. điểm 58, doanh thu 16,8 tỷ)
        ctx.B.txt(s, f"cotl{i}", it["label"], x, base + 45, t, size=32, color=INK, hand=False)


def ve_con_so(ctx, s, spec):
    """Một hàng con số đếm lên (1–4 số), nhãn nhỏ bên dưới."""
    items, opt = _ds(spec)
    xs = chia_ngang(len(items), opt.get("rong", 1500))
    y = opt.get("y", 480)
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 0.4, noi=f"con_so[{i}]")
        ctx.B.counter(s, f"so{i}", xs[i], y, t, it["to"], suffix=it.get("suffix", ""), prefix=it.get("prefix", ""),
                      size=it.get("size", 88), color=mau(it.get("color"), ORANGE), decimals=it.get("thap_phan", 0))
        if it.get("label"):
            ctx.B.txt(s, f"sol{i}", it["label"], xs[i], y + 95, t + 0.3, size=34, color=INK2, hand=False, maxWidth=420)


# ── quan hệ ──────────────────────────────────────────────────────────────────
def ve_toa_ra(ctx, s, spec):
    """1 nút toả ra N nút (mũi tên + hộp). `at` của khối = lúc các nhánh bắt đầu hiện; `tu.lead` để nút gốc hiện sớm hơn."""
    tu, den = _chu(spec["tu"]), spec["den"]
    t0 = ctx.t(spec, noi="toa_ra")
    ctx.B.box(s, "goc", tu["text"], 360, 500, 360, 120, t0 + float(tu.get("lead", 0)), size=38)
    ys = chia_doc(len(den), 500, spec.get("buoc_y", 200))
    for i, it in enumerate(den):
        it = _chu(it)
        t = ctx.t(it, noi=f"toa_ra[{i}]") if it.get("at") else t0 + spec.get("buoc", 0.2) * i
        col = mau(it.get("color"), INK)
        ctx.B.line(s, f"tr{i}", [(540, 500), (780, ys[i])], t, color=col, width=4, dur=0.3)
        ctx.B.box(s, f"nh{i}", it["text"], 960, ys[i], 340, 100, t + 0.2, stroke=col, label_color=col, size=34, hand=i == 0)


def ve_luong(ctx, s, spec):
    """Chuỗi A → B → C (hộp chữ hoặc ảnh), mũi tên hiện ngay trước nút đích."""
    items, opt = _ds(spec)
    n = len(items)
    xs = chia_ngang(n, opt.get("rong", 1700))
    y = opt.get("y", 480)
    bw = min(360, round(opt.get("rong", 1700) / n) - 120)
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 0.6, noi=f"luong[{i}]")
        col = mau(it.get("color"), INK)
        if i:
            ctx.B.line(s, f"lm{i}", [(xs[i - 1] + bw / 2 + 15, y), (xs[i] - bw / 2 - 15, y)], t - 0.2, color=INK, width=4, dur=0.3)
        if it.get("img"):
            ctx.B.img(s, f"ln{i}", it["img"], xs[i], y, bw, t, tier=it.get("tier", "low"))
        else:
            ctx.B.box(s, f"ln{i}", it["text"], xs[i], y, bw, 120, t, stroke=col, label_color=col, size=it.get("size", 34))


def _diem_bien(cx, cy, hw, hh, dx, dy):
    """Điểm giao giữa tia từ tâm hộp (cx, cy) theo hướng (dx, dy) đã chuẩn hoá và viền hộp (hw, hh = nửa rộng/cao)."""
    if not dx and not dy:
        return cx, cy
    tx = hw / abs(dx) if dx else float("inf")
    ty = hh / abs(dy) if dy else float("inf")
    t = min(tx, ty)
    return cx + dx * t, cy + dy * t


# ── T4: sơ đồ ────────────────────────────────────────────────────────────────
def ve_so_do_kien_truc(ctx, s, spec):
    """Sơ đồ hộp + mũi tên (client → API → DB, cache đứng cạnh…). Vị trí theo hàng (`hang`, từ 0) và thứ tự trong
    hàng (`cot`); không gõ toạ độ. Mũi tên tự chạm đúng viền hộp, không cắm vào giữa.
    `nut`: [{id, text, hang: 0, cot: 0, at, color, size, w, h}] · `noi`: [{tu, den, at, nhan, color, dashed}]."""
    nuts = spec["nut"]
    hangs = {}
    for n in nuts:
        hangs.setdefault(n.get("hang", 0), []).append(n)
    hang_keys = sorted(hangs)
    ys = dict(zip(hang_keys, chia_doc(len(hang_keys), spec.get("tam_y", 500), spec.get("buoc_y", 230))))
    pos, t = {}, None
    for hang in hang_keys:
        items = sorted(hangs[hang], key=lambda n: n.get("cot", 0))
        xs = chia_ngang(len(items), spec.get("rong", 1680))
        slot = spec.get("rong", 1680) / len(items)
        for x, n in zip(xs, items):
            w, h = n.get("w", min(320, round(slot) - 100)), n.get("h", 110)
            t = ctx.t(n, t, spec.get("buoc", 0.4), noi=f"so_do_kien_truc·nut {n['id']}")
            col = mau(n.get("color"), INK)
            ctx.B.box(s, f"nd-{n['id']}", n["text"], x, ys[hang], w, h, t, stroke=col, label_color=col, size=n.get("size", 34))
            pos[n["id"]] = (x, ys[hang], w, h)
    for i, e in enumerate(spec.get("noi", [])):
        for k in ("tu", "den"):
            if e[k] not in pos:
                raise ValueError(f"so_do_kien_truc: nối tới nút lạ {e[k]!r} (chưa khai trong `nut`)")
        x0, y0, w0, h0 = pos[e["tu"]]
        x1, y1, w1, h1 = pos[e["den"]]
        dx, dy = x1 - x0, y1 - y0
        do_dai = (dx ** 2 + dy ** 2) ** 0.5 or 1
        ux, uy = dx / do_dai, dy / do_dai
        p0 = _diem_bien(x0, y0, w0 / 2, h0 / 2, ux, uy)
        p1 = _diem_bien(x1, y1, w1 / 2, h1 / 2, -ux, -uy)
        t = ctx.t(e, t, spec.get("buoc_noi", 0.35), noi=f"so_do_kien_truc·noi {e['tu']}->{e['den']}")
        col = mau(e.get("color"), INK)
        ctx.B.line(s, f"nl{i}", [p0, p1], t, color=col, width=e.get("width", 4), dashed=e.get("dashed", False), dur=0.35)
        if e.get("nhan"):
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 - 24
            ctx.B.txt(s, f"nlc{i}", e["nhan"], mx, my, t + 0.2, size=28, color=mau(e.get("mau_nhan"), INK2), hand=False)


# ── ảnh ──────────────────────────────────────────────────────────────────────
ANH = {"duoi-rong": (960, 735, 1500), "phai": (1360, 500, 800), "trai": (560, 500, 800), "giua": (960, 540, 1200)}


def _anh_thieu(ctx, s, spec, id_, x, y, w, t):
    """Trang duyệt: ảnh thật chưa có file → thêm phần tử ảnh (ban_duyet đổi thành khung giữ chỗ) thay vì báo lỗi."""
    import os
    if os.environ.get("KHUON_DUYET") == "1" and not os.path.exists(os.path.join(ctx.B.assets_dir, spec["src"])):
        s.add({"id": id_, "type": "image", "src": f"assets/{spec['src']}", "x": x, "y": y, "w": w, "enterAt": t,
               "enter": "fade", "enterDuration": 0.6, "hand": False})
        return True
    return False


def ve_anh(ctx, s, spec):
    """Ảnh thật (chụp màn hình, hình bài báo…) + nhãn; nhớ có `nguon` trong cảnh."""
    x, y, w = ANH[spec.get("o", "phai")]
    if _anh_thieu(ctx, s, spec, spec.get("id", "anh"), spec.get("x", x), spec.get("y", y), spec.get("w", w), ctx.t(spec, noi="anh")):
        return
    # `video: clip.mp4` (cùng thư mục assets): phát đoạn video thật trong khung, `src` là khung đại diện để lấy kích thước
    extra = {"video": f"assets/{spec['video']}", "videoRate": spec.get("toc_do", 1)} if spec.get("video") else {}
    ctx.B.photo(s, spec.get("id", "anh"), spec["src"], spec.get("x", x), spec.get("y", y), ctx.t(spec, noi="anh"),
                w=spec.get("w", w), tag=spec.get("tag"), frame=spec.get("khung", True), **extra)


# ── liệt kê (T2) ─────────────────────────────────────────────────────────────
DS_O = {"trai": (160, 200), "phai": (1050, 230), "giua": (420, 230)}


def ve_danh_sach(ctx, s, spec):
    """Danh sách dòng căn trái (mục lục, ý chính). `so: true` → đánh số "1. ", `cham: "•"` → gạch đầu dòng."""
    items, opt = _ds(spec)
    x, y0 = DS_O[opt.get("o", "trai")]
    co = opt.get("size", 48 if len(items) <= 5 else 40)
    buoc = opt.get("buoc", round(co * 2.5))
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 0.35, noi=f"danh_sach[{i}]")
        dau = f"{i + 1}. " if opt.get("so") else (opt["cham"] + " " if opt.get("cham") else "")
        ctx.B.txt(s, f"ds{i}", dau + it["text"], opt.get("x", x), opt.get("y", y0) + buoc * i, t, size=co, align="left",
                  color=mau(it.get("color"), INK), hand=it.get("tay", i == 0),
                  maxWidth=opt.get("maxWidth", 1600 if opt.get("o", "trai") != "phai" else 800), **_mark_kw(it))


def ve_cac_buoc(ctx, s, spec):
    """Các bước có số tròn màu cam bên trái (quy trình, 30-60-90 ngày)."""
    items, opt = _ds(spec)
    n = len(items)
    buoc = opt.get("buoc", min(130, round(700 / max(1, n))))
    x, y0 = opt.get("x", 200), opt.get("y", 230)
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 0.5, noi=f"cac_buoc[{i}]")
        ctx.B.badge(s, f"cb{i}", i + 1, x, y0 + buoc * i, t)
        ctx.B.txt(s, f"cbt{i}", it["text"], x + 60, y0 + buoc * i, t + 0.15, size=opt.get("size", 44), align="left",
                  color=mau(it.get("color"), INK), hand=it.get("tay", i == 0), maxWidth=opt.get("maxWidth", 1500), **_mark_kw(it))


def ve_checklist(ctx, s, spec):
    """Danh sách có ô: mặc định ☐; #xong → ✓ xanh lá, #sai → ✗ đỏ, #gach → gạch ngang chữ sau khi hiện."""
    items, opt = _ds(spec)
    x, y0 = DS_O[opt.get("o", "trai")]
    co = opt.get("size", 46)
    buoc = opt.get("buoc", round(co * 2.4))
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 0.5, noi=f"checklist[{i}]")
        y = opt.get("y", y0) + buoc * i
        dau, col = ("✓", GREEN) if it.get("xong") else (("✗", RED) if it.get("sai") else ("☐", INK))
        ctx.B.txt(s, f"ckm{i}", dau, x, y, t, size=co, color=col, hand=False, align="left")
        ctx.B.txt(s, f"ckt{i}", it["text"], x + round(co * 1.3), y, t + 0.1, size=co, align="left",
                  color=mau(it.get("color"), INK2 if it.get("gach") else INK), hand=it.get("tay", i == 0), maxWidth=opt.get("maxWidth", 1500))
        if it.get("gach"):
            w = min(len(it["text"]) * co * 0.55, 1500)
            ctx.B.strike(s, f"ckg{i}", x + round(co * 1.3) + w / 2, y, w, t + 0.8)


def ve_dong_thoi_gian(ctx, s, spec):
    """Trục thời gian ngang: chấm màu + mốc (trên) + nội dung (dưới). Mục: "15/09/2026 | Ra mắt Jev @ …"."""
    items, opt = _ds(spec)
    n, y = len(items), opt.get("y", 760)
    xs = chia_ngang(n, opt.get("rong", 1400))
    mau_xoay = [ORANGE, BLUE, GREEN, RED, INK]
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 0.8, noi=f"dong_thoi_gian[{i}]")
        if i == 0:
            ctx.B.line(s, "tg-truc", [(200, y), (1760, y)], t - 0.3, color=INK, width=5, arrow=True, dur=0.6)
        col = mau(it.get("color"), mau_xoay[i % len(mau_xoay)])
        ctx.B.circle(s, f"tgc{i}", "", xs[i], y, 18, t, fill=col, dur=0.2)
        ctx.B.txt(s, f"tgm{i}", it["title"], xs[i], y - 60, t, size=40, color=col)
        if it.get("body"):
            ctx.B.txt(s, f"tgn{i}", it["body"], xs[i], y + 90, t + 0.3, size=34, hand=False, maxWidth=min(760, round(1500 / n)))


# ── so sánh (T2) ─────────────────────────────────────────────────────────────
def ve_hai_cot(ctx, s, spec):
    """A vs B. Mỗi bên: {tieu_de, img?, color, items}. Có ảnh vẽ: ảnh trên, tiêu đề làm chú thích dưới ảnh;
    không ảnh: tiêu đề màu ở trên, các dòng bên dưới. `giua: "vs"` (tuỳ chọn)."""
    for k, (x, mac) in (("trai", (480, ORANGE)), ("phai", (1440, BLUE))):
        ben = spec.get(k)
        if not ben:
            continue
        col = mau(ben.get("color"), mac)
        td = _chu(ben["tieu_de"])
        t = ctx.t(td, noi=f"hai_cot.{k}")
        lui = 110 if getattr(ctx, "co_the_tin", False) else 0      # cảnh có thẻ tin ở trên → hạ cả khối xuống
        if ben.get("img"):
            ctx.B.img(s, f"hci{k}", ben["img"], x, 420 + lui, ben.get("w", 260) - (40 if lui else 0), t, tier=ben.get("tier", "low"))
            ctx.B.txt(s, f"hc{k}", td["text"], x, 640 + lui, t + 0.4, size=td.get("size", 44), color=mau(td.get("color"), INK), maxWidth=820)
            y, buoc = 760 + lui, 90 if lui else 100
        else:
            ctx.B.txt(s, f"hc{k}", td["text"], x, 180 + (220 if lui else 0), t, size=td.get("size", 52), color=col, maxWidth=820)
            y, buoc = 300 + (190 if lui else 0), 90
        tt = t
        for i, it in enumerate(ben.get("items", [])):
            it = _chu(it)
            tt = ctx.t(it, tt, 0.5, noi=f"hai_cot.{k}[{i}]")
            co = it.get("size", CO_CHU["lon"] if it.get("lon") else 40)
            ctx.B.txt(s, f"hc{k}{i}", it["text"], x, y + buoc * i, tt, size=co, color=mau(it.get("color"), col if it.get("lon") else INK),
                      hand=it.get("tay", i == 0), maxWidth=820)
    if spec.get("giua"):
        g = _chu(spec["giua"])
        ctx.B.txt(s, "hcvs", g["text"], 960, 420, ctx.t(g, noi="hai_cot.giua") if g.get("at") else ctx.bat_dau + 0.5,
                  size=44, color=INK2, hand=False)


def ve_bang(ctx, s, spec):
    """Bảng so sánh: {cot: ["", "LLM", "BERT", "Jev"], hang: ["Đầu ra | token | lớp | phân phối @ cụm chữ", …], nhan: 3}.
    Cột 0 là tên hàng; `nhan` = chỉ số cột được tô cam (cột nhân vật chính)."""
    cot, hang = spec["cot"], spec["hang"]
    nd = len(cot) - 1
    xs = [260] + chia_ngang(nd, 1300, 1180)
    nhan = spec.get("nhan")
    t0 = ctx.t(spec, noi="bang") if spec.get("at") else ctx.bat_dau + 0.5
    for j, h in enumerate(cot[1:], 1):
        ctx.B.txt(s, f"bh{j}", h, xs[j], 180, t0 + 0.4 * (j - 1), size=46, color=ORANGE if j == nhan else (BLUE if j == 1 else INK2))
    buoc = min(140, round(620 / max(1, len(hang))))
    t = t0 + 0.4 * nd
    for i, r in enumerate(hang):
        r = _chu(r)
        t = ctx.t(r, t, 1.0, noi=f"bang[{i}]")
        o = [c.strip() for c in r["text"].split(" | ")]
        y = 320 + buoc * i
        ctx.B.txt(s, f"br{i}", o[0], xs[0], y, t, size=40, color=INK2, hand=False)
        for j, cell in enumerate(o[1:], 1):
            ctx.B.txt(s, f"bc{i}{j}", cell, xs[j], y, t + 0.2 * (j - 1), size=36, color=ORANGE if j == nhan else INK,
                      hand=False, maxWidth=round(1300 / nd) - 20)


# ── chữ (T2) ─────────────────────────────────────────────────────────────────
HOP_O = {"day": (960, 920), "tren-trai": (520, 260), "tren-phai": (1400, 260), "giua": (960, 540)}


def ve_hop_ket_luan(ctx, s, spec):
    """Hộp chốt ý / cảnh báo. Mặc định ở đáy, viền đỏ (cảnh báo); #xanh-la cho ý tích cực; `fill` đổi nền;
    `o: tren-trai | tren-phai | giua` để dùng làm hộp nhấn ở chỗ khác."""
    spec = _chu(spec)
    hx, hy = HOP_O[spec.get("o", "day")]
    co = spec.get("size", 36)
    w = min(1600, round(len(spec["text"]) * co * 0.55) + 120)
    h = 100 if len(spec["text"]) * co * 0.55 < 1480 else 130
    col = mau(spec.get("color"), RED)
    ctx.B.box(s, spec.get("id", "hkl"), spec["text"], hx, spec.get("y", hy), spec.get("w", w), h, ctx.t(spec, noi="hop_ket_luan"),
              stroke=col, label_color=col, size=co, fill=spec.get("fill", "#FFFFFF"))


CODE_O = {"phai": (1420, 520, 820, 620), "trai": (520, 520, 820, 620), "giua": (960, 540, 1300, 700)}


def ve_code(ctx, s, spec):
    """Khung code / request / YAML: {tieu_de: "POST /v1/x", dong: ['"state": "…" @ …', '  "team": Choice @ +0.4 #xanh'], o: phai}."""
    x, y, w, h = CODE_O[spec.get("o", "phai")]
    td = _chu(spec.get("tieu_de", ""))
    t = ctx.t(td, noi="code.tieu_de") if td.get("at") else (ctx.t(spec, noi="code") if spec.get("at") else ctx.bat_dau + 0.5)
    ctx.B.panel(s, "cd", td.get("text", ""), x, y, w, h, t, accent=mau(spec.get("color"), BLUE), title_size=36)
    buoc = spec.get("buoc", 80)
    for i, d in enumerate(spec.get("dong", [])):
        d = _chu(d)
        t = ctx.t(d, t, 0.3, noi=f"code[{i}]")
        ctx.B.txt(s, f"cd{i}", d["text"], x - w / 2 + 50, y - h / 2 + 130 + buoc * i, t, size=spec.get("size", 34), align="left",
                  font="sans", weight=600, hand=False, color=mau(d.get("color"), INK))


# ── ảnh (T2) ─────────────────────────────────────────────────────────────────
def ve_anh_khoanh(ctx, s, spec):
    """Ảnh thật + khoanh vùng màu + chú thích dưới ảnh. Vùng tính theo TỈ LỆ ảnh (0..1, tâm x/y, rộng/cao):
    vung: [{x: 0.25, y: 0.88, w: 0.18, h: 0.11, at: "…", chu: "0,596 ≠ 0,76", color: do}]."""
    x, y, w = ANH[spec.get("o", "phai")]
    if _anh_thieu(ctx, s, spec, spec.get("id", "ak"), spec.get("x", x), spec.get("y", y), spec.get("w", w), ctx.t(spec, noi="anh_khoanh")):
        return
    L, T, Wp, Hp = ctx.B.photo(s, spec.get("id", "ak"), spec["src"], spec.get("x", x), spec.get("y", y), ctx.t(spec, noi="anh_khoanh"),
                               w=spec.get("w", w), tag=spec.get("tag"), frame=spec.get("khung", True))
    t = None
    for i, v in enumerate(spec.get("vung", [])):
        t = ctx.t(v, t, 0.6, noi=f"anh_khoanh[{i}]")
        col = mau(v.get("color"), RED)
        ctx.B.mark(s, f"akm{i}", L + Wp * v["x"], T + Hp * v["y"], Wp * v["w"], Hp * v["h"], t, color=col)
        if v.get("chu"):
            ctx.B.txt(s, f"akc{i}", v["chu"], L + Wp / 2, T + Hp + 60 + 60 * i, t + 0.3, size=38, color=col, maxWidth=round(Wp))


# ── số liệu (T2) ─────────────────────────────────────────────────────────────
TD_O = {"day": (960, 900, 1200), "giua": (960, 560, 1200), "trai": (520, 700, 800), "phai": (1400, 700, 800)}


def ve_tien_do(ctx, s, spec):
    """Thanh tiến độ nằm ngang (giá trị 0..1) + nhãn phía trên. (x, y) là TÂM thanh (studio: BarElement.horizontal).
    Gọn: "tiến độ 22% = 0.22 @ cụm chữ"."""
    spec = _chu(spec)
    x, y, w = TD_O[spec.get("o", "day")]
    t = ctx.t(spec, noi="tien_do")
    col = mau(spec.get("color"), GREEN)
    s.add({"id": "tdo", "type": "bar", "horizontal": True, "x": x, "y": y, "w": spec.get("w", w), "maxH": spec.get("h", 36),
           "value": spec["value"], "color": col, "label": "", "showValue": spec.get("hien_so", False), "valueColor": col,
           "enterAt": t, "growDuration": 1.0, "enter": "grow"})
    nhan = spec.get("label") or spec.get("text")
    if nhan:
        ctx.B.txt(s, "tdol", nhan, x, y - 70, t, size=40, color=col)


# ── dòng 1 "Tuần IT có gì hot" ───────────────────────────────────────────────
MUC_MAU = {"industry": ORANGE, "ra mắt": ORANGE, "mlops": BLUE, "agentops": BLUE, "kiến trúc": BLUE, "learning": GREEN,
           "phân tích": GREEN, "repo": INK, "paper": INK2, "bài báo": INK2}


def ve_the_tin(ctx, s, spec):
    """Thẻ tin trên cùng: nhãn mục (viên màu) + tên + hãng · ngày (+ "Tin 2/6" góc phải).
    {muc: "Industry", ten: "Gemini 4 Argon", hang: "Google DeepMind", ngay: "09/10/2026", so: "2/6", at: "…"}."""
    t = ctx.t(spec, noi="the_tin") if spec.get("at") else ctx.bat_dau + 0.2
    col = mau(spec.get("color"), MUC_MAU.get(str(spec.get("muc", "")).lower(), ORANGE))
    lui = 60 if getattr(ctx, "hud", False) else 0      # có HUD (0019): chừa dải trên cùng, không đè nhãn chương + trục năm
    if spec.get("muc"):
        ctx.B.txt(s, "ttm", str(spec["muc"]).upper(), 260, 90 + lui, t, size=28, color="#FFFFFF", box="pill", boxColor=col, hand=False)
    if spec.get("so"):
        ctx.B.txt(s, "tts", f"Tin {spec['so']}", 1700, 90 + lui, t, size=30, color=INK2, hand=False)
    than = " · ".join(str(x) for x in (spec.get("hang"), spec.get("ngay")) if x)
    ctx.B.card(s, "ttc", spec["ten"], 960, 230 + lui, 1600, 190, t + 0.1, accent=col, body=than or None, titleSize=62, bodySize=34)


# ── một ảnh AI cho cả cảnh (T3) ──────────────────────────────────────────────
AV_O = {"giua": (960, 500), "tren": (960, 380), "trai": (540, 500), "phai": (1380, 500)}


def ve_anh_vung(ctx, s, spec):
    """MỘT ảnh AI chứa vài vật, vẽ dần từng vùng đúng lúc lời nhắc tới (thay vì tạo 3–4 ảnh riêng).
    {img: ten-anh (sketch-<ten>.png), o: giua|tren|trai|phai, rong: 1500, cao: 560, huong: ngang|doc,
     vung: ["chú thích @ cụm chữ", "@ cụm chữ", {at: …, khung: [x0, y0, x1, y1], chu: …}]}
    Vùng tự chia theo khoảng trống giữa các vật (trái → phải), hoặc theo `khung` (tỉ lệ 0..1)."""
    from .anh_vung import tao_vung
    import os
    vung = [_chu(v) for v in spec["vung"]]
    src = os.path.join(ctx.B.assets_dir, f"sketch-{spec['img']}.png")
    if not os.path.exists(src) and os.environ.get("KHUON_DUYET") == "1":
        # trang duyệt (ban_duyet.py): ảnh chưa tạo → chia đều N ô giữ chỗ theo chiều ngang, vẫn đúng mốc thời gian
        n = len(vung)
        W, H = 1500 * n // 3 or 500, 520
        cat = [(spec["img"] + f"__v{i + 1}", (round(i * W / n) + 20, 20, round((i + 1) * W / n) - 20, H - 20)) for i in range(n)]
    else:
        W, H, cat = tao_vung(src, vung, spec.get("huong", "ngang"))
    cx, cy = AV_O[spec.get("o", "giua")]
    cx, cy = spec.get("x", cx), spec.get("y", cy)
    k = min(spec.get("rong", 1500) / W, spec.get("cao", 560) / H)
    left, top = cx - W * k / 2, cy - H * k / 2
    t = None
    for i, (v, (ten, (x0, y0, x1, y1))) in enumerate(zip(vung, cat)):
        t = ctx.t(v, t, 1.2, noi=f"anh_vung[{i}]")
        dien_tich = (x1 - x0) * (y1 - y0) / (W * H)
        ctx.B.img(s, f"av{i}", ten, round(left + (x0 + x1) / 2 * k), round(top + (y0 + y1) / 2 * k), round((x1 - x0) * k), t,
                  tier="low", dur=v.get("dur", round(min(2.0, max(1.0, 0.9 + dien_tich * 2.5)), 2)))
        chu = (v.get("chu") or v.get("text") or "").strip()
        if chu:
            ctx.B.txt(s, f"avc{i}", chu, round(left + (x0 + x1) / 2 * k), round(top + y1 * k + 50), t + 0.4, size=v.get("size", 38),
                      color=mau(v.get("color"), INK), hand=False, maxWidth=max(260, round((x1 - x0) * k)))


# ── lối thoát ────────────────────────────────────────────────────────────────
def ve_custom(ctx, s, spec):
    """Cảnh hiếm chưa có template: `custom: {ham: "videos.ten_file:ten_ham"}` → ham(ctx, s, spec)."""
    mod, _, fn = spec["ham"].partition(":")
    getattr(importlib.import_module(mod), fn)(ctx, s, spec)


KHOI = {"tieu_de": ve_tieu_de, "nguon": ve_nguon, "chu": ve_chu, "the3": ve_the3, "so_lieu": ve_so_lieu, "ghi_chu": ve_ghi_chu,
        "cap": ve_cap, "cot": ve_cot, "con_so": ve_con_so, "toa_ra": ve_toa_ra, "luong": ve_luong, "anh": ve_anh,
        "custom": ve_custom,
        # T2
        "danh_sach": ve_danh_sach, "cac_buoc": ve_cac_buoc, "checklist": ve_checklist, "dong_thoi_gian": ve_dong_thoi_gian,
        "hai_cot": ve_hai_cot, "bang": ve_bang, "hop_ket_luan": ve_hop_ket_luan, "code": ve_code, "anh_khoanh": ve_anh_khoanh,
        "tien_do": ve_tien_do, "the_tin": ve_the_tin,
        # T3
        "anh_vung": ve_anh_vung,
        # T4
        "so_do_kien_truc": ve_so_do_kien_truc}

# khuôn "giải thích sự kiện" (0019) — import cuối file vì su_kien dùng _chu/_ds ở trên
from . import su_kien as _sk  # noqa: E402

KHOI.update({"tron": _sk.ve_tron, "nhan": _sk.ve_nhan, "duong_cong": _sk.ve_duong_cong, "nhan_vat": _sk.ve_nhan_vat,
             "luoi_don_vi": _sk.ve_luoi_don_vi, "thuoc_thoi_gian": _sk.ve_thuoc_thoi_gian, "nhin_lai": _sk.ve_nhin_lai})

# hoạt hình toán học (video Fine-tuning, 23/10/2026)
from . import toan as _toan  # noqa: E402

KHOI.update({"ma_tran": _toan.ve_ma_tran, "nhom_diem": _toan.ve_nhom_diem, "cot_chong": _toan.ve_cot_chong,
             "xac_suat": _toan.ve_xac_suat, "ham_log": _toan.ve_ham_log, "ban_do": _toan.ve_ban_do,
             "bang_so": _toan.ve_bang_so, "luong_tu_hoa": _toan.ve_luong_tu_hoa, "cap_dpo": _toan.ve_cap_dpo,
             "bon_model": _toan.ve_bon_model})
