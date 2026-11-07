"""Tìm mốc thời gian cho cụm chữ trong lời thoại (words.json) — không phụ thuộc thứ tự khai báo.

Khác `whiteboard.Words.at` (con trỏ chỉ tiến, phải khai báo mốc đúng thứ tự lời đọc): mỗi cảnh có một điểm bắt đầu
(đầu đoạn `para`, hoặc mốc mở cảnh), mọi cụm chữ trong cảnh tìm từ điểm đó → viết `at:` ngay cạnh nội dung, thứ tự tuỳ ý.
Chữ của đoạn hỏi (qNN) không dùng làm mốc (câu hỏi nhắc lại cụm chữ không làm lệch hình), giống whiteboard.
"""
import os
from whiteboard import strip

FAR = 1e6
MAU = os.environ.get("WB_MAU") == "1"     # video mẫu: cụm chữ chưa có giọng → đẩy ra xa, không báo lỗi


def _norm(t):
    return strip(t).strip(".,:;!?…\"'“”()").replace("-", "")


class Moc:
    def __init__(self, words, paras):
        self.w = words
        self.keys = ["\x00" if str(x.get("para", "")).startswith("q") else _norm(x["w"]) for x in words]
        self.first = {}
        for i, x in enumerate(words):
            self.first.setdefault(x.get("para"), i)
        self.paras = {p["id"]: p for p in paras}
        self.loi = []          # lỗi gom lại cho lint
        self.goc = 0           # chỉ số chữ bắt đầu tìm của cảnh hiện tại

    def bat_dau_canh(self, para=None, idx=None):
        """Đặt điểm bắt đầu tìm cho cảnh mới (không lùi về trước cảnh trước)."""
        if para is not None and para in self.first:
            self.goc = max(self.goc, self.first[para])
        elif idx is not None:
            self.goc = max(self.goc, idx)

    def tim(self, phrase, lan=1, noi=""):
        """→ (thời điểm, chỉ số chữ) của lần xuất hiện thứ `lan` tính từ điểm bắt đầu cảnh; None nếu không thấy."""
        toks = [_norm(t) for t in str(phrase).split() if _norm(t)]
        n, dem = len(toks), 0
        for i in range(self.goc, len(self.keys) - n + 1):
            if self.keys[i:i + n] == toks:
                dem += 1
                if dem == lan:
                    return self.w[i]["start"], i
        if MAU:
            return FAR, len(self.keys)
        self.loi.append(f"{noi}: không tìm thấy cụm chữ {phrase!r} (tìm từ: {' '.join(x['w'] for x in self.w[self.goc:self.goc + 8])} …)")
        return None, None
