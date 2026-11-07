"""Thư viện dựng timeline kiểu C (bảng trắng vẽ tay) cho Remotion studio.

Mỗi video viết một file trong pipeline/videos/ dùng các hàm ở đây. Hình gắn vào CHỮ trong lời thoại
(words.json), nên đổi giọng thì hình tự khớp lại.
"""
import json, os, unicodedata

INK, INK2, ORANGE, GREEN, RED, BLUE, YELLOW = "#1D2433", "#5B6474", "#F2611D", "#1F9D55", "#E03E3E", "#2F6FEB", "#FFC53D"
TIER = {"low": 0, "medium": 1, "high": 2}
# Video mẫu (ra_phien_ban.py --mau): giọng chỉ có vài đoạn đầu → cụm chữ/đoạn chưa có giọng được đẩy ra "rất xa",
# finish() bỏ các cảnh/phần tử đó. File dựng của từng video không phải sửa.
MAU = os.environ.get("WB_MAU") == "1"
FAR = 1e6


class _Paras(dict):
    def __missing__(self, pid):
        if MAU:
            return {"id": pid, "start": FAR, "end": FAR, "text": "", "giong": ""}
        raise KeyError(pid)
COST_PER_IMAGE = 0.057  # USD, đo vòng 1 (gpt-image-2.5-flare, high, 1024²)


def strip(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")


class Words:
    """Tìm mốc thời gian của một cụm chữ; đi tuần tự để không nhầm lần xuất hiện trước."""

    def __init__(self, words, paras):
        self.w, self.i = words, 0
        # chữ trong đoạn hỏi (qNN, giọng thứ hai) không dùng làm mốc → câu hỏi nhắc lại cụm chữ cũng không làm lệch hình
        self.keys = ["\x00" if str(x.get("para", "")).startswith("q") else strip(x["w"]) for x in words]
        self.p = _Paras({x["id"]: x for x in paras})

    def at(self, phrase, offset=0.0):
        norm = lambda t: strip(t).strip(".,:;!?…\"'“”").replace("-", "")
        toks = [norm(t) for t in phrase.split()]
        keys = [k.replace("-", "") for k in self.keys]
        for i in range(self.i, len(keys) - len(toks) + 1):
            if keys[i:i + len(toks)] == toks:
                self.i = i + 1
                return round(self.w[i]["start"] + offset, 2)
        if MAU:
            return FAR
        raise SystemExit(f"không tìm thấy cụm chữ: {phrase!r} (từ vị trí {self.i}: {' '.join(self.keys[self.i:self.i + 8])})")

    def para(self, pid):
        return self.p[pid]


class Scene:
    """Một vùng 1920×1080 trên bảng lớn. Phần tử dùng toạ độ trong cảnh."""

    def __init__(self, sid, start, origin, transition="pan", tdur=1.0):
        self.d = {"id": sid, "start": round(start, 2), "end": None, "origin": origin,
                  "transitionIn": {"type": transition, "duration": tdur if transition != "none" else 0},
                  "camera": [], "elements": []}

    def cam(self, at, x, y, scale, hold=None):
        """Camera tới (x, y, scale) lúc `at` (toạ độ trong cảnh); hold = giữ tới thời điểm đó rồi mới đi tiếp."""
        self.d.setdefault("cam", []).append({"at": round(at, 2), "x": x, "y": y, "scale": scale})
        if hold:   # giữ nhưng vẫn trôi nhẹ để không đứng hình (lỗi 7 s ở video Jev v1)
            self.d["cam"].append({"at": round(hold, 2), "x": x + 12, "y": y + 6, "scale": round(scale * 1.03, 3)})

    def add(self, e):
        if e:
            if not e["id"].startswith(self.d["id"] + "."):
                e["id"] = f"{self.d['id']}.{e['id']}"      # mã phần tử phải duy nhất trên cả video
            self.d["elements"].append(e)
        return e


class Board:
    """Dựng cả video: quản lý ảnh theo chế độ, vị trí cảnh trên bảng, luật bàn tay."""

    def __init__(self, words, paras, mode, library, cols=6, realism="low", assets_dir=None, width=1920, height=1080):
        self.W = Words(words, paras)
        self.mode, self.library, self.cols = mode, set(library), cols
        self.realism, self.assets_dir = realism, assets_dir   # độ thực tế: low | medium | high
        self.frame_w, self.frame_h = width, height            # khung hình đầu ra (1920×1080 mặc định; 1080×1920 cho Shorts)
        self.photos = set()
        self.scenes, self.images = [], set()

    # ── ảnh: có sẵn trong thư viện thì luôn dùng (miễn phí); ảnh mới chỉ khi chế độ cho phép
    def allowed(self, name, tier):
        return f"sketch-{name}" in self.library or TIER[tier] <= TIER[self.mode]

    def scene(self, sid, start, transition="pan", tdur=0.7):
        i = len(self.scenes)
        r, c = divmod(i, self.cols)
        c = c if r % 2 == 0 else self.cols - 1 - c          # đi zig-zag để camera lia ngắn
        s = Scene(sid, start, {"x": c * self.frame_w, "y": r * self.frame_h}, transition if i else "none", tdur)
        self.scenes.append(s)
        return s

    def img(self, s, id_, name, x, y, w, t, tier="low", alt=None, dur=1.3, **kw):
        if not self.allowed(name, tier):
            return s.add(alt(s) if callable(alt) else None) if alt else None
        self.images.add(f"sketch-{name}")
        e = {"id": id_, "type": "image", "src": f"assets/sketch-{name}.png", "x": x, "y": y, "w": w, "enterAt": t,
             "enter": "draw", "enterDuration": dur, "hand": True, "trace": True}
        e.update(kw)
        return s.add(e)

    def nen(self, s, id_, name, t, nhan_vat=None, w=None, **kw):
        """Bối cảnh có phối cảnh (bàn làm việc, văn phòng...) phủ cả khung hình, rồi đặt nhân vật lên "mặt sàn"
        (plan/16). Ảnh nền tạo bằng style "nen" của gen_assets.py — phủ kín khung nên hiện bằng fade, không vẽ tay.
        nhan_vat: [{"img": "<tên ảnh nhân vật, nền trong suốt>", "x":, "y":, "w":, "tre": 0.3, "dur": 0.6,
        "idle": {...} | False}, ...] — toạ độ x/y/w tuyệt đối trong cảnh, tự ước lượng theo ảnh nền đã xem
        (chưa có phối cảnh tự tính theo chiều sâu)."""
        self.img(s, id_, name, kw.pop("x", self.frame_w / 2), kw.pop("y", self.frame_h / 2), w or self.frame_w, t,
                 hand=False, enter="fade", dur=kw.pop("dur", 0.6), trace=False, **kw)
        out = []
        for i, nv in enumerate(nhan_vat or []):
            idle = nv.get("idle", {"type": "rung", "amplitude": 2, "speed": 1.4}) or None
            out.append(self.img(s, f"{id_}-nv{i}", nv["img"], nv["x"], nv["y"], nv["w"], t + nv.get("tre", 0.3),
                                hand=False, enter="fade", dur=nv.get("dur", 0.6), idle=idle, trace=False))
        return out

    def txt(self, s, id_, text, x, y, t, size=56, weight=700, color=INK, hand=True, **kw):
        e = {"id": id_, "type": "text", "text": text, "x": x, "y": y, "size": size, "weight": min(weight, 700),
             "color": color, "align": kw.pop("align", "center"), "maxWidth": kw.pop("maxWidth", 1500), "box": "none",
             "enterAt": t, "enter": "draw", "hand": hand,
             "enterDuration": kw.pop("dur", min(1.1, 0.04 * len(text) + 0.25) if hand else min(0.7, 0.025 * len(text) + 0.2))}
        e.update(kw)
        return s.add(e)

    def box(self, s, id_, label, x, y, w, h, t, fill="#FFFFFF", stroke=INK, label_color=INK, size=40, hand=True, **kw):
        e = {"id": id_, "type": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "radius": 16, "stroke": stroke,
             "strokeWidth": 4, "label": label, "labelColor": label_color, "labelSize": size, "enterAt": t, "enter": "draw",
             "enterDuration": kw.pop("dur", 0.65), "hand": hand}
        e.update(kw)
        return s.add(e)

    def circle(self, s, id_, label, x, y, r, t, fill="#FFFFFF", label_color=INK, size=36, hand=False, **kw):
        e = {"id": id_, "type": "circle", "x": x, "y": y, "r": r, "w": 2 * r, "h": 2 * r, "fill": fill, "stroke": INK,
             "strokeWidth": 4, "label": label, "labelColor": label_color, "labelSize": size, "enterAt": t, "enter": "draw",
             "enterDuration": kw.pop("dur", 0.5), "hand": hand}
        e.update(kw)
        return s.add(e)

    def panel(self, s, id_, title, x, y, w, h, t, accent=ORANGE, title_size=40):
        """Khung giấy có tiêu đề ở mép trên (thay card khi bên trong còn chữ khác, tránh tiêu đề đè nội dung)."""
        self.box(s, id_, "", x, y, w, h, t, dur=0.9)
        self.line(s, id_ + "-acc", [(x - w / 2 + 12, y - h / 2 + 8), (x + w / 2 - 12, y - h / 2 + 8)], t + 0.5,
                  color=accent, width=10, arrow=False, dur=0.3)
        return self.txt(s, id_ + "-t", title, x, y - h / 2 + 52, t + 0.6, size=title_size, hand=False)

    def q_before(self, pid):
        """Đoạn hỏi (qNN) đứng ngay trước đoạn pNN, nếu có."""
        q = "q" + pid[1:]
        return self.W.p.get(q)

    def scene_start(self, pid, lead=0.25):
        """Cảnh mở ở đầu câu hỏi (nếu có) để câu hỏi hiện trong cảnh mới, không thì sau đầu đoạn một chút."""
        q = self.q_before(pid)
        return q["start"] - 0.05 if q else self.W.p[pid]["start"] + lead

    def hoi(self, s, pid):
        """Bong bóng câu hỏi (giọng thứ hai) giữa màn hình, biến mất khi phần giải thích bắt đầu vẽ."""
        q = self.q_before(pid)
        if not q:
            return None
        t0, t1 = q["start"], q["end"] + 0.35
        self.box(s, "hoi-khung", "", 960, 520, 1360, 230, t0, fill="#FFF7E0", stroke=YELLOW, hand=False, dur=0.3, exitAt=t1, exit="fade")
        self.txt(s, "hoi-dau", "?", 380, 520, t0, size=130, color=ORANGE, hand=False, dur=0.2, exitAt=t1, exit="fade")
        return self.txt(s, "hoi-chu", q["text"], 1010, 520, t0 + 0.1, size=50, color=INK, hand=False, maxWidth=1060,
                        dur=min(1.2, 0.02 * len(q["text"]) + 0.3), exitAt=t1, exit="fade")

    def real(self, level):
        """True nếu độ thực tế hiện tại ≥ level (dùng để chọn cảnh có ảnh thật hay cảnh minh hoạ)."""
        return TIER[self.realism] >= TIER[level]

    def photo(self, s, id_, src, x, y, t, w=None, h=None, tag=None, frame=True, **kw):
        """Ảnh thật (ảnh chụp màn hình…): hiện ra rồi được khung vẽ tay bao quanh. Trả về (left, top, w, h) để khoanh vùng."""
        from PIL import Image
        iw, ih = Image.open(os.path.join(self.assets_dir, src)).size
        if w is None:
            w = h * iw / ih
        h = w * ih / iw
        self.photos.add(src)
        e = {"id": id_, "type": "image", "src": f"assets/{src}", "x": x, "y": y, "w": round(w), "enterAt": t,
             "enter": "fade", "enterDuration": 0.6, "hand": False}
        e.update(kw)
        s.add(e)
        if frame:
            self.box(s, id_ + "-fr", "", x, y, w + 24, h + 24, t + 0.3, fill="none", dur=0.7, **{k: kw[k] for k in ("exitAt", "exit") if k in kw})
        if tag:
            self.txt(s, id_ + "-tag", tag, x - w / 2 + 10, y - h / 2 - 40, t + 0.2, size=34, color=INK2, hand=False, align="left",
                     **{k: kw[k] for k in ("exitAt", "exit") if k in kw})
        return (x - w / 2, y - h / 2, w, h)

    def cite(self, s, id_, text, t, **kw):
        """Dòng trích nguồn nhỏ ở góc dưới trái (video khoa học: mọi hình/số liệu lấy từ nguồn phải ghi nguồn)."""
        return self.txt(s, id_, "Nguồn: " + text, 90, 1028, t, size=26, color=INK2, hand=False, align="left", maxWidth=1700, **kw)

    def caption(self, s, id_, words, x, y, color="#FFFFFF", active_color=ORANGE, size=46, max_width=840, **kw):
        """Phụ đề kiểu karaoke đốt sẵn vào hình (chữ đang đọc nổi bật) — dùng cho TikTok, không dùng cho YouTube
        (kênh tải phụ đề rời, không in lên hình). `words`: list các từ liên tiếp từ words.json (1 câu/cụm ngắn,
        không phải cả bài — chia bằng `chunk_caption`)."""
        t0, t1 = words[0]["start"], words[-1].get("end", words[-1]["start"] + 0.3) + kw.pop("duoi", 0.4)
        e = {"id": id_, "type": "caption",
             "words": [{"text": w["w"], "start": w["start"], "end": w.get("end", w["start"] + 0.3)} for w in words],
             "x": x, "y": y, "maxWidth": max_width, "size": size, "color": color, "activeColor": active_color,
             "enterAt": round(t0 - 0.08, 3), "enter": "fade", "exitAt": round(t1, 3), "exit": "fade"}
        e.update(kw)
        return s.add(e)

    def mark(self, s, id_, x, y, w, h, t, color=RED, **kw):
        """Khoanh một vùng (khung đỏ không nền)."""
        return self.box(s, id_, "", x, y, w, h, t, fill="none", stroke=color, hand=False, dur=0.35, **kw)

    def dashed_rect(self, s, id_, x, y, w, h, t, color=INK2, **kw):
        l, tp, r, b = x - w / 2, y - h / 2, x + w / 2, y + h / 2
        return self.line(s, id_, [(l, tp), (r, tp), (r, b), (l, b), (l, tp)], t, color=color, width=4, arrow=False, dashed=True, dur=0.9, **kw)

    def badge(self, s, id_, n, x, y, t):
        return self.circle(s, id_, str(n), x, y, 30, t, fill=ORANGE, label_color="#FFFFFF", size=36, hand=False, dur=0.3)

    ICON_MAU = {"cham-than": RED, "mo-hoi": BLUE, "suy-nghi": INK2, "bong-den": YELLOW}

    def icon(self, s, id_, kind, x, y, t, color=None, size=70, idle=True, **kw):
        """Icon phản ứng ghép từ hộp/tròn/đường có sẵn — không cần tạo ảnh AI riêng (plan/16).
        kind: cham-than (!), mo-hoi (giọt mồ hôi), suy-nghi (bong bóng suy nghĩ), bong-den (ý tưởng).
        Tự rung nhẹ liên tục (tắt bằng idle=False)."""
        col = color or self.ICON_MAU.get(kind, INK)
        r = size / 2
        rung = {"type": "rung", "amplitude": 4, "speed": 2.2} if idle else None
        if kind == "cham-than":
            self.box(s, f"{id_}-than", "", x, y - r * 0.55, size * 0.34, size * 0.9, t, fill=col, stroke="none",
                     hand=False, dur=0.25, radius=size * 0.17, idle=rung, **kw)
            return self.circle(s, f"{id_}-cham", "", x, y + r * 0.62, size * 0.18, t + 0.05, fill=col, hand=False, dur=0.2, idle=rung)
        if kind == "mo-hoi":
            d = (f"M {x} {y - r} C {x - r * 0.9} {y - r * 0.1}, {x - r * 0.6} {y + r}, {x} {y + r} "
                 f"C {x + r * 0.6} {y + r}, {x + r * 0.9} {y - r * 0.1}, {x} {y - r} Z")
            e = {"id": id_, "type": "path", "d": d, "fill": col, "stroke": "none", "arrow": False,
                 "enterAt": t, "enter": "fade", "enterDuration": 0.3, "hand": False, "idle": rung}
            e.update(kw)
            return s.add(e)
        if kind == "suy-nghi":
            self.circle(s, f"{id_}-c1", "", x, y, r, t, fill="#FFFFFF", stroke=col, hand=False, dur=0.25, idle=rung, **kw)
            self.circle(s, f"{id_}-c2", "", x - r * 0.7, y + r * 0.95, r * 0.3, t + 0.1, fill="#FFFFFF", stroke=col, hand=False, dur=0.15)
            return self.circle(s, f"{id_}-c3", "", x - r * 1.05, y + r * 1.35, r * 0.15, t + 0.18, fill="#FFFFFF", stroke=col, hand=False, dur=0.1)
        if kind == "bong-den":
            import math
            self.circle(s, f"{id_}-bulb", "", x, y - r * 0.2, r * 0.75, t, fill="#FFF7E0", stroke=col, hand=False, dur=0.25, idle=rung, **kw)
            self.box(s, f"{id_}-base", "", x, y + r * 0.7, r * 0.5, r * 0.3, t + 0.12, fill=col, stroke="none", hand=False, dur=0.15)
            for i, ang in enumerate((-45, 0, 45)):
                rad = math.radians(ang - 90)
                p0 = (x + math.cos(rad) * r * 0.9, y - r * 0.2 + math.sin(rad) * r * 0.9)
                p1 = (x + math.cos(rad) * r * 1.35, y - r * 0.2 + math.sin(rad) * r * 1.35)
                self.line(s, f"{id_}-ray{i}", [p0, p1], t + 0.18 + i * 0.05, color=col, width=4, arrow=False, dur=0.2)
            return None
        raise ValueError(f"icon lạ {kind!r} (có: {', '.join(self.ICON_MAU)})")

    def line(self, s, id_, pts, t, color=INK, width=5, arrow=True, dur=0.5, dashed=False, **kw):
        d = "M " + " L ".join(f"{x} {y}" for x, y in pts)
        e = {"id": id_, "type": "path", "d": d, "stroke": color, "strokeWidth": width, "arrow": arrow, "dashed": dashed,
             "enterAt": t, "enter": "draw", "enterDuration": dur, "hand": False}
        e.update(kw)
        return s.add(e)

    def strike(self, s, id_, x, y, w, t):
        return self.line(s, id_, [(x - w / 2, y + 4), (x + w / 2, y - 4)], t, color=RED, width=7, arrow=False, dur=0.35)

    def counter(self, s, id_, x, y, t, to, suffix="", prefix="", size=88, color=ORANGE, dur=1.0, **kw):
        e = {"id": id_, "type": "counter", "from": 0, "to": to, "decimals": 0, "prefix": prefix, "suffix": suffix,
             "x": x, "y": y, "size": size, "weight": 700, "color": color, "enterAt": t, "countDuration": dur, "enter": "fade"}
        e.update(kw)
        return s.add(e)

    def bar(self, s, id_, x, y, value, t, color, label="", w=160, maxH=520, **kw):
        e = {"id": id_, "type": "bar", "x": x, "y": y, "w": w, "maxH": maxH, "value": value, "color": color,
             "label": label, "showValue": True, "valueColor": color, "labelColor": INK, "enterAt": t, "growDuration": 1.2,
             "enter": "grow"}
        e.update(kw)
        return s.add(e)

    def card(self, s, id_, title, x, y, w, h, t, accent=BLUE, body=None, hand=True, **kw):
        e = {"id": id_, "type": "card", "x": x, "y": y, "w": w, "h": h, "title": title, "color": "#FFFFFF",
             "border": INK, "accent": accent, "titleSize": kw.pop("titleSize", 40), "enterAt": t, "enter": "draw",
             "enterDuration": kw.pop("dur", 0.8), "hand": hand}
        if body:
            e["body"], e["bodySize"] = body, kw.pop("bodySize", 28)
        e.update(kw)
        return s.add(e)

    # ── hoàn thiện: sắp bàn tay, chờ vẽ xong mới chuyển cảnh, tính độ dài
    def finish(self, duration):
        cx, cy = self.frame_w // 2, self.frame_h // 2            # tâm khung mặc định của camera (960,540 khi 1920×1080)
        sc = [s.d for s in self.scenes]
        if MAU:   # chỉ giữ phần có giọng
            lim = max(p["end"] for p in self.W.p.values()) + 0.5
            sc = [s for s in sc if s["start"] < lim]
            for s in sc:
                s["elements"] = [e for e in s["elements"] if e["enterAt"] < lim]
                if s.get("cam"):
                    s["cam"] = [k for k in s["cam"] if k["at"] < lim]
            self.scenes = [x for x in self.scenes if x.d in sc]

        def min_dur(e):
            return 1.0 if e.get("trace") else (0.55 if e["type"] in ("rect", "circle", "card", "clock") else 0.35)

        def seq(scene):
            hs = sorted([e for e in scene["elements"] if e.get("hand") and e.get("enter") == "draw"], key=lambda e: e["enterAt"])
            for a, b in zip(hs, hs[1:]):
                end = a["enterAt"] + a.get("enterDuration", 1.0)
                if end > b["enterAt"] - 0.05:
                    a["enterDuration"] = round(max(min_dur(a), b["enterAt"] - 0.05 - a["enterAt"]), 2)
                    end = a["enterAt"] + a["enterDuration"]
                    if end > b["enterAt"] - 0.05:
                        b["enterAt"] = round(end + 0.05, 2)

        drift = []
        for s in sc:
            seq(s)
        for prev, nxt in zip(sc, sc[1:]):
            draws = [e["enterAt"] + e.get("enterDuration", 0.5) for e in prev["elements"] if e.get("enter") == "draw"]
            need = (max(draws) + 0.25 + nxt["transitionIn"]["duration"]) if draws else nxt["start"]
            if nxt["start"] < need:
                drift.append((nxt["id"], round(need - nxt["start"], 2)))
                nxt["start"] = round(need, 2)
                for e in nxt["elements"]:
                    if e["enterAt"] < nxt["start"]:
                        e["enterAt"] = round(nxt["start"] + 0.05, 2)
                seq(nxt)
            prev["end"] = nxt["start"]
        last = max(e["enterAt"] + e.get("enterDuration", 0.5) for s in sc for e in s["elements"])
        duration = max(duration, round(last + 1.5, 2))
        sc[-1]["end"] = duration
        # chống đứng hình: khoảng > 4,5 s không có gì mới (vẽ/hiện/di chuyển/biến mất) → camera phóng chậm vào chỗ vừa vẽ
        for s in sc:
            if s.get("cam"):
                continue
            ev = []
            for e in s["elements"]:
                a = e["enterAt"]; ev.append((a + e.get("enterDuration", e.get("growDuration", e.get("countDuration", 0.5))), e))
                if e.get("exitAt"): ev.append((e["exitAt"] + 0.3, e))
                for mv in e.get("moves", []): ev.append((mv["at"] + mv.get("duration", 0.5), e))
            ev = sorted([x for x in ev if s["start"] <= x[0] <= s["end"]], key=lambda x: x[0])
            pts = [(s["start"], None)] + ev + [(s["end"], None)]
            keys = [{"at": s["start"], "x": cx, "y": cy, "scale": 1.0}]
            for (a, ea), (b, _) in zip(pts, pts[1:]):
                if b - a > 4.5:
                    x0, y0 = (ea.get("x", cx), ea.get("y", cy)) if ea else (cx, cy)
                    keys.append({"at": round(a + 0.2, 2), "x": cx, "y": cy, "scale": 1.0})
                    keys.append({"at": round(b - 0.3, 2), "x": round(cx + (x0 - cx) * 0.2), "y": cy, "scale": 1.06})
                    keys.append({"at": round(b + 0.5, 2), "x": cx, "y": cy, "scale": 1.0})
            if len(keys) > 1:
                s["cam"] = sorted(keys, key=lambda k: k["at"])
        for s in sc:   # camera: theo mốc riêng của cảnh nếu có, không thì trôi nhẹ để không đứng hình
            if s.get("cam"):
                keys = [{"at": s["start"], "x": cx, "y": cy, "scale": 1.0}] + [k for k in s["cam"] if k["at"] > s["start"]]
                s["camera"] = sorted(keys, key=lambda k: k["at"])
                del s["cam"]
            else:
                s["camera"] = [{"at": s["start"], "x": cx, "y": cy, "scale": 1.0},
                               {"at": s["end"], "x": cx + 15, "y": cy + 5, "scale": 1.035}]
        seen = set()
        for s in sc:
            for e in s["elements"]:
                assert e["id"] not in seen, f"trùng mã phần tử {e['id']}"
                seen.add(e["id"])
        rows = (len(sc) + self.cols - 1) // self.cols
        tl = {"style": "C", "mode": self.mode, "realism": self.realism, "fps": 30, "width": self.frame_w, "height": self.frame_h, "duration": duration,
              "audio": "voice.wav", "music": None, "background": "#FCFCFA", "font": "hand",
              "hand": {"src": "common/hand.png", "tip": {"x": 2, "y": 9}, "scale": 0.55},
              "board": {"width": self.cols * self.frame_w, "height": rows * self.frame_h}, "scenes": sc}
        return tl, drift


def load(voice_dir):
    words = json.load(open(os.path.join(voice_dir, "words.json")))
    paras = json.load(open(os.path.join(voice_dir, "paras.json")))
    return words, paras


def chunk_caption(words, n=5, max_gap=0.6):
    """Chia words.json (hoặc 1 đoạn của nó) thành các cụm ~n từ cho phụ đề karaoke (Board.caption).
    Cắt sớm hơn ở chỗ ngừng lời dài (> max_gap giây) để cụm không vắt qua hai ý khác nhau."""
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and (len(cur) >= n or w["start"] - cur[-1].get("end", cur[-1]["start"]) > max_gap):
            out.append(cur)
            cur = []
        cur.append(w)
    if cur:
        out.append(cur)
    return out
