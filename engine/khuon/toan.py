"""Khối hoạt hình TOÁN HỌC cho storyboard (23/10/2026, video Fine-tuning): số liệu thật hoặc tự tính, vẽ đúng tỉ lệ,
mỗi bước của phép tính hiện đúng lúc lời đọc tới — kiểu giải thích bằng hình của các kênh nước ngoài (3Blue1Brown…).
Mọi số trên hình do code tính từ tham số, không gõ tay → không lệch giữa lời và hình.

  ma_tran     LoRA: ma trận W d×d đóng băng + B (d×r) × A (r×d) = ΔW, đếm tham số, tỉ lệ %
              {d: 4096, r: 16, at, khoa_at, ba_at, so_at}
  nhom_diem   GRPO: N câu trả lời của một đề → điểm → vạch trung bình → lợi thế (r − tb) / độ lệch chuẩn, cột lên/xuống
              {diem: [1, 0, 0.5, …], at, tb_at, loi_the_at}
  cot_chong   bộ nhớ GPU: cột chồng tầng (GB) theo tỉ lệ thật + vạch giới hạn card
              {cot: [{ten, at, tang: [{nhan, gb, mau}]}], gioi_han: {nhan, gb, at}, max_gb}
  xac_suat    SFT: cột xác suất các token kế tiếp, token đúng tô màu; `sau` = phân bố sau huấn luyện; loss = −ln p đếm theo
              {truoc: "total:", items: [{tok, p}], dung: "1199", at, sau: {at, items: [{tok, p}]}}
  ham_log     đồ thị thật y = −ln(p) trên [0,05; 1], chấm chạy từ p0 tới p1 đúng lúc đọc
              {p0: 0.2, p1: 0.9, at, chay_at}
Đăng ký vào KHOI ở khoi.py. Tất cả dùng vùng dưới dải HUD (y ≥ 150).
"""
import math
from .bo_cuc import mau, INK, INK2, ORANGE, RED, BLUE

XANH_LA = "#1F9D55"
XAM = "#C9CED6"


def _vn(x, so_le=0):
    """Số kiểu Việt: 16.777.216 · 0,78."""
    s = f"{x:,.{so_le}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _t(ctx, spec, khoa, truoc, buoc, noi):
    v = spec.get(khoa)
    if v:
        return ctx.t({"at": v}, noi=f"{noi}.{khoa}")
    return truoc + buoc


def _luoi(s, id_, x0, y0, w, h, n, t, color=XAM):
    """Lưới n×n trong khung (đường mảnh) — để ma trận trông như ma trận."""
    d = []
    for i in range(1, n):
        d.append(f"M {x0 + w * i / n:.1f} {y0} L {x0 + w * i / n:.1f} {y0 + h}")
        d.append(f"M {x0} {y0 + h * i / n:.1f} L {x0 + w} {y0 + h * i / n:.1f}")
    s.add({"id": id_, "type": "path", "d": " ".join(d), "stroke": color, "strokeWidth": 2, "fill": None, "arrow": False,
           "enterAt": round(t, 2), "enter": "fade", "enterDuration": 0.5, "hand": False, "rough": False})


# ── LoRA ────────────────────────────────────────────────────────────────────
def ve_ma_tran(ctx, s, spec):
    B = ctx.B
    d, r = int(spec.get("d", 4096)), int(spec.get("r", 16))
    t0 = ctx.t(spec, noi="ma_tran") if spec.get("at") else ctx.bat_dau + 0.3
    S, cy = 340, 600                       # cạnh ma trận vuông (px), tâm dọc
    wx = 330                               # tâm W
    B.box(s, "mtW", "", wx, cy, S, S, t0, fill="#FFFFFF", stroke=INK, hand=False, enter="pop", dur=0.4, radius=6)
    _luoi(s, "mtWl", wx - S / 2, cy - S / 2, S, S, 12, t0 + 0.2)
    B.txt(s, "mtWt", f"W · {_vn(d)} × {_vn(d)}", wx, cy - S / 2 - 40, t0 + 0.2, size=34, color=INK, hand=False)
    B.counter(s, "mtWn", wx, cy + S / 2 + 60, t0 + 0.4, d * d, size=46, color=INK, dur=1.2, suffix=" số")
    tk = _t(ctx, spec, "khoa_at", t0, 2.0, "ma_tran")
    B.box(s, "mtK", "ĐÓNG BĂNG", wx, cy, S, S, tk, fill="rgba(201,206,214,0.72)", stroke=INK2, label_color=INK,
          size=38, hand=False, enter="fade", dur=0.4, radius=6, labelWeight=800)
    tb = _t(ctx, spec, "ba_at", tk, 1.5, "ma_tran")
    rong = max(16, S * r / d)              # r/d thật quá mảnh để thấy (16/4096 · 340 ≈ 1,3 px) → tối thiểu 16 px, có ghi chú
    B.txt(s, "mtPlus", "+", 560, cy, tb, size=80, color=INK, hand=False, enter="pop", dur=0.3)
    bx = 660
    B.box(s, "mtB", "", bx, cy, rong, S, tb + 0.2, fill=ORANGE, stroke=INK, hand=False, enter="grow", dur=0.5, radius=3)
    B.txt(s, "mtBt", f"B · {_vn(d)}×{r}", bx, cy - S / 2 - 40, tb + 0.3, size=30, color=ORANGE, hand=False)
    B.txt(s, "mtX", "×", 740, cy, tb + 0.6, size=64, color=INK, hand=False, enter="pop", dur=0.3)
    ax = 960
    B.box(s, "mtA", "", ax, cy, S, rong, tb + 0.8, fill=ORANGE, stroke=INK, hand=False, enter="grow", dur=0.5, radius=3)
    B.txt(s, "mtAt", f"A · {r}×{_vn(d)}", ax, cy - 50, tb + 0.9, size=30, color=ORANGE, hand=False)
    B.txt(s, "mtEq", "=", 1200, cy, tb + 1.3, size=80, color=INK, hand=False, enter="pop", dur=0.3)
    dx = 1460
    B.box(s, "mtD", "", dx, cy, S, S, tb + 1.5, fill="rgba(242,97,29,0.08)", stroke=ORANGE, hand=False, enter="pop",
          dur=0.4, radius=6, dashed=True)
    _luoi(s, "mtDl", dx - S / 2, cy - S / 2, S, S, 12, tb + 1.7, color="#F6C2A6")
    B.txt(s, "mtDt", "ΔW = B·A · cùng cỡ W", dx, cy - S / 2 - 40, tb + 1.6, size=34, color=ORANGE, hand=False)
    B.txt(s, "mtGhi", "bề ngang B, A phóng to cho dễ thấy", 960, cy + S / 2 + 20, tb + 1.0, size=22, color=INK2, hand=False)
    ts = _t(ctx, spec, "so_at", tb, 2.5, "ma_tran")
    n_lora = 2 * d * r
    B.counter(s, "mtLn", dx, cy + S / 2 + 60, ts, n_lora, size=46, color=ORANGE, dur=1.0, suffix=" số phải học")
    B.txt(s, "mtPct", f"= {_vn(100 * n_lora / (d * d), 2)}% của W  (tự tính)", dx, cy + S / 2 + 120, ts + 0.8, size=32,
          color=ORANGE, hand=False, enter="pop", dur=0.3)


# ── GRPO ────────────────────────────────────────────────────────────────────
def ve_nhom_diem(ctx, s, spec):
    B = ctx.B
    diem = [float(x) for x in spec["diem"]]
    n = len(diem)
    tb = sum(diem) / n
    lech = math.sqrt(sum((x - tb) ** 2 for x in diem) / n) or 1.0
    adv = [(x - tb) / lech for x in diem]
    t0 = ctx.t(spec, noi="nhom_diem") if spec.get("at") else ctx.bat_dau + 0.3
    W = 1560
    xs = [180 + W * (i + 0.5) / n for i in range(n)]
    cw = min(150, W / n - 24)
    B.box(s, "ndDe", spec.get("de", "1 đề bài"), 960, 205, 300, 64, t0, fill="#FFFFFF", stroke=INK, size=30, hand=False,
          enter="pop", dur=0.3)
    for i, x in enumerate(xs):
        ti = t0 + 0.35 + 0.12 * i
        B.line(s, f"ndL{i}", [(960, 240), (x, 300)], ti, color=XAM, width=2, arrow=False, dur=0.3)
        B.box(s, f"ndC{i}", f"câu {i + 1}", x, 340, cw, 70, ti + 0.15, fill="#FFFFFF", stroke=INK, size=26, hand=False,
              enter="pop", dur=0.25)
    tdiem = _t(ctx, spec, "diem_at", t0 + 0.35 + 0.12 * n, 0.4, "nhom_diem")
    for i, (x, v) in enumerate(zip(xs, diem)):
        col = XANH_LA if v >= 0.99 else RED if v <= 0.01 else ORANGE
        B.txt(s, f"ndS{i}", _vn(v, 1).rstrip("0").rstrip(",") if v % 1 else _vn(v), x, 420, tdiem + 0.25 * i, size=44,
              color=col, hand=False, enter="pop", dur=0.25)
    # biểu đồ lợi thế: đường gốc y0, đơn vị 110 px
    y0, k = 700, 110
    ttb = _t(ctx, spec, "tb_at", tdiem + 0.25 * n, 0.6, "nhom_diem")
    B.line(s, "ndTb", [(150, y0), (1770, y0)], ttb, color=INK, width=3, arrow=False, dur=0.6, dashed=True)
    B.txt(s, "ndTbt", f"trung bình nhóm = {_vn(tb, 2).rstrip('0').rstrip(',')}", 1770, y0 + 34, ttb + 0.2, size=28,
          color=INK, hand=False, align="right", z=6)
    tl = _t(ctx, spec, "loi_the_at", ttb, 1.5, "nhom_diem")
    for i, (x, a) in enumerate(zip(xs, adv)):
        h = max(6, abs(a) * k)
        col = XANH_LA if a > 0.01 else RED if a < -0.01 else XAM
        yc = y0 - h / 2 if a >= 0 else y0 + h / 2
        B.box(s, f"ndA{i}", "", x, yc, cw * 0.6, h, tl + 0.1 * i, fill=col, stroke=None, hand=False, enter="grow",
              dur=0.4, radius=4)
        nhan = ("+" if a > 0.01 else "") + _vn(a, 2) if abs(a) > 0.005 else "0"
        B.txt(s, f"ndAt{i}", nhan, x, (y0 - h - 26) if a >= 0 else (y0 + h + 30), tl + 0.1 * i + 0.3, size=28, color=col,
              hand=False)
    B.txt(s, "ndF", "lợi thế = (điểm − trung bình) ÷ độ lệch chuẩn", 960, 985, tl + 0.4, size=36, color=INK,
          hand=False, enter="pop", dur=0.35)
    B.txt(s, "ndG", f"độ lệch chuẩn = {_vn(lech, 2)} (tự tính)", 1760, 930, tl + 0.8, size=24, color=INK2, hand=False,
          align="right")


# ── Bộ nhớ GPU ──────────────────────────────────────────────────────────────
def ve_cot_chong(ctx, s, spec):
    B = ctx.B
    cot = spec["cot"]
    tong = [sum(t["gb"] for t in c["tang"]) for c in cot]
    max_gb = spec.get("max_gb") or max(tong + [spec.get("gioi_han", {}).get("gb", 0)]) * 1.08
    day, cao = 930, 680                     # đáy và chiều cao vùng vẽ
    px = cao / max_gb
    xs = spec.get("x") or [520 + 560 * i for i in range(len(cot))]
    t_truoc = ctx.bat_dau + 0.3
    B.line(s, "ccDay", [(240, day), (1700, day)], t_truoc, color=INK, width=3, arrow=False, dur=0.4)
    for j, (c, x) in enumerate(zip(cot, xs)):
        tc = ctx.t({"at": c["at"]}, noi=f"cot_chong[{j}]") if c.get("at") else t_truoc + 0.6
        y = day
        for i, tg in enumerate(c["tang"]):
            h = tg["gb"] * px
            ti = ctx.t({"at": tg["at"]}, noi=f"cot_chong[{j}].tang[{i}]") if tg.get("at") else tc + 0.45 * i
            B.box(s, f"cc{j}_{i}", "", x, y - h / 2, 220, h, ti, fill=mau(tg.get("mau"), ORANGE), stroke=INK,
                  hand=False, enter="grow", dur=0.45, radius=2, strokeWidth=3)
            if h >= 34:
                B.txt(s, f"cc{j}_{i}t", f"{tg['nhan']} · {_vn(tg['gb'])} GB", x + 130, y - h / 2, ti + 0.2, size=26,
                      color=INK, hand=False, align="left", z=6, box="card", boxColor="#FFFFFF")
            y -= h
        B.txt(s, f"cc{j}n", c["ten"], x, day + 45, tc, size=32, color=INK, hand=False)
        B.counter(s, f"cc{j}s", x, y - 45, tc + 0.45 * len(c["tang"]), tong[j], size=50, color=INK, dur=0.8,
                  suffix=" GB", prefix="~")
        t_truoc = tc
    g = spec.get("gioi_han")
    if g:
        tg = ctx.t({"at": g["at"]}, noi="cot_chong.gioi_han") if g.get("at") else t_truoc + 1.0
        yg = day - g["gb"] * px
        B.line(s, "ccG", [(240, yg), (1700, yg)], tg, color=RED, width=4, arrow=False, dur=0.6, dashed=True)
        B.txt(s, "ccGt", g["nhan"], 1700, yg - 28, tg + 0.3, size=30, color=RED, hand=False, align="right")
    B.txt(s, "ccTu", spec.get("ghi", "tự tính · chưa gồm activation"), 1700, day + 45, ctx.bat_dau + 0.5, size=22,
          color=INK2, hand=False, align="right")


# ── SFT: xác suất token và loss ─────────────────────────────────────────────
def _cot_xac_suat(ctx, s, id_, items, dung, t, x0=260, w=820, day=820, cao=440, ra=None):
    B = ctx.B
    n = len(items)
    bw = w / n
    out = []
    for i, it in enumerate(items):
        x = x0 + bw * (i + 0.5)
        h = max(4, it["p"] * cao)
        col = ORANGE if it["tok"] == dung else XAM
        kw = {"exitAt": ra, "exit": "fade", "exitDuration": 0.25} if ra else {}
        out.append(B.box(s, f"{id_}{i}", "", x, day - h / 2, bw * 0.62, h, t + 0.08 * i, fill=col, stroke=None, hand=False,
                         enter="grow", dur=0.45, radius=4, **kw))
        B.txt(s, f"{id_}p{i}", _vn(it["p"], 2), x, day - h - 26, t + 0.08 * i + 0.3, size=26,
              color=ORANGE if it["tok"] == dung else INK2, hand=False, **kw)
    return out


def ve_xac_suat(ctx, s, spec):
    B = ctx.B
    t0 = ctx.t(spec, noi="xac_suat") if spec.get("at") else ctx.bat_dau + 0.3
    dung = spec["dung"]
    items = spec["items"]
    sau = spec.get("sau")
    t_sau = ctx.t({"at": sau["at"]}, noi="xac_suat.sau") if sau and sau.get("at") else None
    B.txt(s, "xsTr", f"… {spec.get('truoc', '')} ▢", 670, 230, t0, size=44, color=INK, hand=False)
    x0, w, day = 260, 820, 820
    bw = w / len(items)
    for i, it in enumerate(items):
        B.txt(s, f"xsTok{i}", it["tok"], x0 + bw * (i + 0.5), day + 40, t0 + 0.08 * i, size=28,
              color=ORANGE if it["tok"] == dung else INK, hand=False)
    _cot_xac_suat(ctx, s, "xsA", items, dung, t0 + 0.3, ra=round(t_sau - 0.05, 2) if t_sau else None)
    p0 = next(it["p"] for it in items if it["tok"] == dung)
    B.txt(s, "xsLt", "loss = −ln p(chữ đúng)", 1460, 330, t0 + 0.9, size=40, color=INK, hand=False)
    B.counter(s, "xsL", 1460, 470, t0 + 1.2, round(-math.log(p0), 2), size=110, color=RED, dur=0.6, decimals=2,
              **({"exitAt": round(t_sau - 0.05, 2), "exit": "fade"} if t_sau else {}))
    B.txt(s, "xsLp", f"p = {_vn(p0, 2)}", 1460, 580, t0 + 1.2, size=34, color=INK2, hand=False,
          **({"exitAt": round(t_sau - 0.05, 2), "exit": "fade"} if t_sau else {}))
    if sau:
        _cot_xac_suat(ctx, s, "xsB", sau["items"], dung, t_sau)
        p1 = next(it["p"] for it in sau["items"] if it["tok"] == dung)
        B.counter(s, "xsL2", 1460, 470, t_sau, round(-math.log(p1), 2), size=110, color=XANH_LA, dur=0.8, decimals=2,
                  **{"from": round(-math.log(p0), 2)})
        B.txt(s, "xsLp2", f"p = {_vn(p1, 2)} sau huấn luyện", 1460, 580, t_sau + 0.2, size=34, color=XANH_LA, hand=False)


def ve_ham_log(ctx, s, spec):
    """Đồ thị y = −ln p thật (p từ 0,05 tới 1), chấm chạy từ p0 tới p1."""
    B = ctx.B
    t0 = ctx.t(spec, noi="ham_log") if spec.get("at") else ctx.bat_dau + 0.3
    L, R, T, D = 1180, 1760, 640, 960         # khung đồ thị góc phải dưới
    ymax = -math.log(0.05)

    def xy(p):
        return (round(L + (p - 0.05) / 0.95 * (R - L), 1), round(D - (-math.log(p)) / ymax * (D - T), 1))
    B.line(s, "hlT", [(L, T - 10), (L, D), (R + 10, D)], t0, color=INK, width=3, arrow=False, dur=0.4)
    B.txt(s, "hlY", "loss", L - 10, T - 30, t0 + 0.2, size=24, color=INK2, hand=False, align="right")
    B.txt(s, "hlX", "p của chữ đúng → 1", R, D + 32, t0 + 0.2, size=24, color=INK2, hand=False, align="right")
    pts = [xy(0.05 + 0.95 * k / 60) for k in range(61)]
    s.add({"id": "hlD", "type": "path", "d": "M " + " L ".join(f"{x},{y}" for x, y in pts), "stroke": BLUE,
           "strokeWidth": 5, "fill": None, "arrow": False, "enterAt": round(t0 + 0.4, 2), "enter": "draw",
           "enterDuration": 0.9, "hand": False, "rough": False})
    p0, p1 = float(spec.get("p0", 0.2)), float(spec.get("p1", 0.9))
    x0, y0 = xy(p0)
    tc = ctx.t({"at": spec["chay_at"]}, noi="ham_log.chay") if spec.get("chay_at") else t0 + 2.0
    buoc = [{"at": round(tc + 0.08 * k, 3), "x": xy(p0 + (p1 - p0) * k / 12)[0], "y": xy(p0 + (p1 - p0) * k / 12)[1],
             "duration": 0.08} for k in range(1, 13)]
    B.circle(s, "hlP", "", x0, y0, 12, t0 + 1.3, fill=ORANGE, stroke=None, enter="pop", dur=0.25, moves=buoc)


# ── Bản đồ tiến hoá fine-tuning: hai trục độc lập, vẽ dần qua từng chương ────────────────────────────────
BD_Y = [("full", "Sửa tất cả", None), ("lora", "LoRA · < 1%", "quá tốn bộ nhớ"), ("qlora", "QLoRA · 4-bit", "model gốc vẫn nặng")]
BD_X = [("sft", "Đáp án mẫu · SFT", None), ("rlhf", "So sánh · RLHF", "không có đáp án duy nhất"),
        ("dpo", "So sánh · DPO", "bốn model, dễ vỡ"), ("kto", "Nút thích · KTO", "không có cặp so sánh"),
        ("grpo", "Bộ chấm · GRPO", "có bộ chấm tự động")]


def ve_ban_do(ctx, s, spec):
    """{hien: [khoá đã giới thiệu], moi: khoá mới (sáng + mũi tên từ khoá trước), at, to_hop: [[x, y], …], to_hop_at}.
    Trục dọc (trái): sửa bao nhiêu con số, từ trên xuống. Trục ngang (dưới): học từ tín hiệu gì, trái sang phải."""
    B = ctx.B
    t0 = ctx.t(spec, noi="ban_do") if spec.get("at") else ctx.bat_dau + 0.2
    _m = spec.get("moi")
    hien = set(spec.get("hien", [])) | (set(_m) if isinstance(_m, list) else ({_m} if _m else set()))
    O = (420, 880)                                  # góc: trục dọc x=420, trục ngang y=880
    ys = {k: 300 + 220 * i for i, (k, _, _) in enumerate(BD_Y)}
    xs = {k: 640 + 270 * i for i, (k, _, _) in enumerate(BD_X)}
    B.line(s, "bdY", [(O[0], O[1]), (O[0], 220)], t0, color=INK, width=4, arrow=True, dur=0.5)
    B.line(s, "bdX", [(O[0], O[1]), (1880, O[1])], t0, color=INK, width=4, arrow=True, dur=0.5)
    B.txt(s, "bdYt", "sửa bao nhiêu con số", O[0] + 20, 200, t0 + 0.2, size=28, color=INK2, hand=False, align="left")
    B.txt(s, "bdXt", "học từ tín hiệu gì →", 1880, O[1] + 95, t0 + 0.2, size=28, color=INK2, hand=False, align="right")
    moi = spec.get("moi")
    moi_set = set(moi) if isinstance(moi, list) else ({moi} if moi else set())
    tm = ctx.t({"at": spec["moi_at"]}, noi="ban_do.moi") if spec.get("moi_at") else t0 + 0.6

    def diem(id_, x, y, nhan, la_moi, truoc, ly_do, ngang):
        col = ORANGE if la_moi else INK
        t = tm if la_moi else t0 + 0.4
        B.circle(s, f"bd{id_}", "", x, y, 16 if la_moi else 11, t, fill=col if la_moi else "#FFFFFF", stroke=col,
                 enter="pop", dur=0.3)
        if ngang:
            B.txt(s, f"bd{id_}t", nhan, x, y + 44, t + 0.1, size=28 if la_moi else 24, color=col, hand=False,
                  maxWidth=250, weight=800 if la_moi else 600)
        else:
            B.txt(s, f"bd{id_}t", nhan, x - 30, y, t + 0.1, size=28 if la_moi else 24, color=col, hand=False,
                  align="right", weight=800 if la_moi else 600)
        if la_moi and truoc:
            px, py = truoc
            if ngang:
                B.line(s, f"bd{id_}a", [(px + 22, py), (x - 26, y)], tm + 0.2, color=ORANGE, width=4, arrow=True, dur=0.4)
                B.txt(s, f"bd{id_}l", ly_do, (px + x) / 2, y - 34, tm + 0.4, size=22, color=RED, hand=False, maxWidth=250)
            else:
                B.line(s, f"bd{id_}a", [(px, py + 22), (x, y - 26)], tm + 0.2, color=ORANGE, width=4, arrow=True, dur=0.4)
                B.txt(s, f"bd{id_}l", ly_do, x + 24, (py + y) / 2, tm + 0.4, size=22, color=RED, hand=False, align="left",
                      maxWidth=280)

    truoc = None
    for k, nhan, ly_do in BD_Y:
        if k in hien:
            diem(k, O[0], ys[k], nhan, k in moi_set, truoc, ly_do, False)
        truoc = (O[0], ys[k]) if k in hien else truoc
    truoc = None
    for k, nhan, ly_do in BD_X:
        if k in hien:
            diem(k, xs[k], O[1], nhan, k in moi_set, truoc, ly_do, True)
        truoc = (xs[k], O[1]) if k in hien else truoc
    if spec.get("chuoi"):                     # nhìn lại: hiện cả chuỗi "kỹ thuật sau vá chỗ hỏng nào của kỹ thuật trước"
        tc = ctx.t({"at": spec["chuoi_at"]}, noi="ban_do.chuoi") if spec.get("chuoi_at") else t0 + 0.8
        i = 0
        for truc, ds in (("y", BD_Y), ("x", BD_X)):
            for (k0, _, _), (k1, _, ly_do) in zip(ds, ds[1:]):
                if k0 in hien and k1 in hien and k1 not in moi_set:
                    ti = tc + 0.35 * i
                    i += 1
                    if truc == "y":
                        B.line(s, f"bdc{k1}", [(O[0], ys[k0] + 18), (O[0], ys[k1] - 18)], ti, color=ORANGE, width=4,
                               arrow=True, dur=0.3)
                        B.txt(s, f"bdc{k1}t", ly_do, O[0] + 24, (ys[k0] + ys[k1]) / 2, ti + 0.1, size=22, color=RED,
                              hand=False, align="left", maxWidth=280)
                    else:
                        B.line(s, f"bdc{k1}", [(xs[k0] + 18, O[1]), (xs[k1] - 18, O[1])], ti, color=ORANGE, width=4,
                               arrow=True, dur=0.3)
                        B.txt(s, f"bdc{k1}t", ly_do, (xs[k0] + xs[k1]) / 2, O[1] - 34, ti + 0.1, size=22, color=RED,
                              hand=False, maxWidth=250)
    th = spec.get("to_hop") or []
    if th:
        tt = ctx.t({"at": spec["to_hop_at"]}, noi="ban_do.to_hop") if spec.get("to_hop_at") else tm + 1.0
        for i, (kx, ky) in enumerate(th):
            x, y = xs[kx], ys[ky]
            ti = tt + 0.8 * i
            B.line(s, f"bdh{i}a", [(x, O[1] - 20), (x, y)], ti, color=BLUE, width=3, arrow=False, dur=0.4, dashed=True)
            B.line(s, f"bdh{i}b", [(O[0] + 20, y), (x, y)], ti, color=BLUE, width=3, arrow=False, dur=0.4, dashed=True)
            ny = dict((k, n) for k, n, _ in BD_Y)[ky].split(" ·")[0]
            nx = dict((k, n) for k, n, _ in BD_X)[kx].split("· ")[-1]
            B.circle(s, f"bdh{i}c", "", x, y, 18, ti + 0.4, fill=BLUE, stroke=BLUE, enter="pop", dur=0.3)
            B.txt(s, f"bdh{i}t", f"{ny} × {nx}", x, y - 44, ti + 0.5, size=30, color=BLUE, hand=False, weight=800)


# ── Bảng số của model, lượng tử hoá, DPO, bộ nhớ bốn model (23/10/2026) ──────────────────────────────────────
def ve_bang_so(ctx, s, spec):
    """Model là một bảng số. {hang: 5, cot: 8, at, tong: 8000000000, nhich_at: "cụm chữ"}.
    Số sinh từ hạt cố định (không gõ tay); lúc `nhich_at`, ~1/3 ô đổi giá trị một chút (số cũ tắt, số mới màu cam)."""
    import random
    B = ctx.B
    h, c = int(spec.get("hang", 5)), int(spec.get("cot", 8))
    rnd = random.Random(spec.get("hat", 11))
    t0 = ctx.t(spec, noi="bang_so") if spec.get("at") else ctx.bat_dau + 0.2
    dx, dy, x0, y0 = 190, 105, 960 - 190 * (c - 1) / 2, 560 - 105 * (h - 1) / 2
    tn = ctx.t({"at": spec["nhich_at"]}, noi="bang_so.nhich") if spec.get("nhich_at") else None
    for i in range(h):
        for j in range(c):
            v = round(rnd.uniform(-1, 1), 2)
            x, y = x0 + dx * j, y0 + dy * i
            ti = t0 + 0.02 * (i * c + j)
            doi = tn is not None and rnd.random() < 0.35
            kw = {"exitAt": round(tn - 0.02, 2), "exit": "fade", "exitDuration": 0.15} if doi else {}
            B.txt(s, f"bs{i}_{j}", _vn(v, 2), x, y, ti, size=40, color=INK2, hand=False, enter="pop", dur=0.2, **kw)
            if doi:
                moi = round(v + rnd.choice([-1, 1]) * rnd.uniform(0.02, 0.09), 2)
                B.txt(s, f"bs{i}_{j}n", _vn(moi, 2), x, y, tn, size=40, color=ORANGE, weight=800, hand=False,
                      enter="pop", dur=0.25)
    if spec.get("tong"):
        tg = ctx.t({"at": spec["tong_at"]}, noi="bang_so.tong") if spec.get("tong_at") else t0 + 0.8
        B.counter(s, "bsT", 960, 930, tg, int(spec["tong"]), size=70, color=INK, dur=1.4, suffix=" con số")
    B.txt(s, "bsG", "ví dụ minh hoạ, không phải trọng số thật", 960, 1010, t0 + 0.4, size=22, color=INK2, hand=False)


def ve_luong_tu_hoa(ctx, s, spec):
    """QLoRA: 40 con số thực trên một trục, rồi mỗi số bị kéo về vạch gần nhất trong 2^bits vạch.
    {bits: 4, at, keo_at}. Số mức = 2**bits (tự tính)."""
    import random
    B = ctx.B
    bits = int(spec.get("bits", 4))
    n_vach = 2 ** bits
    t0 = ctx.t(spec, noi="luong_tu_hoa") if spec.get("at") else ctx.bat_dau + 0.2
    L, R, Y = 280, 1640, 640
    vach = [L + (R - L) * k / (n_vach - 1) for k in range(n_vach)]
    B.line(s, "ltT", [(L - 30, Y), (R + 30, Y)], t0, color=INK, width=4, arrow=False, dur=0.5)
    for k, x in enumerate(vach):
        B.line(s, f"ltV{k}", [(x, Y - 40), (x, Y + 40)], t0 + 0.3 + 0.03 * k, color=BLUE, width=3, arrow=False, dur=0.2)
    B.txt(s, "ltN", f"{n_vach} mức" if bits < 8 else f"{n_vach} mức", 960, Y + 120, t0 + 0.8, size=60, color=BLUE,
          hand=False, enter="pop", dur=0.3)
    B.txt(s, "ltF", f"2^{bits} = {_vn(n_vach)}  ·  16 bit sẽ có 2^16 = {_vn(2 ** 16)} mức", 960, Y + 190, t0 + 1.0, size=32,
          color=INK2, hand=False)
    rnd = random.Random(spec.get("hat", 5))
    tk = ctx.t({"at": spec["keo_at"]}, noi="luong_tu_hoa.keo") if spec.get("keo_at") else t0 + 3.0
    for i in range(40):
        x = rnd.uniform(L, R)
        y = Y - 70 - rnd.uniform(0, 150)
        gan = min(vach, key=lambda v: abs(v - x))
        B.circle(s, f"ltD{i}", "", round(x, 1), round(y, 1), 9, t0 + 1.2 + 0.03 * i, fill=ORANGE, stroke=None,
                 enter="pop", dur=0.2, moves=[{"at": round(tk + 0.01 * i, 3), "x": round(gan, 1), "y": Y - 18 - (i % 3) * 20,
                                              "duration": 0.7}])
    B.txt(s, "ltS", "mỗi con số bị làm tròn về vạch gần nhất → có sai số nhỏ", 960, 350, tk, size=34, color=INK, hand=False,
          enter="pop", dur=0.3)


def ve_cap_dpo(ctx, s, spec):
    """DPO: hai cột xác suất log (so với bản gốc): câu được chọn đẩy lên, câu bị loại đẩy xuống, đếm khoảng cách.
    {at, tach_at, dich: 1.2}."""
    B = ctx.B
    t0 = ctx.t(spec, noi="cap_dpo") if spec.get("at") else ctx.bat_dau + 0.2
    tt = ctx.t({"at": spec["tach_at"]}, noi="cap_dpo.tach") if spec.get("tach_at") else t0 + 2.0
    k = 190                                   # px mỗi đơn vị
    dich = float(spec.get("dich", 1.2))
    Y0 = 600
    B.line(s, "dpR", [(300, Y0), (1620, Y0)], t0, color=INK, width=4, arrow=False, dur=0.5, dashed=True)
    B.txt(s, "dpRt", "bản gốc (mốc so sánh)", 1620, Y0 + 40, t0 + 0.2, size=28, color=INK2, hand=False, align="right")
    for nhan, x, col in (("câu được chọn", 700, XANH_LA), ("câu bị loại", 1220, RED)):
        B.txt(s, f"dpL{x}", nhan, x, 280, t0 + 0.3, size=36, color=col, hand=False)
        B.box(s, f"dp0{x}", "", x, Y0, 150, 18, t0 + 0.4, fill=col, stroke=None, hand=False, enter="grow", dur=0.3,
              radius=3, exitAt=round(tt - 0.02, 2), exit="fade", exitDuration=0.1)
    h = dich * k
    B.box(s, "dpC", "", 700, Y0 - h / 2, 150, h, tt, fill=XANH_LA, stroke=None, hand=False, enter="grow", dur=0.8, radius=4)
    B.box(s, "dpJ", "", 1220, Y0 + h / 2, 150, h, tt, fill=RED, stroke=None, hand=False, enter="grow", dur=0.8, radius=4)
    B.txt(s, "dpCt", f"+{_vn(dich, 1)}", 700, Y0 - h - 36, tt + 0.5, size=40, color=XANH_LA, hand=False)
    B.txt(s, "dpJt", f"−{_vn(dich, 1)}", 1220, Y0 + h + 40, tt + 0.5, size=40, color=RED, hand=False)
    B.line(s, "dpG", [(960, Y0 - h), (960, Y0 + h)], tt + 0.8, color=ORANGE, width=5, arrow=True, dur=0.5)
    B.txt(s, "dpGt", "khoảng cách", 990, Y0 - 90, tt + 1.0, size=28, color=ORANGE, hand=False, align="left")
    B.counter(s, "dpK", 960, 880, tt + 1.0, round(2 * dich, 1), size=80, color=ORANGE, dur=0.9, decimals=1)
    B.txt(s, "dpKt", "DPO chỉ làm một việc: nới rộng khoảng cách này", 960, 960, tt + 1.2, size=32, color=INK2, hand=False)


BM = {"hoc": ("model đang học", 520, 360, ORANGE), "goc": ("bản gốc (mốc)", 1400, 360, INK2),
      "cham": ("model chấm điểm", 520, 700, BLUE), "gia": ("model ước lượng giá trị", 1400, 700, BLUE)}


def ve_bon_model(ctx, s, spec):
    """Bộ nhớ của RLHF: 4 model; `gach: [{k, at}]` gạch bỏ; `thay: {k, text, at}` thay bằng một đoạn code.
    Bộ đếm "N model trong bộ nhớ" tự đổi theo."""
    B = ctx.B
    t0 = ctx.t(spec, noi="bon_model") if spec.get("at") else ctx.bat_dau + 0.2
    gach = {g["k"]: ctx.t({"at": g["at"]}, noi=f"bon_model.gach.{g['k']}") for g in spec.get("gach", [])}
    thay = spec.get("thay")
    tt = ctx.t({"at": thay["at"]}, noi="bon_model.thay") if thay else None
    for i, (k, (ten, x, y, col)) in enumerate(BM.items()):
        ti = t0 + 0.3 * i
        B.box(s, f"bm{k}", ten, x, y, 520, 150, ti, fill="#FFFFFF", stroke=col, label_color=INK, size=34, hand=False,
              enter="pop", dur=0.3)
        if k in gach:
            B.strike(s, f"bm{k}x", x, y, 500, gach[k])
        if thay and thay["k"] == k:
            B.box(s, f"bm{k}n", thay["text"], x, y, 520, 150, tt, fill="#F3F4F6", stroke=XANH_LA, label_color=INK, size=30,
                  hand=False, enter="pop", dur=0.35, z=5)
    # bộ đếm: tắt/bật theo mốc
    t_dem = ctx.t({"at": spec["dem_at"]}, noi="bon_model.dem") if spec.get("dem_at") else t0 + 1.4
    bot = list(gach.values()) + ([tt] if tt is not None else [])     # mỗi lần gạch / thay là bớt một model
    mocs = sorted(set([t_dem] + bot))
    for i, tm in enumerate(mocs):
        con = 4 - sum(1 for g in bot if g <= tm + 0.01)
        ra = {"exitAt": round(mocs[i + 1] - 0.02, 2), "exit": "fade", "exitDuration": 0.1} if i + 1 < len(mocs) else {}
        B.txt(s, f"bmN{i}", f"{con} model trong bộ nhớ" if con > 0 else "", 960, 940, tm, size=54, color=RED if con >= 4 else INK,
              hand=False, enter="pop", dur=0.25, **ra)
