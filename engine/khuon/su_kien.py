"""Khối và lớp phủ cho khuôn "giải thích sự kiện" (quyết định 0019, học từ Minh Vấn Đáp, bản nền sáng).

Khối (đăng ký vào KHOI ở khoi.py):
  tron        ảnh trong khung tròn + nhãn dưới        tron: ["ten-anh | nhãn @ cụm chữ", …]  (nhiều mục → xếp ngang)
  nhan        nhãn chữ trên thẻ trắng, đặt theo ô      nhan: ["giá in sẵn @ cụm chữ", …] hoặc {o: tren-phai, items: […]}
  duong_cong  biểu đồ đường minh hoạ: trục, điểm hiện dần, đường tự vẽ, chấm đánh dấu
  nhan_vat    nhân vật kể chuyện một tư thế           nhan_vat: "chi-tay @ cụm chữ"  hoặc {tu_the, o: goc-trai|goc-phai|giua|can-mat, at}

Khoá của cảnh (không phải khối): `chuong: "1936: cầu thiếu"` (đổi nhãn chương trên HUD), `moc: "1936"` hoặc
{nhan: "1936", at: "cụm chữ"} (thêm chấm trên trục mốc).
Khoá đầu storyboard: `hud: true | {icon: ten-anh}` · `am_thanh: true` (tự gắn tiếng hiệu ứng) · `nhac: {file, am_luong}` (mặc định 0,07 ≈ nhạc thấp hơn giọng ~18 dB, mẫu ~20 dB).
"""
import math, os, random
from .bo_cuc import mau, chia_ngang, INK, INK2, ORANGE, RED, BLUE


def _chu(x):          # nạp muộn: khoi.py import su_kien ở cuối file để đăng ký khối, import sớm ở đây sẽ thành vòng
    from .khoi import _chu as f
    return f(x)


def _ds(spec):
    from .khoi import _ds as f
    return f(spec)

VIEN = "#E3E6EB"


def _danh_sach(spec):
    """Một mục (chuỗi / dict không có `items`) → danh sách một mục; list hoặc {items: …} giữ nguyên."""
    if isinstance(spec, list) or (isinstance(spec, dict) and "items" in spec):
        return spec
    return [spec]


def _co_anh(ctx, ten):
    return bool(ctx.B.assets_dir) and os.path.exists(os.path.join(ctx.B.assets_dir, f"sketch-{ten}.png"))


def _kich_thuoc(ctx, ten):
    try:
        from PIL import Image
        return Image.open(os.path.join(ctx.B.assets_dir, f"sketch-{ten}.png")).size
    except Exception:
        return None


def _nhan_the(ctx, s, id_, text, x, y, t, size=32, color=INK, mw=520):
    """Nhãn chữ trên thẻ trắng (bản nền sáng của thẻ giấy be ở mẫu)."""
    return ctx.B.txt(s, id_, text, x, y, t, size=size, color=color, hand=False, box="card", boxColor="#FFFFFF",
                     maxWidth=mw, enter="pop", dur=0.35, font="sans", weight=600)


# ── tròn ─────────────────────────────────────────────────────────────────────
TRON_O = {"trai": (480, 470), "phai": (1440, 470), "giua": (960, 470), "tren-trai": (360, 330), "tren-phai": (1560, 330),
          "duoi-trai": (360, 760), "duoi-phai": (1560, 760)}


def ve_tron(ctx, s, spec):
    """Ảnh minh hoạ trong khung tròn trắng viền mực + nhãn bên dưới. Mục: "ten-anh | nhãn @ cụm chữ".
    Nhiều mục không ghi `o` → xếp ngang đều. `r` = bán kính (mặc định 150)."""
    items, opt = _ds(_danh_sach(spec))
    n = len(items)
    xs = chia_ngang(n, opt.get("rong", 1500)) if n > 1 else [960]
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        ten = it.get("img") or it["title"]
        nhan = it.get("body") or it.get("chu")
        r = it.get("r", opt.get("r", 150))
        x, y = TRON_O[it["o"]] if it.get("o") else (xs[i], opt.get("y", 470))
        x, y = it.get("x", x), it.get("y", y)
        t = ctx.t(it, t, 0.6, noi=f"tron[{i}]")
        ctx.B.circle(s, f"tr{i}", "", x, y, r, t, fill="#FFFFFF", enter="pop", dur=0.4, stroke=INK, strokeWidth=3)
        kt = _kich_thuoc(ctx, ten)
        w = r * 1.3
        if kt:                                   # ảnh dọc: co theo chiều cao để không tràn khung tròn
            w = min(w, r * 1.3 * kt[0] / kt[1])
        ctx.B.img(s, f"tri{i}", ten, x, y, round(w), t + 0.1, tier=it.get("tier", "low"), enter="pop", dur=0.45,
                  hand=False, trace=False)
        if nhan:
            _nhan_the(ctx, s, f"trn{i}", nhan, x, y + r + 50, t + 0.3, size=it.get("size", 32), color=mau(it.get("color"), INK))


# ── nhãn ─────────────────────────────────────────────────────────────────────
NHAN_O = {"tren": (960, 210), "tren-trai": (420, 230), "tren-phai": (1500, 230), "trai": (420, 540), "phai": (1500, 540),
          "giua": (960, 540), "duoi": (960, 880), "duoi-trai": (420, 860), "duoi-phai": (1500, 860)}


def ve_nhan(ctx, s, spec):
    """Nhãn chữ ngắn (2–6 chữ) trên thẻ trắng. Mỗi mục có `o` riêng hoặc dùng `o` chung, mục sau xếp dưới mục trước."""
    items, opt = _ds(_danh_sach(spec))
    t, dem = None, {}
    for i, it in enumerate(items):
        it = _chu(it)
        o = it.get("o", opt.get("o", "tren-phai"))
        x, y = NHAN_O[o]
        y += dem.get(o, 0) * 90
        dem[o] = dem.get(o, 0) + 1
        t = ctx.t(it, t, 0.5, noi=f"nhan[{i}]")
        _nhan_the(ctx, s, f"nh{i}", it["text"], it.get("x", x), it.get("y", y), t, size=it.get("size", 34),
                  color=mau(it.get("color"), INK), mw=opt.get("rong", 900 if o in ("giua", "tren", "duoi") else 640))


# ── biểu đồ đường ────────────────────────────────────────────────────────────
DC_O = {"phai": (1250, 520, 820, 440), "trai": (680, 520, 820, 440), "giua": (960, 540, 1100, 500)}
KIEU = {
    "giam": lambda x: 0.12 + 0.85 * math.exp(-3.2 * x),
    "tang": lambda x: 0.1 + 0.8 * x ** 1.6,
    "tang-vot": lambda x: 0.08 + 0.85 * (math.exp(3 * x) - 1) / (math.e ** 3 - 1),
    "len-xuong": lambda x: 0.15 + 0.75 * math.sin(math.pi * x) ** 1.5,
    "ngang": lambda x: 0.5,
}


def ve_duong_cong(ctx, s, spec):
    """Biểu đồ đường MINH HOẠ (hình dạng, không phải số liệu): trục + nhãn trục, `diem` chấm hiện dần quanh đường,
    rồi đường cam tự vẽ ra, `danh_dau` chấm đỏ + nhãn trên đường.
    {o: phai, truc: ["trục dọc", "trục ngang"], at: "…", kieu: giam|tang|tang-vot|len-xuong|ngang, gia_tri: [0..1, …],
     diem: 14, duong: "@ cụm chữ", danh_dau: ["ít thất nghiệp hơn @ cụm chữ #do"], minh_hoa: true}
    Có `gia_tri` thì đường đi qua đúng các giá trị (cách đều theo trục ngang)."""
    cx, cy, w, h = DC_O[spec.get("o", "phai")]
    L, R, T, B = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    t0 = ctx.t(spec, noi="duong_cong") if spec.get("at") else ctx.bat_dau + 0.4
    truc = spec.get("truc", ["", ""])
    ctx.B.line(s, "dct", [(L, T), (L, B), (R, B)], t0, color=INK, width=3, arrow=False, dur=0.6)
    if truc[0]:
        ctx.B.txt(s, "dcy", truc[0], L, T - 34, t0 + 0.3, size=28, color=INK2, hand=False, align="left")
    if len(truc) > 1 and truc[1]:
        ctx.B.txt(s, "dcx", truc[1], R, B + 40, t0 + 0.3, size=28, color=INK2, hand=False, align="right")
    gt = spec.get("gia_tri")
    if gt:
        def f(x):
            k = x * (len(gt) - 1)
            i = min(int(k), len(gt) - 2)
            return gt[i] + (gt[i + 1] - gt[i]) * (k - i)
    else:
        f = KIEU[spec.get("kieu", "giam")]

    def diem_xy(x, y):
        return (round(L + 30 + x * (w - 60), 1), round(B - 20 - y * (h - 40), 1))

    t = t0 + 0.7
    rnd = random.Random(spec.get("hat", 7))
    for i in range(spec.get("diem", 0)):
        x = (i + 0.5) / spec["diem"]
        px, py = diem_xy(x, max(0.02, min(0.98, f(x) + rnd.uniform(-0.06, 0.06))))
        ctx.B.circle(s, f"dcp{i}", "", px, py, 6, t + 0.08 * i, fill=INK2, stroke=None, enter="pop", dur=0.2)
    if spec.get("diem"):
        t += 0.08 * spec["diem"] + 0.3
    du = _chu(spec["duong"]) if spec.get("duong") else {}
    t_duong = ctx.t(du, noi="duong_cong.duong") if du.get("at") else t
    pts = [diem_xy(k / 40, f(k / 40)) for k in range(41)]
    d = "M " + " L ".join(f"{x},{y}" for x, y in pts)
    s.add({"id": "dcd", "type": "path", "d": d, "stroke": ORANGE, "strokeWidth": 6, "fill": None, "arrow": False,
           "enterAt": round(t_duong, 2), "enter": "draw", "enterDuration": 1.2, "hand": False, "rough": False})
    tt = t_duong + 1.2
    for i, it in enumerate(spec.get("danh_dau", [])):
        it = _chu(it)
        tt = ctx.t(it, tt, 0.6, noi=f"duong_cong.danh_dau[{i}]")
        x = it.get("x", 0.3 + 0.4 * i)
        px, py = diem_xy(x, f(x))
        col = mau(it.get("color"), RED)
        ctx.B.circle(s, f"dcm{i}", "", px, py, 13, tt, fill=col, stroke=None, enter="pop", dur=0.25)
        if it.get("text"):
            ctx.B.txt(s, f"dcmt{i}", it["text"], px + 24, py - 44, tt + 0.15, size=30, color=col, hand=False, align="left", maxWidth=420)
    if spec.get("minh_hoa", not gt):
        ctx.B.txt(s, "dcmh", "hình minh hoạ, không phải số liệu thật", R, B + 80, t_duong, size=22, color=INK2, hand=False, align="right")


# ── nhân vật ─────────────────────────────────────────────────────────────────
NV_O = {"goc-trai": (190, 770, 280), "goc-phai": (1730, 770, 280), "giua": (960, 600, 420), "can-mat": (960, 640, 980)}


def ve_nhan_vat(ctx, s, spec):
    """Nhân vật kể chuyện, một tư thế (ảnh sketch-nv-<tu_the>.png, nền trong suốt, tạo bằng gen_assets `nhan_vat`).
    Tư thế mới trong cùng cảnh thay tư thế cũ (cũ mờ đi). Chưa có ảnh → khung đứt giữ chỗ, để xem bố cục."""
    it = _chu(spec)
    tu_the = it.get("tu_the") or it["text"]
    x, y, w = NV_O[it.get("o", "goc-trai")]
    t = ctx.t(it, noi="nhan_vat")
    cu = getattr(s, "_nv_cuoi", None) if not hasattr(s, "_s") else getattr(s._s, "_nv_cuoi", None)
    for e in cu or []:
        e["exitAt"], e["exit"], e["exitDuration"] = round(t - 0.05, 2), "fade", 0.2
    ten = f"nv-{tu_the}"
    if _co_anh(ctx, ten):
        kt = _kich_thuoc(ctx, ten)
        if kt and it.get("o", "goc-trai") != "can-mat":       # đứng: khống chế chiều cao, không chỉ chiều rộng
            w = min(w, round(w * 1.6 * kt[0] / kt[1]))
        elif kt:                                               # cận mặt bằng ảnh toàn thân: đỉnh đầu cách mép trên 60 px
            w = 900                                            # (130 px khi có HUD), phần dưới thắt lưng ra ngoài khung
            y = round((130 if getattr(ctx, "hud", False) else 60) + w * kt[1] / kt[0] / 2)
        moi = [ctx.B.img(s, "nv", ten, x, y, w, t, enter="pop", dur=0.35, hand=False, trace=False,
                         idle={"type": "rung", "amplitude": 1.5, "speed": 1.2})]
    else:
        h = round(w * (0.62 if it.get("o") == "can-mat" else 1.6))
        moi = [ctx.B.box(s, "nv", f"nhân vật · {tu_the}", x, y - (0 if it.get("o") == "can-mat" else 0), w, h, t,
                         fill="#FFFFFF", stroke=INK2, label_color=INK2, size=26, hand=False, enter="pop", dur=0.3)]
    moi = [e for e in moi if e]
    goc = s._s if hasattr(s, "_s") else s
    goc._nv_cuoi = moi


# ── lưới đơn vị (có ở cả 2 video mẫu, audit.md mục 2.5) ───────────────────────
LDV_O = {"giua": (960, 520, 1300, 520), "phai": (1300, 520, 900, 520), "trai": (620, 520, 900, 520)}


def ve_luoi_don_vi(ctx, s, spec):
    """N icon = N thứ, để nói số lớn bằng hình (100 chấm = 100 người lao động; lưới nhà = 2.309 hộ).
    {so: 100, cot: 20, to: 37, at: "…", to_at: "cụm chữ lúc tô", icon: cham|o|<ten-anh>, color: xam, mau_to: cam,
     nhan: "100 người lao động", nhan_to: "37 người thất nghiệp", o: giua|phai|trai}
    Hiện theo hàng (nhanh, ~1,2 s cả lưới), rồi tô `to` ô đầu bằng màu nhấn lúc đọc tới `to_at`."""
    n = int(spec["so"])
    if n > 400:
        raise ValueError(f"luoi_don_vi: so={n} quá nhiều phần tử (≤ 400); quy ra đơn vị lớn hơn, ghi rõ ở `nhan`")
    cot = int(spec.get("cot", min(20, max(5, round(math.sqrt(n * 2))))))
    hang = math.ceil(n / cot)
    cx, cy, w, h = LDV_O[spec.get("o", "giua")]
    buoc = min(w / cot, h / hang, spec.get("o_max", 80))      # lưới ít ô: không phóng chấm to quá
    r = buoc * 0.36
    x0, y0 = cx - buoc * (cot - 1) / 2, cy - buoc * (hang - 1) / 2
    t0 = ctx.t(spec, noi="luoi_don_vi") if spec.get("at") else ctx.bat_dau + 0.4
    icon = spec.get("icon", "cham")
    col = mau(spec.get("color"), INK2)

    def o(i, id_, t, c):
        x, y = round(x0 + (i % cot) * buoc, 1), round(y0 + (i // cot) * buoc, 1)
        if icon == "cham":
            ctx.B.circle(s, id_, "", x, y, round(r, 1), t, fill=c, stroke=None, enter="pop", dur=0.2)
        elif icon == "o":
            ctx.B.box(s, id_, "", x, y, round(r * 1.8), round(r * 1.8), t, fill=c, stroke=None, hand=False, enter="pop", dur=0.2,
                      radius=4)
        else:
            ctx.B.img(s, id_, icon, x, y, round(buoc * 0.85), t, tier="low", enter="pop", dur=0.2, hand=False, trace=False)

    for i in range(n):
        o(i, f"ld{i}", round(t0 + 1.2 * (i // cot) / max(1, hang), 2), col)
    t = t0 + 1.4
    if spec.get("nhan"):
        ctx.B.txt(s, "ldn", spec["nhan"], cx, cy + buoc * hang / 2 + 40, t, size=32, color=INK2, hand=False, font="sans", weight=600)
    if spec.get("to"):
        tt = ctx.t({"at": spec["to_at"]}, noi="luoi_don_vi.to_at") if spec.get("to_at") else t + 0.8
        mt = mau(spec.get("mau_to"), ORANGE)
        for i in range(int(spec["to"])):
            o(i, f"ldt{i}", round(tt + 0.6 * i / max(1, spec["to"]), 2), mt)
        if spec.get("nhan_to"):
            ctx.B.txt(s, "ldnt", spec["nhan_to"], cx, cy - buoc * hang / 2 - 44, tt + 0.3, size=34, color=mt, hand=False, font="sans",
                      weight=600)


# ── thước so thời lượng (audit.md mục 2.6) ─────────────────────────────────────
def ve_thuoc_thoi_gian(ctx, s, spec):
    """So độ dài thời gian bằng thanh có vạch: "113 tháng | 4/1973 – 8/1982 = 113 @ cụm chữ #do".
    Thanh dài theo tỉ lệ giá trị (dài nhất = `rong`, mặc định 1500), mỗi vạch = 1 đơn vị (≤ 200 vạch, nhiều hơn thì vạch theo `vach`)."""
    items, opt = _ds(_danh_sach(spec))
    rong, x0 = opt.get("rong", 1500), opt.get("x0", 210)
    vals = [_chu(it).get("value", 1) for it in items]
    vmax = max(vals) or 1
    y = opt.get("y", 380 if len(items) > 1 else 520)
    buoc_y = opt.get("buoc_y", 230)
    t = None
    for i, it in enumerate(items):
        it = _chu(it)
        t = ctx.t(it, t, 1.0, noi=f"thuoc_thoi_gian[{i}]")
        col = mau(it.get("color"), [RED, BLUE][i % 2] if len(items) > 1 else RED)
        v, yy = it.get("value", 1), y + buoc_y * i
        dai = rong * v / vmax
        s.add({"id": f"tt{i}", "type": "bar", "horizontal": True, "x": round(x0 + dai / 2, 1), "y": yy, "w": round(dai, 1), "maxH": 34,
               "value": 1, "color": col, "track": None, "label": "", "showValue": False, "enterAt": round(t, 2), "growDuration": 1.4,
               "enter": "grow"})
        vach = opt.get("vach", 1 if v <= 200 else math.ceil(v / 200))
        k = int(v // vach)
        if k > 1:
            d = " ".join(f"M {round(x0 + dai * j / k, 1)},{yy - 17} L {round(x0 + dai * j / k, 1)},{yy + 17}" for j in range(1, k))
            s.add({"id": f"ttv{i}", "type": "path", "d": d, "stroke": "#FFFFFF", "strokeWidth": 2, "fill": None, "arrow": False,
                   "enterAt": round(t + 0.2, 2), "enter": "draw", "enterDuration": 1.2, "hand": False, "rough": False})
        ctx.B.txt(s, f"ttt{i}", it["title"], x0, yy - 52, t, size=40, color=col, hand=False, align="left", font="sans", weight=700)
        if it.get("body") and it["body"] != it["title"]:
            ctx.B.txt(s, f"ttb{i}", it["body"], x0, yy + 50, t + 0.4, size=26, color=INK2, hand=False, align="left", font="sans")


# ── nhìn lại: trục ngang đi ngược mốc (audit.md mục 2.9) ──────────────────────
def ve_nhin_lai(ctx, s, spec):
    """Đoạn nhìn lại cuối video: một trục ngang, đi lần lượt từng mốc (thường từ mới về cũ), mỗi mốc gọi lại đúng hình
    của chương đó; hình mốc trước mờ đi khi mốc sau hiện. Mục: "2003 | ba phương trình @ cụm chữ" hoặc
    {nhan: "2003", img: ten-anh, chu: "ba phương trình", at}. Nhãn là năm → chấm đặt theo tỉ lệ năm, không thì cách đều."""
    items = [_chu(it) for it in (_ds(_danh_sach(spec))[0])]
    nhans = [str(it.get("nhan") or it["title"]) for it in items]
    so = [_so(x) for x in nhans]
    L, R, Y = 200, 1720, spec.get("y", 300) if isinstance(spec, dict) else 300
    if all(v is not None for v in so) and max(so) > min(so):
        xs = [L + (R - L) * (v - min(so)) / (max(so) - min(so)) for v in so]
    else:
        xs = [L + (R - L) * i / max(1, len(items) - 1) for i in range(len(items))]
    t = None
    truoc = []
    for i, (it, x) in enumerate(zip(items, xs)):
        t = ctx.t(it, t, 2.0, noi=f"nhin_lai[{i}]")
        if i == 0:
            ctx.B.line(s, "nlt", [(L - 60, Y), (R + 60, Y)], t - 0.4, color=INK2, width=3, arrow=False, dur=0.5)
        for e in truoc:
            e.setdefault("exitAt", round(t - 0.05, 2)); e.setdefault("exit", "fade"); e.setdefault("exitDuration", 0.25)
        ctx.B.circle(s, f"nlc{i}", "", round(x, 1), Y, 11, t, fill=ORANGE, stroke=None, enter="pop", dur=0.25)
        moi = [_nhan_the(ctx, s, f"nln{i}", nhans[i], round(x, 1), Y - 52, t, size=30)]
        if it.get("img"):
            moi.append(ctx.B.img(s, f"nli{i}", it["img"], round(min(max(x, 420), 1500), 1), Y + 300, spec.get("rong_anh", 500) if isinstance(spec, dict) else 500, t + 0.2, tier="low",
                                 enter="pop", dur=0.4, hand=False, trace=False))
        chu = it.get("chu") or (it.get("body") if it.get("body") != it.get("title") else None)
        if chu:
            moi.append(ctx.B.txt(s, f"nlx{i}", chu, round(min(max(x, 420), 1500), 1), Y + (580 if it.get("img") else 200), t + 0.3,
                                 size=36, color=INK, hand=False, font="sans", weight=600, maxWidth=760))
        truoc = [e for e in moi if e]


# ── kiểm: nhân vật kể chuyện không lấn át (audit.md mục 5.2) ─────────────────────
def kiem_hud(tl, assets_dir, day=115):
    """Có HUD: cảnh báo phần tử nào có mép trên lấn vào dải `day` px trên cùng (nhãn chương + trục năm) — góp ý của Lộc
    17/10/2026 "hình ảnh bị đè vào thanh mục lục năm phía trên". Ảnh tính theo kích thước file thật."""
    if not tl.get("hud"):
        return []
    from PIL import Image
    kt, out = {}, []
    for sc in tl["scenes"]:
        for e in sc["elements"]:
            ma = e["id"].split(".")[-1]
            if ma.startswith("nguon") or "y" not in e:
                continue
            y, tren = e["y"], None
            if e["type"] == "image":
                f = os.path.join(assets_dir, e["src"].split("/")[-1])
                if f not in kt:
                    try:
                        kt[f] = Image.open(f).size
                    except Exception:
                        kt[f] = None
                if kt[f]:
                    tren = y - e["w"] * kt[f][1] / kt[f][0] / 2
            elif e["type"] == "text":
                co = e.get("size", 40)
                tren = y - co * (0.95 if e.get("box") in ("card", "pill") else 0.65)
            elif e["type"] in ("rect", "card"):
                tren = y - e.get("h", 0) / 2
            elif e["type"] == "circle":
                tren = y - e.get("r", 0)
            if tren is not None and tren < day:
                out.append(f"{sc['id']} · {ma}: mép trên {round(tren)} px, lấn vào dải HUD ({day} px trên cùng)")
    return out


def kiem_chong(tl, assets_dir, nguong=0.15):
    """Chữ dính chữ / chữ đè ảnh trong cùng cảnh, lúc cả hai đang hiện (góp ý Lộc 17/10/2026 trên v2: "hình ảnh, chữ còn bị
    dính nhau"). Khung chữ ước lượng theo số ký tự × cỡ chữ; ảnh theo kích thước file thật. Báo khi phần chồng > `nguong`
    diện tích khung nhỏ hơn. Bỏ qua: dòng nguồn, khung viền ảnh, nhãn ghi trên ảnh (-tag), ảnh trong khung tròn."""
    from PIL import Image
    kt, out = {}, []

    def khung(e):
        x, y = e.get("x"), e.get("y")
        if x is None or y is None:
            return None
        if e["type"] == "text":
            co, mw = e.get("size", 40), e.get("maxWidth") or 1500
            dai = len(e.get("text", "")) * co * 0.55
            w, dong = min(mw, dai), max(1, -(-dai // mw))
            h = dong * co * 1.25 + (co * 0.6 if e.get("box") in ("card", "pill") else 0)
            canh = e.get("align", "center")
            x0 = x if canh == "left" else (x - w if canh == "right" else x - w / 2)
            return (x0, y - h / 2, x0 + w, y + h / 2)
        if e["type"] == "image":
            f = os.path.join(assets_dir, e["src"].split("/")[-1])
            if f not in kt:
                try:
                    kt[f] = Image.open(f).size
                except Exception:
                    kt[f] = None
            if not kt[f]:
                return None
            w = e["w"]; h = w * kt[f][1] / kt[f][0]
            return (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
        if e["type"] == "counter":
            co = e.get("size", 88); w = (len(str(e.get("to", ""))) + len(e.get("suffix", "")) + len(e.get("prefix", ""))) * co * 0.6
            return (x - w / 2, y - co / 2, x + w / 2, y + co / 2)
        return None

    for sc in tl["scenes"]:
        els = []
        for e in sc["elements"]:
            ma = e["id"].split(".")[-1]
            if ma.startswith("nguon") or ma.endswith("-fr") or ma.endswith("-tag") or ma.startswith("tri") or ma.startswith("nv"):
                continue
            b = khung(e)
            if b:
                els.append((ma, e["type"], b, e.get("enterAt", sc["start"]), e.get("exitAt") or sc["end"]))
        for i in range(len(els)):
            for j in range(i + 1, len(els)):
                a, b = els[i], els[j]
                if a[1] != "text" and b[1] != "text":
                    continue                                  # chỉ xét cặp có chữ
                if a[4] <= b[3] or b[4] <= a[3]:
                    continue                                  # không cùng lúc trên màn hình
                (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = a[2], b[2]
                ix, iy = min(ax1, bx1) - max(ax0, bx0), min(ay1, by1) - max(ay0, by0)
                if ix <= 0 or iy <= 0:
                    continue
                nho = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0)) or 1
                if ix * iy / nho > nguong:
                    out.append(f"{sc['id']} · {a[0]} ↔ {b[0]}: chồng {round(ix * iy / nho * 100)}% (chữ dính / đè)")
    return out


def tat_can_mat(tl):
    """Ảnh cận mặt (ảnh toàn thân phóng to) dài quá mép dưới cảnh → lòi sang cảnh nằm ngay dưới trên bảng vẽ (thấy ở s41b,
    17/10/2026). Cho mờ đi 0,4 s trước khi cảnh kết thúc, trước lúc camera lia sang cảnh sau."""
    for sc in tl["scenes"]:
        for e in sc["elements"]:
            ma = e["id"].split(".")[-1]
            if (ma == "nv" or ma.startswith("nv-")) and e.get("w", 0) >= 900 and not e.get("exitAt"):
                e["exitAt"], e["exit"], e["exitDuration"] = round(sc["end"] - 0.9, 2), "fade", 0.4


def kiem_nhan_vat(tl):
    """Cảnh báo khi nhân vật kể chuyện chiếm > 20% thời lượng (mẫu 5–15%) hoặc cận mặt > 1 lần."""
    out, tong, can = [], 0.0, 0
    for sc in tl["scenes"]:
        for e in sc["elements"]:
            ma = e["id"].split(".")[-1]
            if not (ma == "nv" or ma.startswith("nv-")):
                continue
            tong += (e.get("exitAt") or sc["end"]) - e["enterAt"]
            if e.get("w", 0) >= 900:
                can += 1
    dai = tl["duration"] or 1
    if tong / dai > 0.20:
        out.append(f"nhân vật kể chuyện hiện {tong / dai:.0%} thời lượng (mẫu 5–15%): chỉ dùng ở câu hỏi mở đầu, phản ứng trước con số, mở phần mới, CTA")
    if can > 1:
        out.append(f"nhân vật cận mặt {can} lần (mẫu ≤ 1 lần/video)")
    return out


# ── HUD + âm thanh (gọi từ dung.py sau Board.finish) ─────────────────────────
def _so(x):
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        return None


def gan_hud(tl, sb, chuong, moc):
    """chuong: [(scene_dict, nhãn)] · moc: [(scene_dict | None, giây | None, nhãn)] → tl['hud'].
    Vị trí chấm: nhãn đều là số (năm) → theo tỉ lệ năm; không thì cách đều theo thứ tự."""
    cfg = sb.get("hud")
    if not cfg:
        return
    cfg = cfg if isinstance(cfg, dict) else {}
    if cfg.get("muc_luc"):              # mục lục header của video tuần (gop-y 25/10/2026): mục = nhãn `chuong` của các cảnh
        tl["hud"] = {"icon": None, "chapters": [], "marks": [], "end": tl["duration"],
                     "mucLuc": [{"at": round(sc["start"], 2), "label": nhan} for sc, nhan in chuong]}
        return
    ch = [{"at": round(sc["start"] + 0.1, 2), "label": nhan} for sc, nhan in chuong]
    mk = [{"at": round(t if t is not None else sc["start"] + 0.3, 2), "label": str(nhan)} for sc, t, nhan in moc]
    so = [_so(m["label"]) for m in mk]
    if mk and all(v is not None for v in so) and max(so) > min(so):
        lo, hi = min(so), max(so)
        for m, v in zip(mk, so):
            m["pos"] = round(0.03 + 0.94 * (v - lo) / (hi - lo), 3)
    else:
        thu_tu = list(dict.fromkeys(m["label"] for m in mk))
        for m in mk:
            m["pos"] = round(0.03 + 0.94 * thu_tu.index(m["label"]) / max(1, len(thu_tu) - 1), 3)
    tl["hud"] = {"icon": f"assets/sketch-{cfg['icon']}.png" if cfg.get("icon") else None, "chapters": ch, "marks": mk}


SFX_AM_LUONG = {"pop": 0.22, "lach_cach": 0.25, "tick": 0.28, "whoosh": 0.22, "ting": 0.28, "ve": 0.1}
# Luật gắn tiếng theo audit âm thanh mẫu (phong-cach/minh-van-dap/am-thanh.md): chỉ ~1/6 vật hiện có tiếng, 1,2–3,4 tiếng/phút,
# KHÔNG gắn cho chuyển cảnh, nổ 0,1 s sau khi vật hiện. Ưu tiên cao được chọn trước khi vượt ngân sách.
SFX_UU_TIEN = {"so": 6, "danh_dau": 5, "can_mat": 5, "luoi": 4, "dau_nhom": 3, "duong": 2}
SFX_TRE, SFX_CACH_MIN, SFX_MOI_PHUT_MAX = 0.1, 1.5, 3


def _quy_giay(tl, moc, tu):
    """`tu` của một đoạn nhạc: id cảnh → giây mở cảnh; số → giây; chuỗi khác → cụm chữ trong lời."""
    if isinstance(tu, (int, float)):
        return float(tu)
    for sc in tl["scenes"]:
        if sc["id"] == tu:
            return float(sc["start"])
    goc, moc.goc = moc.goc, 0                    # nhạc khai ở đầu storyboard: tìm cụm chữ từ đầu bài, không từ cảnh cuối
    t, _ = moc.tim(tu, 1, noi=f"nhac · {tu}")
    moc.goc = goc
    return float(t or 0.0)


def gan_am_thanh(tl, sb, moc=None):
    """Tự gắn tiếng hiệu ứng theo phần tử (studio/public/common/sfx, tạo bằng pipeline/tao_sfx.py) + nhạc nền.
    Hai tiếng cách nhau < 0,3 s thì giữ tiếng ưu tiên hơn (ting > whoosh > pop > tick > ve).
    `nhac:` là danh sách đoạn → quy ra giây vào tl["_nhac_cues"]; dung.py trộn thành music.wav (pipeline/tron_nhac.py)."""
    if isinstance(sb.get("nhac"), list):
        cues = [dict(c, tu=_quy_giay(tl, moc, c.get("tu", 0))) for c in sb["nhac"]]
        cues.sort(key=lambda c: c["tu"])
        for c, sau in zip(cues, cues[1:] + [None]):
            c["den"] = sau["tu"] if sau else tl["duration"]
        tl["_nhac_cues"] = cues
    elif sb.get("nhac"):
        n = sb["nhac"] if isinstance(sb["nhac"], dict) else {"file": sb["nhac"]}
        tl["music"] = {"src": n["file"], "volume": float(n.get("am_luong", 0.07)), "fadeIn": 2.0, "fadeOut": 4.0}
    if not sb.get("am_thanh"):
        return
    ung = []                                         # (thời điểm, tiếng, ưu tiên)
    for sc in tl["scenes"]:
        nhom_da = set()
        for e in sc["elements"]:
            ma = e["id"].split(".")[-1]
            a = e.get("enterAt", 0) + SFX_TRE
            ep = e.pop("sfx", None)
            if ep:
                ung.append((a, ep, 9)); continue
            if e["type"] == "counter":
                ung.append((e.get("countAt", e.get("enterAt", 0)) + SFX_TRE, "pop", SFX_UU_TIEN["so"]))
            elif ma.startswith("dcm") and e["type"] == "circle":                 # chấm đánh dấu trên đồ thị
                ung.append((a, "pop", SFX_UU_TIEN["danh_dau"]))
            elif ma.startswith("nv") and e.get("w", 0) >= 900:                   # cận mặt nhân vật
                ung.append((a, "ting", SFX_UU_TIEN["can_mat"]))
            elif ma in ("ld0", "ldt0"):                                         # lưới đơn vị: hàng đầu / lúc tô
                ung.append((a, "lach_cach", SFX_UU_TIEN["luoi"]))
            elif ma.startswith("dcd"):                                          # đường đồ thị vẽ ra
                ung.append((a, "whoosh", SFX_UU_TIEN["duong"]))
            # khối của video tuần / video có ảnh nguồn (gop-y 25/10/2026: nghe "ngang, buồn ngủ" khi chỉ có vài tiếng)
            elif ma.startswith("akm") and e["type"] == "rect":                  # khoanh câu chứa số trên ảnh bài gốc
                ung.append((a, "ve", SFX_UU_TIEN["danh_dau"]))
            elif ma == "ttc":                                                    # thẻ tin mở một câu chuyện
                ung.append((a, "whoosh", SFX_UU_TIEN["can_mat"]))
            elif ma == "hkl":                                                    # hộp chốt ý
                ung.append((a, "ting", SFX_UU_TIEN["luoi"]))
            elif ma.startswith("ckm"):                                           # dấu ✓ của checklist
                ung.append((a, "tick", SFX_UU_TIEN["dau_nhom"]))
            elif ma.startswith("cot") and e["type"] == "bar" and "cot" not in nhom_da:
                nhom_da.add("cot")
                ung.append((e.get("growAt", e.get("enterAt", 0)) + SFX_TRE, "pop", SFX_UU_TIEN["dau_nhom"]))
            elif ma[:2] in ("tr", "nl", "tt") and ma[:2] not in nhom_da and e["type"] in ("circle", "bar"):
                nhom_da.add(ma[:2])                                             # vật đầu tiên của nhóm (khung tròn, nhìn lại, thước)
                ung.append((a, "pop", SFX_UU_TIEN["dau_nhom"]))
    giu = []
    for a, ten, ut in sorted(ung, key=lambda x: (-x[2], x[0])):
        if any(abs(a - b) < SFX_CACH_MIN for b, _ in giu):
            continue
        if sum(1 for b, _ in giu if abs(a - b) < 30) >= SFX_MOI_PHUT_MAX:
            continue
        giu.append((a, ten))
    giu.sort()
    tl["sfx"] = [{"src": f"common/sfx/{ten}.wav", "at": round(max(0.0, a), 2), "volume": SFX_AM_LUONG[ten]} for a, ten in giu]
