"""Overview figure for the README, in the style of a paper's Figure 1 (panels, numbered stages, small charts).

Run:  python3 docs/make_figure.py      →  docs/figure_overview.{svg,png}
Hand-written SVG (no plotting library); PNG exported with headless Chrome.
Every number in the charts is a measured value from the channel's private pipeline (sources in NUMBERS below).
"""
import os, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1800, 1020
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
C = {"am": "#f3dfb0", "am_nen": "#fffaf0", "vien": "#d9b45e", "chu": "#1f2937", "mo": "#6b7280",
     "xanh": "#3b6fb6", "xanh_nen": "#e8f0fb", "cam": "#c26b12", "cam_nen": "#fdf0e2", "la": "#2f8a4c", "la_nen": "#e9f5ec",
     "tim": "#6b4aa8", "tim_nen": "#f1ecf8", "do": "#c0392b", "xam": "#9ca3af"}

# Measured numbers (channel "Đi Làm IT", private pipeline repo, 10/10–07/11/2026)
NUMBERS = {
    # first released version of each long episode, images + voice (USD); Carbon/Benchmark images from the asset log
    "cost": [("Jev", 2.28), ("2nd brain", 1.74), ("4 futures", 1.49), ("Claude", 1.02), ("PHP2Shell", 1.09),
             ("Weekly #2", 0.49), ("Carbon", 0.79), ("Benchmark", 0.46)],
    # GMO episode: v1 measured 31 stretches > 3.5 s with no new visual (longest 19.9 s); v2 built with the blocking check
    "gaps": [("v1, before\nthe check", 31), ("v2, check\nblocks render", 0)],
    # Weekly #2: seconds of near-blank screen (>= 1.5 s), v2 → v3
    "blank": [("v2", 61), ("v3", 7)],
    # Terminal-Bench task heterogeneous-dates, run locally with Docker
    "tb": [("reference\nsolution", 1, 1), ("GPT-4o\nmini", 0, 3), ("GPT-5.6\nLuna", 3, 3)],
}


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def chu(x, y, t, co=16, mau=None, dam=False, neo="start", nghieng=False, mono=False):
    st = ' font-style="italic"' if nghieng else ""
    ff = ' font-family="Menlo, Consolas, monospace"' if mono else ""
    fw = ' font-weight="700"' if dam else ""
    fw += ' xml:space="preserve"' if mono else ""
    return (f'<text x="{x}" y="{y}" font-size="{co}" fill="{mau or C["chu"]}" text-anchor="{neo}"'
            f'{fw}{st}{ff}>{esc(t)}</text>')


def nhieu(x, y, dong, co=16, gian=None, **kw):
    gian = gian or co * 1.3
    return "".join(chu(x, y + i * gian, d, co, **kw) for i, d in enumerate(dong))


def the(x, y, w, h, nen, vien, rx=14, day=1.6, dut=False):
    d = ' stroke-dasharray="7 5"' if dut else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{nen}" stroke="{vien}" stroke-width="{day}"{d}/>'


def mui(x1, y1, x2, y2, mau="#4b5563", day=2.4, dut=False):
    d = ' stroke-dasharray="6 5"' if dut else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{mau}" stroke-width="{day}"{d} '
            f'marker-end="url(#m-{mau[1:]})"/>')


def cot(x, y, w, h, items, mau, ymax, fmt="{:g}", nhan_co=13, xoay=False):
    """Bar chart: items = [(label, value)], bars bottom-aligned at y+h."""
    p, n = [], len(items)
    bw = w / n * 0.62
    p.append(f'<line x1="{x}" y1="{y + h}" x2="{x + w}" y2="{y + h}" stroke="#cbd5e1" stroke-width="1.4"/>')
    for i, (lab, v) in enumerate(items):
        cx = x + w / n * (i + 0.5)
        bh = max(2, h * v / ymax)
        col = mau[i] if isinstance(mau, list) else mau
        p.append(f'<rect x="{cx - bw / 2}" y="{y + h - bh}" width="{bw}" height="{bh}" rx="3" fill="{col}"/>')
        p.append(chu(cx, y + h - bh - 7, fmt.format(v), 14, dam=True, neo="middle"))
        if xoay:
            p.append(f'<g transform="rotate(-38 {cx + 4} {y + h + 12})">'
                     + chu(cx + 4, y + h + 16, lab, nhan_co, mau=C["mo"], neo="end") + "</g>")
            continue
        for k, dong in enumerate(lab.split("\n")):
            p.append(chu(cx, y + h + 18 + k * 15, dong, nhan_co, mau=C["mo"], neo="middle"))
    return "".join(p)


def o_kq(x, y, w, h, tieu, ghi, ve):
    return (the(x, y, w, h, "#fff", "#c9b7e6", rx=12) + chu(x + 16, y + 30, tieu, 17, mau=C["tim"], dam=True)
            + ve + f'<rect x="{x + 10}" y="{y + h - 52}" width="{w - 20}" height="42" rx="8" fill="{C["tim_nen"]}"/>'
            + chu(x + w / 2, y + h - 25, ghi, 15, dam=True, neo="middle"))


def nguoi_noi(x, y, s=1.0):
    """Narrator icon (head + shoulders + speech wave)."""
    return (f'<circle cx="{x}" cy="{y}" r="{14 * s}" fill="{C["xanh_nen"]}" stroke="{C["xanh"]}" stroke-width="2.2"/>'
            f'<path d="M{x - 24 * s} {y + 38 * s} q{24 * s} -34 {48 * s} 0" fill="{C["xanh_nen"]}" stroke="{C["xanh"]}" stroke-width="2.2"/>'
            + "".join(f'<path d="M{x + 24 * s + k * 9} {y - 10} q8 10 0 20" fill="none" stroke="{C["xanh"]}" stroke-width="2"/>'
                      for k in range(3)))


def man_hinh(x, y, w=150, h=96):
    """Laptop with a hand-drawn chart on screen."""
    return (the(x, y, w, h, "#fff", C["chu"], rx=8, day=2)
            + f'<rect x="{x - 12}" y="{y + h}" width="{w + 24}" height="10" rx="4" fill="{C["chu"]}"/>'
            + f'<path d="M{x + 18} {y + h - 18} l28 -26 l24 14 l34 -40" fill="none" stroke="{C["cam"]}" stroke-width="3"/>'
            + f'<rect x="{x + 18}" y="{y + 14}" width="54" height="8" rx="3" fill="{C["xanh"]}"/>')


def ve():
    p = []
    defs = "".join(f'<marker id="m-{m[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                   f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{m}"/></marker>'
                   for m in ("#4b5563", C["cam"], C["la"], C["tim"], C["xanh"]))

    # ── left: the idea ─────────────────────────────────────────────────────
    L, Lw = 16, 600
    p.append(the(L, 14, Lw, H - 28, C["am_nen"], C["vien"], rx=22, day=2))
    p.append(f'<path d="M{L} 58 v-22 a22 22 0 0 1 22 -22 h{Lw - 44} a22 22 0 0 1 22 22 v22 z" fill="{C["am"]}"/>')
    p.append(chu(L + Lw / 2, 46, "The idea: no timestamps", 25, dam=True, neo="middle"))

    # a) narration with word timings
    p.append(the(L + 18, 76, Lw - 36, 250, "#fff", "#ead7a8"))
    p.append(chu(L + Lw / 2, 106, "Narration → word timings", 19, dam=True, neo="middle"))
    p.append(nguoi_noi(L + 70, 160))
    words = [("Câu", 134.9), ("kiểm", 135.2), ("thứ", 135.5), ("nhất", 135.7), ("qua", 136.0)]
    x0 = L + 150
    for i, (w_, t) in enumerate(words):
        xx = x0 + i * 78
        p.append(f'<rect x="{xx}" y="{142}" width="70" height="30" rx="6" fill="{C["xanh_nen"]}" stroke="{C["xanh"]}"/>')
        p.append(chu(xx + 35, 163, w_, 15, mau=C["xanh"], dam=True, neo="middle"))
        p.append(chu(xx + 35, 192, f"{t:.1f}s", 12, mau=C["mo"], neo="middle"))
    # waveform
    import math
    wave = " ".join(f"L{L + 60 + k * 4.4} {262 + 22 * math.sin(k * 0.55) * abs(math.sin(k * 0.13))}" for k in range(115))
    p.append(f'<path d="M{L + 60} 262 {wave}" fill="none" stroke="{C["xanh"]}" stroke-width="1.6" opacity="0.7"/>')
    p.append(chu(L + Lw / 2, 312, "TTS voice + forced alignment (word start/end)", 14, mau=C["mo"], neo="middle"))

    # b) storyboard YAML
    p.append(mui(L + Lw / 2, 330, L + Lw / 2, 356, C["cam"]))
    p.append(the(L + 18, 360, Lw - 36, 250, "#fff", "#ead7a8"))
    p.append(chu(L + Lw / 2, 390, "Storyboard YAML: anchor to a phrase", 19, dam=True, neo="middle"))
    p.append(f'<rect x="{L + 40}" y="406" width="{Lw - 80}" height="150" rx="8" fill="#1f2937"/>')
    code = [("- id: s10", "#e5e7eb"), ("  para: p10", "#9ca3af"),
            ('  nhan: {items: [', "#e5e7eb"), ('    "✓ có file @ Câu kiểm thứ nhất qua",', "#86efac"),
            ('    "✗ câu thứ ba hỏng @ Câu thứ ba hỏng"]}', "#fca5a5")]
    for i, (ln, col) in enumerate(code):
        p.append(chu(L + 56, 432 + i * 25, ln, 14.5, mau=col, mono=True))
    p.append(chu(L + Lw / 2, 590, "“@ phrase” → seconds, looked up in the word timings", 14, mau=C["mo"], neo="middle"))

    # c) why
    p.append(mui(L + Lw / 2, 614, L + Lw / 2, 640, C["cam"]))
    p.append(the(L + 18, 644, Lw - 36, 340, "#fff", "#ead7a8"))
    p.append(chu(L + Lw / 2, 674, "Why it matters", 19, dam=True, neo="middle"))
    p.append(man_hinh(L + 70, 706))
    p.append(nhieu(L + 260, 724, ["every label appears exactly", "when the narrator says it"], 16))
    p.append(nhieu(L + 260, 792, ["re-record the voice,", "the edit does not break"], 16))
    p.append(the(L + 40, 860, Lw - 80, 100, C["tim_nen"], C["tim"], rx=12, dut=True))
    p.append(chu(L + 60, 892, "?", 34, mau=C["tim"], dam=True))
    p.append(nhieu(L + 96, 893, ["Can a solo developer ship weekly explainer", "videos that stay accurate and never look static?"],
                   16, mau=C["tim"], dam=True))

    # ── right: pipeline & results ─────────────────────────────────────────
    R, Rw = 632, W - 632 - 16
    p.append(the(R, 14, Rw, H - 28, C["am_nen"], C["vien"], rx=22, day=2))
    p.append(f'<path d="M{R} 58 v-22 a22 22 0 0 1 22 -22 h{Rw - 44} a22 22 0 0 1 22 22 v22 z" fill="{C["am"]}"/>')
    p.append(chu(R + Rw / 2, 46, "Pipeline & measured results", 25, dam=True, neo="middle"))

    stages = [("①", "Sources", "crawl + fact table", C["xanh"], C["xanh_nen"]),
              ("②", "Script", "human approval", C["xanh"], C["xanh_nen"]),
              ("③", "Voice", "TTS + alignment", C["xanh"], C["xanh_nen"]),
              ("④", "Storyboard", "YAML blocks", C["cam"], C["cam_nen"])]
    sx, sw, sg = R + 22, 196, 26
    for i, (n, t, s, col, nen) in enumerate(stages):
        x = sx + i * (sw + sg)
        p.append(the(x, 80, sw, 86, nen, col, rx=12))
        p.append(chu(x + 14, 112, f"{n} {t}", 18, mau=col, dam=True))
        p.append(chu(x + 14, 140, s, 14, mau=C["mo"]))
        if i < 3:
            p.append(mui(x + sw + 2, 123, x + sw + sg - 2, 123))
    # ⑤ engine (this repo)
    ex, ey, ew, eh = R + 22, 196, Rw - 44, 284
    p.append(mui(sx + 3 * (sw + sg) + sw / 2, 168, sx + 3 * (sw + sg) + sw / 2, ey - 4, C["la"]))
    p.append(the(ex, ey, ew, eh, C["la_nen"], C["la"], rx=14, day=2.2, dut=True))
    p.append(chu(ex + 18, ey + 34, "⑤ Engine — this repository", 21, mau=C["la"], dam=True))
    sub = [("anchor", "phrase → seconds", "engine/khuon/moc.py"), ("layout", "~30 blocks, no coordinates", "khoi.py · bo_cuc.py"),
           ("check", "blocks the render", "kiem_tra.py"), ("render", "React + Remotion", "studio/")]
    bw_, bg_ = 236, 22
    for i, (t, s, f) in enumerate(sub):
        x = ex + 18 + i * (bw_ + bg_)
        col = C["do"] if t == "check" else C["la"]
        p.append(the(x, ey + 54, bw_, 92, "#fff", col, rx=10, day=1.8))
        p.append(chu(x + bw_ / 2, ey + 84, t, 18, mau=col, dam=True, neo="middle"))
        p.append(chu(x + bw_ / 2, ey + 108, s, 14, neo="middle"))
        p.append(chu(x + bw_ / 2, ey + 130, f, 12, mau=C["mo"], neo="middle", mono=True))
        if i < 3:
            p.append(mui(x + bw_ + 2, ey + 100, x + bw_ + bg_ - 2, ey + 100, C["la"]))
    checks = ["no new visual for > 4 s while the narrator talks", "text overlapping text or images",
              "a number on screen the narrator never says", "a #color tag YAML would silently drop"]
    p.append(chu(ex + 18, ey + 180, "Render is blocked when:", 16, mau=C["do"], dam=True))
    for i, c_ in enumerate(checks):
        cx_, cy_ = ex + 18 + (i % 2) * 520, ey + 212 + (i // 2) * 34
        p.append(f'<circle cx="{cx_ + 9}" cy="{cy_ - 5}" r="9" fill="#fdecea" stroke="{C["do"]}" stroke-width="1.6"/>')
        p.append(chu(cx_ + 9, cy_ - 0.5, "✕", 12, mau=C["do"], dam=True, neo="middle"))
        p.append(chu(cx_ + 26, cy_, c_, 15))
    p.append(chu(ex + ew - 18, ey + 34, "⑥ QA → YouTube API → analytics", 16, mau=C["mo"], neo="end"))

    # results row
    ry, rh = 504, 492
    rw = (Rw - 44 - 3 * 18) / 4
    p.append(the(R + 12, ry - 8, Rw - 24, rh + 8, "#fbf8ff", "#b8a3e0", rx=16, day=1.6))
    p.append(chu(R + Rw / 2, ry + 22, "Measured on the channel Đi Làm IT (10/10–07/11/2026)", 18, mau=C["tim"], dam=True, neo="middle"))
    xs = [R + 22 + i * (rw + 18) for i in range(4)]
    top = ry + 40
    hh = rh - 60
    cost = NUMBERS["cost"]
    p.append(o_kq(xs[0], top, rw, hh, "Cost per long video (USD)", "Oldest → newest: 2.28 → 0.46",
                  cot(xs[0] + 14, top + 60, rw - 28, hh - 210, cost,
                      [C["xam"]] * 5 + [C["la"]] * 3, 2.5, "{:.2f}", nhan_co=12, xoay=True)))
    p.append(o_kq(xs[1], top, rw, hh, "Static stretches > 3.5 s", "The 4 s check removes them",
                  cot(xs[1] + 30, top + 70, rw - 60, hh - 190, NUMBERS["gaps"], [C["do"], C["la"]], 35, "{:d}")
                  + chu(xs[1] + rw / 2, top + hh - 64, "GMO episode · v1 longest: 19.9 s", 12, mau=C["mo"], neo="middle")))
    p.append(o_kq(xs[2], top, rw, hh, "Near-blank screen time (s)", "From 61 s to 7 s",
                  cot(xs[2] + 50, top + 70, rw - 100, hh - 190, [(f"Weekly #2\n{l}", v) for l, v in NUMBERS["blank"]],
                      [C["do"], C["la"]], 70, "{:d}")))
    tb = NUMBERS["tb"]
    p.append(o_kq(xs[3], top, rw, hh, "Real Terminal-Bench run", "Demo footage is real",
                  cot(xs[3] + 14, top + 70, rw - 28, hh - 190, [(l, ok / n) for l, ok, n in tb],
                      [C["xam"], C["do"], C["la"]], 1.15, "{:.0%}")
                  + chu(xs[3] + rw / 2, top + hh - 64, "passed / runs: 1/1 · 0/3 · 3/3", 12, mau=C["mo"], neo="middle")))

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">'
            f'<defs>{defs}</defs><rect width="{W}" height="{H}" fill="#fff"/>' + "\n".join(p) + "</svg>")


def xuat(svg):
    html = svg[:-4] + ".html"
    open(html, "w", encoding="utf-8").write(f"<!doctype html><html><head><meta charset='utf-8'><style>body{{margin:0}}</style>"
                                            f"</head><body>{open(svg, encoding='utf-8').read()}</body></html>")
    chrome = shutil.which("google-chrome") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{H}",
                    "--force-device-scale-factor=2", f"--screenshot={svg[:-4]}.png", html], check=True, capture_output=True)
    os.remove(html)


if __name__ == "__main__":
    out = os.path.join(HERE, "figure_overview.svg")
    open(out, "w", encoding="utf-8").write(ve())
    xuat(out)
    print("→", out, "+ .png")
