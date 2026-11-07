"""Một ảnh AI cho cả cảnh, vẽ dần TỪNG VÙNG theo lời (giảm số ảnh phải tạo: 1 ảnh thay vì 3–4).

Cách làm (ý tưởng "vùng được phép vẽ" từ geeklee/srt-whiteboard-animation, MIT — tự viết lại):
1. Tìm các mảng mực (điểm ảnh không trong suốt), nối nét gần nhau thành một vật (giãn nở nhẹ rồi gán nhãn liền khối).
2. Gom vật vào N vùng:
   - tự động: chia theo vị trí tâm (trái → phải, hoặc trên → dưới) tại N−1 khoảng trống lớn nhất;
   - hoặc theo khung tay `khung: [x0, y0, x1, y1]` (tỉ lệ 0..1): vật thuộc khung chứa tâm của nó.
   Cả vật được gán nguyên vào MỘT vùng → không cắt đôi nét, không vẽ trùng.
3. Mỗi vùng → một ảnh cắt (chỉ mực của vùng đó, phần còn lại trong suốt) + trace riêng (trace_map.py).
   Studio vẽ từng ảnh cắt đúng chỗ của nó trong ảnh gốc → ghép lại thành ảnh nguyên vẹn.
Ảnh cắt lưu cạnh ảnh gốc: sketch-<tên>__v<k>.png (+ .trace.*), tạo lại khi ảnh gốc hoặc cách chia đổi.
"""
import hashlib, json, os, subprocess, sys
import numpy as np
from PIL import Image
from scipy import ndimage

PIPE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = os.path.join(os.path.dirname(PIPE), ".venv", "bin", "python")


def _muc(rgba):
    a = rgba[..., 3]
    if a.min() < 250:                       # ảnh nền trong suốt (gen_assets)
        return a > 24
    rgb = rgba[..., :3].astype(int)          # ảnh nền trắng
    return rgb.min(axis=2) < 235


def chia(src, vung, huong="ngang"):
    """→ (W, H, [mask_k]) ; vung: danh sách dict (có thể có `khung`)."""
    im = np.array(Image.open(src).convert("RGBA"))
    H, W = im.shape[:2]
    muc = _muc(im)
    r = max(2, round(0.012 * max(W, H)))                      # nối nét gần nhau (cùng một vật)
    nhan, n = ndimage.label(ndimage.binary_dilation(muc, iterations=r))
    nhan = nhan * muc
    if n == 0:
        raise ValueError(f"{os.path.basename(src)}: ảnh không có nét nào")
    tam = ndimage.center_of_mass(muc, nhan, range(1, n + 1))   # (y, x) từng vật
    co = ndimage.sum(muc, nhan, range(1, n + 1))
    k = len(vung)
    gan = np.zeros(n + 1, int)                                  # vật → vùng
    if any(v.get("khung") for v in vung):
        for i, (cy, cx) in enumerate(tam, 1):
            fx, fy = cx / W, cy / H
            hit = [j for j, v in enumerate(vung) if v.get("khung") and v["khung"][0] <= fx <= v["khung"][2] and v["khung"][1] <= fy <= v["khung"][3]]
            if hit:
                gan[i] = hit[0]
            else:                                               # ngoài mọi khung → khung gần nhất
                d = [((fx - (v["khung"][0] + v["khung"][2]) / 2) ** 2 + (fy - (v["khung"][1] + v["khung"][3]) / 2) ** 2) if v.get("khung") else 9
                     for v in vung]
                gan[i] = int(np.argmin(d))
    else:
        if n < k:
            raise ValueError(f"{os.path.basename(src)}: chỉ tìm thấy {n} vật tách rời, không chia được {k} vùng — giảm số vùng, hoặc dùng `khung`")
        truc = [c[1] if huong == "ngang" else c[0] for c in tam]
        thu_tu = np.argsort(truc)
        # vật rất nhỏ (chấm, nét lẻ) không được làm "khoảng trống" chia vùng
        lon = [i for i in thu_tu if co[i] >= 0.01 * max(co)]
        vi_tri = sorted(truc[i] for i in lon)
        khe = sorted(range(1, len(vi_tri)), key=lambda j: vi_tri[j] - vi_tri[j - 1], reverse=True)[:k - 1]
        moc = sorted((vi_tri[j - 1] + vi_tri[j]) / 2 for j in khe)
        for i in range(n):
            gan[i + 1] = int(np.searchsorted(moc, truc[i]))
    masks = [np.isin(nhan, [i for i in range(1, n + 1) if gan[i] == j]) & muc for j in range(k)]
    return W, H, masks, im


def tao_vung(src, vung, huong="ngang", pad=6):
    """Cắt ảnh theo vùng, tính trace cho ảnh cắt (có bộ nhớ tạm). → (W, H, [(ten, (x0, y0, x1, y1))]);
    `ten` không có tiền tố "sketch-" (Board.img tự thêm), file là sketch-<goc>__v<k>.png."""
    goc = os.path.basename(src)[:-4]
    dau = hashlib.sha1((str(os.path.getmtime(src)) + json.dumps([v.get("khung") for v in vung]) + huong).encode()).hexdigest()[:10]
    meta_p = os.path.join(os.path.dirname(src), f"{goc}__vung.json")
    if os.path.exists(meta_p):
        meta = json.load(open(meta_p))
        if meta.get("hash") == dau and all(os.path.exists(os.path.join(os.path.dirname(src), f"sketch-{f}.trace.json")) for f, _ in meta["vung"]):
            return meta["W"], meta["H"], [(f, tuple(b)) for f, b in meta["vung"]]
    W, H, masks, im = chia(src, vung, huong)
    out, files = [], []
    for k, m in enumerate(masks):
        ys, xs = np.nonzero(m)
        if len(ys) == 0:
            raise ValueError(f"{os.path.basename(src)}: vùng {k + 1} trống (không có vật nào) — kiểm lại `khung` hoặc số vùng")
        x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
        x1, y1 = min(W, xs.max() + 1 + pad), min(H, ys.max() + 1 + pad)
        cat = im[y0:y1, x0:x1].copy()
        cat[..., 3] = np.where(m[y0:y1, x0:x1], cat[..., 3], 0)
        ten = f"{goc}__v{k + 1}"
        p = os.path.join(os.path.dirname(src), ten + ".png")
        Image.fromarray(cat).save(p)
        files.append(p)
        out.append((ten[len("sketch-"):] if ten.startswith("sketch-") else ten, (int(x0), int(y0), int(x1), int(y1))))
    subprocess.run([PY, os.path.join(PIPE, "trace_map.py"), *files], check=True, capture_output=True)
    json.dump({"hash": dau, "W": W, "H": H, "vung": out}, open(meta_p, "w"))
    return W, H, out


if __name__ == "__main__":     # thử: python anh_vung.py <ảnh.png> <số vùng>
    W, H, v = tao_vung(sys.argv[1], [{}] * int(sys.argv[2]))
    print(W, H, v)
