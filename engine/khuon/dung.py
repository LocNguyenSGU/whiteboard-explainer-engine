"""Dựng timeline (kiểu C) từ STORYBOARD (YAML) thay cho file Python viết tay từng cảnh.

Dùng:
  .venv/bin/python pipeline/khuon/dung.py <storyboard.yaml> <voice_dir> <studio_public_video_dir> [--kiem-tra]
  hoặc qua ra_phien_ban.py:  --dung <storyboard.yaml>   (file .py cũ vẫn chạy như trước)
--kiem-tra: chỉ kiểm lỗi (mốc chữ, khối lạ, chữ tràn, thiếu nguồn…), không ghi timeline.

Storyboard (xem khuon/README.md):
  video: 2026-10-jev
  mode: medium            # số ảnh AI
  realism: high           # độ thực tế
  nguon: {BONN: "Deußer et al., arXiv:…"}     # tên tắt cho dòng nguồn
  scenes:
    - id: s14
      para: p12           # mở cảnh ở đầu câu hỏi qNN (nếu có) + bong bóng hỏi; hoặc `at: "cụm chữ"` (+ lead, mặc định -0.2)
      toa_ra: {...}       # các khối, dựng theo thứ tự viết; tên khối ở khuon/khoi.py (KHOI)
      nguon: {src: BONN, extra: "§4.7", at: "..."}
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))          # pipeline/ → whiteboard, videos.*
import yaml  # noqa: E402
from whiteboard import Board, load  # noqa: E402
from khuon.moc import Moc  # noqa: E402
from khuon.khoi import Ctx, KHOI  # noqa: E402
from khuon.su_kien import gan_hud, gan_am_thanh, kiem_nhan_vat, kiem_hud, kiem_chong, tat_can_mat  # noqa: E402
from khuon.kiem_tra import kiem_tra, kiem_text, kiem_so, kiem_nhip  # noqa: E402

RIENG = {"id", "ten", "para", "at", "lead", "lan", "hoi", "task", "ghi", "khoi", "bo_kiem_so", "chuong", "moc"}   # chuong/moc: HUD khuôn sự kiện (0019)   # khoá của cảnh, không phải khối; ten = tên cảnh dễ đọc (trang duyệt)


def cac_khoi(sc):
    """Các khối của cảnh theo thứ tự viết; `khoi: [{cot: …}, {cot: …}]` để dùng một khối nhiều lần."""
    out = [(k, v) for k, v in sc.items() if k not in RIENG]
    for x in sc.get("khoi", []):
        out += list(x.items())
    return out


class _CanhPhu:
    """Dùng một khối lần thứ 2+ trong cùng cảnh: thêm hậu tố vào mã phần tử để không trùng."""

    def __init__(self, s, hau_to):
        self._s, self.hau_to, self.d = s, hau_to, s.d

    def add(self, e):
        if e:
            e["id"] = e["id"] + self.hau_to
        return self._s.add(e)

    def cam(self, *a, **k):
        return self._s.cam(*a, **k)


def dung(sb, words, paras, library, adir):
    B = Board(words, paras, sb.get("mode", "medium"), library, realism=sb.get("realism", "medium"), assets_dir=adir)
    moc = Moc(words, paras)
    ctx = Ctx(B, moc, sb.get("nguon", {}))
    chuong, moc_hud = [], []
    ctx.hud = bool(sb.get("hud"))
    for sc in sb["scenes"]:
        ctx.canh = sc["id"]
        if sc.get("para"):
            s = B.scene(sc["id"], B.scene_start(sc["para"]))
            if sc.get("hoi", True):
                B.hoi(s, sc["para"])
            moc.bat_dau_canh(para=sc["para"])
        else:
            t, i = moc.tim(sc["at"], sc.get("lan", 1), noi=f"{sc['id']} · mở cảnh")
            s = B.scene(sc["id"], (t or 0.0) + float(sc.get("lead", -0.2)))
            moc.bat_dau_canh(idx=i)
        ctx.s = s
        if sc.get("chuong"):
            chuong.append((s.d, sc["chuong"]))
        if sc.get("moc") is not None:
            m = sc["moc"] if isinstance(sc["moc"], dict) else {"nhan": sc["moc"]}
            tm = moc.tim(m["at"], m.get("lan", 1), noi=f"{sc['id']} · moc")[0] if m.get("at") else None
            moc_hud.append((s.d, tm, m["nhan"]))
        ctx.co_the_tin = any(k == "the_tin" for k, _ in cac_khoi(sc))
        dem = {}
        for k, v in cac_khoi(sc):
            dem[k] = dem.get(k, 0) + 1
            try:
                KHOI[k](ctx, s if dem[k] == 1 else _CanhPhu(s, f"-{dem[k]}"), v)
            except (ValueError, FileNotFoundError) as e:      # vd. ảnh vùng không chia được → báo lỗi gọn
                moc.loi.append(f"{sc['id']} · {k}: {e}")
    tl, drift = B.finish(paras[-1]["end"] + 1.5)
    tl["paperNoise"] = True
    # Nhiễu giấy đứng yên (không trôi theo camera): render nhanh ~20%, hạt giấy vẫn còn (đo 17/10/2026: 22 s so với 28 s
    # cho 30 s video). Muốn hạt trôi theo camera như video cũ: `nhieu_troi: true` ở đầu storyboard.
    tl["noiseStatic"] = not sb.get("nhieu_troi", False)
    # T3: video dựng từ storyboard mặc định có nét vẽ tay thật (rough.js) cho hộp/mũi tên/vòng tròn và tự co chữ cho vừa ô.
    # Tắt: `net_tay: false` / `vua_chu: false` ở đầu storyboard; `do_tho` = độ "run tay" (studio mặc định 1,2; 1,5–2 rõ hơn).
    tl["rough"] = bool(sb.get("net_tay", True))
    tl["roughness"] = float(sb.get("do_tho", 1.5))
    tl["fitText"] = bool(sb.get("vua_chu", True))
    tat_can_mat(tl)
    gan_hud(tl, sb, chuong, moc_hud)        # khuôn "giải thích sự kiện" (0019): HUD, nhạc, tiếng hiệu ứng
    gan_am_thanh(tl, sb, moc)
    return B, tl, drift, moc.loi


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sb_path, vdir, pub = args[0], args[1], args[2]
    raw = open(sb_path, encoding="utf-8").read()
    sb = yaml.safe_load(raw)
    words, paras = load(vdir)
    adir = os.path.join(pub, "assets")
    library = [f[:-4] for f in os.listdir(adir) if f.startswith("sketch-") and f.endswith(".png") and ".trace" not in f] if os.path.isdir(adir) else []

    loi, canh_bao = kiem_tra(sb, KHOI, RIENG, cac_khoi)
    loi = kiem_text(raw) + loi
    if loi:                     # lỗi cấu trúc: dừng trước khi dựng
        for x in loi:
            print("  LỖI:", x)
        sys.exit(1)
    B, tl, drift, loi_moc = dung(sb, words, paras, library, adir)
    loi += loi_moc
    loi += kiem_nhip(tl, words, sb)
    canh_bao += kiem_so(tl, words, sb)
    canh_bao += kiem_nhan_vat(tl)
    canh_bao += kiem_hud(tl, os.path.join(pub, "assets"))
    canh_bao += kiem_chong(tl, os.path.join(pub, "assets"))
    for x in canh_bao:
        print("  cảnh báo:", x)
    for x in loi:
        print("  LỖI:", x)
    n_el = sum(len(s["elements"]) for s in tl["scenes"])
    print(f"storyboard {os.path.basename(sb_path)}: {len(sb['scenes'])} cảnh · {n_el} phần tử · {len(loi)} lỗi · {len(canh_bao)} cảnh báo")
    if loi:
        sys.exit(1)
    if "--kiem-tra" in sys.argv:
        tl.pop("_nhac_cues", None)
        return
    cues = tl.pop("_nhac_cues", None)
    if cues:                    # nhạc theo đoạn (0019): trộn thành music.wav, hạ nhạc khi có giọng
        from tron_nhac import tron
        kq = tron(cues, os.path.join(vdir, "voice.wav"), os.path.join(pub, "music.wav"), tl["duration"])
        tl["music"] = {"src": "music.wav", "volume": 1.0}
        print(f"nhạc: {kq['so_doan']} đoạn → music.wav (giọng {kq['giong_db']} dB)")
        # CC BY 4.0 (Incompetech): bắt buộc ghi công trong mô tả video — gom sẵn để chép vào dang-youtube.md
        bai = sorted({os.path.basename(c["bai"])[:-4] for c in cues if c.get("bai", "").startswith("incompetech/")})
        if bai:
            tl["ghi_cong_nhac"] = [f'"{b}" Kevin MacLeod (incompetech.com) — Licensed under Creative Commons: By Attribution 4.0 License, '
                                   "http://creativecommons.org/licenses/by/4.0/" for b in bai]
            print("ghi công nhạc (chép vào mô tả video):\n  " + "\n  ".join(tl["ghi_cong_nhac"]))
    json.dump(tl, open(os.path.join(pub, "timeline-C.json"), "w"), ensure_ascii=False, indent=1)
    anh = {re.sub(r"__v\d+$", "", x) for x in B.images}       # ảnh vùng (…__v1, __v2) tính là 1 ảnh AI
    print(f"{tl['duration']:.1f}s · {len(tl['scenes'])} cảnh · ảnh AI {len(anh)} · ảnh thật/công thức {len(B.photos)}")
    if drift:
        print("lùi chuyển cảnh:", ", ".join(f"{a}+{b}s" for a, b in drift))


if __name__ == "__main__":
    main()
