"""Nhận diện nhãn cảm xúc trong lời thoại và đổi sang cách thể hiện của nguồn giọng đích (quyết định 0014, plan/12 mục 4).

Nhãn = chữ trong ngoặc vuông, không có số, không theo sau bởi "(" (không phải link markdown): [curious], [cười], [thở dài].
`[5]`, `[0, 1]`, `[plan/09]` KHÔNG phải nhãn.
Nhãn áp cho CÂU ĐỨNG SAU nó (tới dấu . ? ! … hoặc hết dòng), giống cách eleven_v3 đọc.
Thứ tự: giữ (nguồn đọc được) → nhãn tương đương / gần nghĩa → dấu câu → thán từ (chỉ khi bật) → bỏ + cảnh báo.
"""
import json, os, re

NHAN = re.compile(r"\[((?:[^\W\d_]| )+)\](?!\()[ \t]*")
BANG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cam_xuc.json"), encoding="utf-8"))
MUC_TEN = {"giu": "giữ", "tuong-duong": "đổi tương đương", "gan-nghia": "đổi gần nghĩa", "dau-cau": "dấu câu",
           "than-tu": "thán từ", "bo": "BỎ"}


def bo_nhan(text):
    """Lời không còn nhãn (cho phụ đề, mốc chữ, đếm độ dài)."""
    return NHAN.sub("", text)


def chuyen(text, nguon, them_than_tu=False, pid=""):
    """Trả về (lời đã chuyển, danh sách thay đổi). nguon: khoá trong cam_xuc.json → 'nguon'."""
    cfg = BANG["nguon"][nguon]
    res, log = text, []
    for m in reversed(list(NHAN.finditer(text))):          # từ cuối lên để vị trí phía trước không lệch
        raw, a, b = m.group(1).strip(), m.start(), m.end()
        key = BANG["bi_danh"].get(raw.lower())
        th = cfg["the_hien"].get(key, {}) if key else {}
        e = re.search(r"[.?!…]|\n|$", res[b:])
        body_end = b + e.start()
        punct = res[body_end] if body_end < len(res) and res[body_end] in ".?!…" else ""
        after = body_end + len(punct)
        body, truoc = res[b:body_end], (res[b:after]).strip()
        tag = ""
        if cfg.get("giu_nhan_tieng_anh") and re.fullmatch(r"[a-zA-Z ]+", raw):
            muc, tag = "giu", f"[{raw}] "
        elif th.get("nhan"):
            muc, tag = th.get("muc", "tuong-duong"), th["nhan"] + " "
        elif th.get("dau_cau") == "?" and punct == "?":
            muc = "dau-cau"                                 # đã là câu hỏi → tự lên giọng hỏi
        elif th.get("dau_cau") in ("!", "…") and punct == ".":
            muc, punct = "dau-cau", th["dau_cau"]
        elif th.get("than_tu") and them_than_tu:
            muc, body = "than-tu", th["than_tu"] + " " + body     # không tự viết thường: chữ đầu có thể là tên riêng (Jev)
        else:
            muc = "bo"
        res = res[:a] + tag + body + punct + res[after:]
        log.append({"doan": pid, "nhan": f"[{raw}]", "ma": key or "(lạ)", "muc": muc, "nhan_moi": tag.strip(),
                    "truoc": truoc, "sau": (tag + body + punct).strip()})
    log.reverse()
    return res, log


def bao_cao(log, nguon, path=None):
    """Tóm tắt + bảng markdown (cam-xuc.md). Trả về (dòng tóm tắt, đếm theo mức)."""
    dem = {}
    for x in log:
        dem[x["muc"]] = dem.get(x["muc"], 0) + 1
    tom = " · ".join(f"{MUC_TEN[k]} {dem[k]}" for k in MUC_TEN if k in dem) or "không có nhãn"
    lines = [f"# Nhãn cảm xúc → nguồn `{nguon}`", "", f"**{len(log)} nhãn:** {tom}", "",
             "| Đoạn | Nhãn gốc | Mã | Xử lý | Câu trước | Câu sau |", "|---|---|---|---|---|---|"]
    for x in log:
        moi = f" → `{x['nhan_moi']}`" if x["nhan_moi"] and x["muc"] != "giu" else ""
        lines.append(f"| {x['doan']} | `{x['nhan']}` | {x['ma']} | {MUC_TEN[x['muc']]}{moi} | {x['truoc']} | {x['sau']} |")
    if path:
        open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return tom, dem
