"""Kiểm storyboard TRƯỚC khi dựng/tạo ảnh/tạo giọng (chỗ bắt đầu tốn tiền).

Lỗi (dừng): khối không có trong thư viện, cảnh thiếu `para`/`at`, trùng id cảnh; mốc chữ không tìm thấy (kiểm khi dựng, moc.py).
Cảnh báo: cảnh có ảnh mà không có dòng nguồn; hai cảnh liền nhau cùng bộ khối (đơn điệu); chữ có thể tràn ô.
Chưa có (T2): số trên hình phải có trong lời đọc hoặc nguồn.
"""

import re
from khuon.khoi import _chu

RONG_CHU = 0.55     # bề rộng trung bình một ký tự ≈ 0,55 × cỡ chữ (font tay, đo ước lượng)


def _tran(text, co, rong):
    return len(str(text)) * co * RONG_CHU > rong


GON_KHONG_NGOAC = re.compile(r"""^\s*(?:-\s+|[\w]+:\s+)(?!["'\[{])[^#\n]*\s@\s[^\n]*\s#[\w-]""")


def kiem_text(raw):
    """Quét file YAML thô: chuỗi gọn có #màu mà KHÔNG đặt trong ngoặc kép → YAML đã cắt mất #màu như chú thích."""
    return [f"dòng {i}: chuỗi gọn có #tag nhưng không có ngoặc kép (YAML cắt mất phần #…): {l.strip()[:70]}"
            for i, l in enumerate(raw.splitlines(), 1) if GON_KHONG_NGOAC.search(l)]


KHONG_TINH_NHIP = (".nguon", "-fr", "tg-truc", "-tag")    # dòng nguồn, khung ảnh, trục: hiện kèm khối chính, không phải hình mới


def kiem_nhip(tl, words, sb):
    """Quãng lời vẫn chạy mà không có hình mới (Lộc chê 2 lần: 25/10 và 27/10/2026). Trả về lỗi kèm lời đọc trong quãng
    để biết cần minh hoạ câu nào. Ngưỡng `nhip_toi_da` ở đầu storyboard (mặc định 4 s)."""
    nguong = float(sb.get("nhip_toi_da", 4.0))
    moc = sorted({round(e["enterAt"], 1) for s in tl["scenes"] for e in s["elements"]
                  if e.get("enterAt") is not None and not e["id"].endswith(KHONG_TINH_NHIP)})
    het = max((w["end"] for w in words), default=0.0)
    loi = []
    for a, b in zip(moc, moc[1:] + [het]):
        if b - a > nguong:
            loi_doc = " ".join(w["w"] for w in words if a + 0.3 <= w["start"] < b)
            loi.append(f"{b - a:.1f}s không có hình mới ({a:.1f}s → {b:.1f}s): “{loi_doc[:110]}”")
    return loi


def kiem_tra(sb, KHOI, RIENG, cac_khoi):
    loi, cb, ids, truoc = [], [], set(), None
    for sc in sb.get("scenes", []):
        sid = sc.get("id", "?")
        if sid in ids:
            loi.append(f"{sid}: trùng id cảnh")
        ids.add(sid)
        if not sc.get("para") and not sc.get("at"):
            loi.append(f"{sid}: cảnh cần `para: pNN` hoặc `at: \"cụm chữ\"` để biết lúc mở")
        khoi = cac_khoi(sc)
        for k, _ in khoi:
            if k not in KHOI:
                loi.append(f"{sid}: khối lạ `{k}` (có: {', '.join(sorted(KHOI))})")
        ten = tuple(k for k, _ in khoi if k != "nguon")
        if ten and ten == truoc:
            cb.append(f"{sid}: cùng bộ khối với cảnh trước ({', '.join(ten)}) — người xem dễ thấy lặp")
        truoc = ten
        d = dict(khoi)
        n_loi = len(loi)
        for k, v in khoi:      # mục bị YAML hiểu nhầm (chuỗi có ': ' không có ngoặc kép)
            ds = v if isinstance(v, list) else (v.get("items", []) if isinstance(v, dict) else [])
            for it in ds:
                try:
                    _chu(it)
                except ValueError as e:
                    loi.append(f"{sid} · {k}: {e}")
        if len(loi) > n_loi:
            continue

        if "anh" in d and "nguon" not in d:
            cb.append(f"{sid}: có ảnh thật nhưng thiếu dòng `nguon`")
        for it in (d.get("the3") or []) if isinstance(d.get("the3"), list) else (d.get("the3") or {}).get("items", []):
            it = _chu(it)
            if _tran(it.get("title", ""), 60, 460):
                cb.append(f"{sid}: tiêu đề thẻ dài (sẽ tự co chữ, tối đa còn 60%): {it.get('title')!r}")
        if isinstance(d.get("toa_ra"), dict):
            for it in d["toa_ra"].get("den", []):
                t = _chu(it)["text"]
                if _tran(t, 34, 320):
                    cb.append(f"{sid}: chữ trong hộp nhánh dài (sẽ tự co chữ, tối đa còn 60%): {t!r}")
        if d.get("cot") is not None:
            ds, opt = (d["cot"], {}) if isinstance(d["cot"], list) else (d["cot"].get("items", []), d["cot"])
            khe = opt.get("w", 150) + opt.get("gap", 90)
            for it in ds:
                if _tran(_chu(it)["label"], 32, khe - 10):
                    cb.append(f"{sid}: nhãn cột dài, đè nhãn bên cạnh: {_chu(it)['label']!r} (rút gọn hoặc tăng gap)")
        td = d.get("tieu_de")
        if td and _tran(_chu(td)["text"], 52, 1700):
            cb.append(f"{sid}: tiêu đề dài, sẽ xuống dòng")
    return loi, cb


def _co(mau_doc, loi_doc):
    """mau_doc có thể chứa ' ~ ' = 0–2 chữ bất kỳ chen giữa."""
    if " ~ " not in mau_doc:
        return mau_doc in loi_doc
    a, b = mau_doc.split(" ~ ", 1)
    return re.search(re.escape(a.rstrip()) + r"(?: \S+){0,2} " + re.escape(b.strip()) + " ", loi_doc) is not None


def kiem_so(tl, words, sb):
    """Cảnh báo: số hiện trên hình mà lời đọc của cảnh không nhắc tới (kể cả dạng đọc bằng chữ).
    Bỏ qua: dòng nguồn, nhãn ảnh, thẻ tin (ngày tháng), số thứ tự danh sách, số nguyên một chữ số. Số đã quy đổi đơn vị (vd. "4,2 xu" → "$0,042")
    thì ghi vào `bo_kiem_so: ["0,042"]` của cảnh."""
    from whiteboard import strip
    from khuon.doc_so import doc, SO

    def norm(t):
        return " " + " ".join(strip(w).strip(".,:;!?…\"'“”()") for w in t.split()) + " "

    bo = {sc["id"]: {str(x) for x in sc.get("bo_kiem_so", [])} for sc in sb.get("scenes", [])}
    out = []
    for sc in tl["scenes"]:
        ws = [w["w"] for w in words if sc["start"] - 0.5 <= w["start"] <= sc["end"]]
        loi_doc, tho = norm(" ".join(ws)), " ".join(ws)
        da = set()
        for e in sc["elements"]:
            eid = e["id"].split(".", 1)[-1]
            if eid == "nguon" or eid.endswith("-tag") or eid.startswith("tt") or eid.startswith("bs") or e["type"] in ("circle", "bar", "path", "image"):
                continue
            chu = [e.get(k) for k in ("text", "label", "title", "body") if e.get(k)]
            if e["type"] == "counter":
                chu.append(str(e.get("to")))
            for c in chu:
                if str(c).startswith("Nguồn:"):
                    continue
                c = re.sub(r"^\s*\d+\.\s", "", str(c))
                for so in SO.findall(c):
                    if so in da or so in bo.get(sc["id"], set()) or so in tho or (so.isdigit() and int(so) < 10):
                        continue
                    da.add(so)
                    cach = doc(so)
                    if cach and not any(_co(norm(v), loi_doc) for v in cach):
                        out.append(f"{sc['id']}: số '{so}' trên hình không thấy trong lời đọc của cảnh "
                                   f"(đọc là: '{sorted(cach)[0]}'). Kiểm lại số, hoặc thêm vào `bo_kiem_so` nếu đã quy đổi đơn vị")
    return out
