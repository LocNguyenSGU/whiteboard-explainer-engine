"""Mốc thời gian ƯỚC TÍNH từ lời thoại (không gọi API giọng, 0 đồng), để dựng/duyệt bố cục hình trước khi có giọng thật.

Dùng:  .venv/bin/python pipeline/fake_timing.py <lời-thoại.md> <out_dir> [--nguon vieneu|elevenlabs]
- Đọc đoạn `## pNN` (giải thích) và `## qNN · hỏi` (hỏi); bỏ nhãn cảm xúc [curious]… khỏi chữ.
- Nhịp theo nguồn giọng (ký tự/giây khi đang nói) + nghỉ sau dấu câu, nghỉ giữa các đoạn như giong.py
  (0,35 s sau câu hỏi, 0,6 s sau đoạn giải thích). HE_SO hiệu chỉnh theo giọng thật (Jev v2 ElevenLabs, mẫu 01 VieNeu).
Xuất words.json, paras.json (đúng định dạng giong.py), voice.wav (im lặng), usage.json {"uoc_tinh": true}.
"""
import json, os, re, sys, wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nguon_giong.cam_xuc import bo_nhan  # noqa: E402

# ký tự/giây lúc đang nói (chưa tính nghỉ); chỉnh cho khớp tổng thời lượng giọng thật
HE_SO = {"elevenlabs": 16.2, "vieneu": 20.6}
NGHI_PHAY, NGHI_CAU = 0.18, 0.32


def uoc_tinh(md, out, nguon="vieneu"):
    os.makedirs(out, exist_ok=True)
    s = open(md, encoding="utf-8").read()
    s = re.sub(r"^\s*`\[[^\n]*\]`\s*$\n?", "", s, flags=re.M)      # bỏ dòng ghi chú dựng `[ẢNH: …]`, như giong.py
    paras = [(p, t.strip()) for p, t in re.findall(r"^## ([pq]\d+)[^\n]*\n(.*?)(?=\n## |\n# |\Z)", s, re.S | re.M)]
    cps = HE_SO[nguon]
    words, pinfo, t = [], [], 0.0
    for pid, text in paras:
        text = bo_nhan(text)
        start = t
        for line in text.splitlines():
            for tok in line.split():
                w = re.sub(r"[^\wÀ-ỹ-]", "", tok)
                if w:
                    d = (len(tok) + 1) / cps
                    words.append({"w": w, "start": round(t, 3), "end": round(t + d * 0.9, 3), "para": pid})
                    t += d
                if re.search(r"[,:;]$", tok):
                    t += NGHI_PHAY
                if re.search(r"[.?!…]$", tok):
                    t += NGHI_CAU
            t += NGHI_CAU
        pinfo.append({"id": pid, "start": round(start, 3), "end": round(t, 3), "text": text,
                      "giong": "hoi" if pid.startswith("q") else "giai-thich"})
        t += 0.35 if pid.startswith("q") else 0.6
    json.dump(words, open(os.path.join(out, "words.json"), "w"), ensure_ascii=False)
    json.dump(pinfo, open(os.path.join(out, "paras.json"), "w"), ensure_ascii=False, indent=1)
    with wave.open(os.path.join(out, "voice.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b"\0\0" * int(24000 * (t + 1)))
    json.dump({"uoc_tinh": True, "nguon": nguon, "characters_this_run": 0}, open(os.path.join(out, "usage.json"), "w"))
    return t, len(words), len(pinfo)


if __name__ == "__main__":
    ng = sys.argv[sys.argv.index("--nguon") + 1] if "--nguon" in sys.argv else "vieneu"
    a = [x for x in sys.argv[1:] if not x.startswith("--") and x != ng]
    t, nw, npar = uoc_tinh(a[0], a[1], ng)
    print(f"ước tính ({ng}) {t:.1f}s · {nw} chữ · {npar} đoạn")
