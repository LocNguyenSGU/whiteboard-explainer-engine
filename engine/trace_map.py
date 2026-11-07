"""Tính "bản đồ thời gian vẽ" cho ảnh kiểu bút dạ, để bàn tay vẽ theo ĐƯỜNG VIỀN trước rồi mới tô màu.

Dùng:  .venv/bin/python pipeline/trace_map.py <asset.png> [<asset2.png> ...] [--preview <out.mp4>]
Xuất cạnh mỗi ảnh:
- <name>.trace.png : ảnh xám, mỗi điểm ảnh = thời điểm được vẽ (0 = đầu tiên, 254 = cuối cùng, 255 = không vẽ)
- <name>.trace.json: {"width","height","outlineEnd","path":[[t,x,y],...]} — đường đi của đầu bút, t trong 0..1
Cách tính: tách nét viền tối → làm mảnh (skeleton) → nối thành các nét liên tục, nét sau bắt đầu gần chỗ nét trước kết thúc
→ viền chiếm 0..OUTLINE_END thời gian; sau đó tô từng vùng màu theo đường zig-zag, vùng lớn được nhiều thời gian hơn.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from skimage.morphology import skeletonize

OUTLINE_END = 0.6
NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def order_skeleton(skel):
    ys, xs = np.nonzero(skel)
    if len(ys) == 0:
        return []
    remaining = np.ones(len(ys), bool)
    index = {(int(y), int(x)): i for i, (y, x) in enumerate(zip(ys, xs))}
    seq, pen = [], (0, 0)
    while remaining.any():
        cand = np.nonzero(remaining)[0]
        d = (ys[cand] - pen[0]) ** 2 + (xs[cand] - pen[1]) ** 2
        cur = int(cand[np.argmin(d)])
        stroke, prev_dir = [], (0, 0)
        while cur is not None:
            remaining[cur] = False
            y, x = int(ys[cur]), int(xs[cur])
            stroke.append((y, x))
            nxt, best = None, -9
            for dy, dx in NB:
                j = index.get((y + dy, x + dx))
                if j is not None and remaining[j]:
                    score = dy * prev_dir[0] + dx * prev_dir[1]   # ưu tiên đi thẳng tiếp
                    if score > best:
                        best, nxt, nd = score, j, (dy, dx)
            if nxt is not None:
                prev_dir = nd
            cur = nxt
        seq.append(stroke)
        pen = stroke[-1]
    return seq


def _refine_order(strokes):
    """2-opt giới hạn: đảo một đoạn nét liên tiếp (và chiều từng nét trong đoạn) nếu rút ngắn quãng tay di chuyển
    giữa các nét. Chỉ đổi THỨ TỰ/CHIỀU vẽ, không đổi hình các nét. Ý tưởng từ whiteboard-animation-vi
    (letuandat131, CC0) — route refinement bằng 2-opt có cửa sổ giới hạn, ưu tiên đi xuống (đỡ tay giật ngược lên)."""
    n = len(strokes)
    if n < 3:
        return strokes

    def d(a, b):
        return float(np.hypot(a[0] - b[0], a[1] - b[1])) + 0.08 * max(a[0] - b[0], 0)   # phạt nhẹ khi tay đi ngược lên trên

    for _ in range(2):
        ends = [(s[0], s[-1]) for s in strokes]
        best, change = 0.0, None
        for left in range(n):
            prev = (0, 0) if left == 0 else ends[left - 1][1]
            for right in range(left + 1, min(n, left + 14)):
                old = d(prev, ends[left][0])
                new = d(prev, ends[right][1])
                if right + 1 < n:
                    old += d(ends[right][1], ends[right + 1][0])
                    new += d(ends[left][0], ends[right + 1][0])
                if old - new > best + 1e-6:
                    best, change = old - new, (left, right)
        if change is None:
            break
        left, right = change
        strokes[left:right + 1] = [s[::-1] for s in strokes[left:right + 1][::-1]]
    return strokes


def travel(strokes):
    """Tổng quãng đường tay di chuyển: trong từng nét + giữa các nét (để so trước/sau refine)."""
    pen, total = (0, 0), 0.0
    for s in strokes:
        total += float(np.hypot(s[0][0] - pen[0], s[0][1] - pen[1]))
        for a, b in zip(s, s[1:]):
            total += float(np.hypot(a[0] - b[0], a[1] - b[1]))
        pen = s[-1]
    return total


def build(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im).astype(np.float32)
    H, W = a.shape[:2]
    obj = a[..., 3] > 30
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    outline = obj & (lum < 80)
    skel = skeletonize(outline)
    strokes = order_skeleton(skel)
    strokes = [s for s in strokes if len(s) >= 6] or strokes          # bỏ chấm vụn
    strokes = _refine_order(strokes)                                   # rút ngắn quãng tay di chuyển giữa các nét
    total = sum(len(s) for s in strokes) or 1

    tmap = np.full((H, W), 2.0, np.float32)                            # 2 = chưa gán
    path_pts, k = [], 0
    skel_t = np.full((H, W), np.nan, np.float32)
    for s in strokes:
        for j, (y, x) in enumerate(s):
            t = OUTLINE_END * k / total
            skel_t[y, x] = t
            if j % 6 == 0 or j == len(s) - 1:
                path_pts.append([round(t, 4), x, y])
            k += 1
    # điểm viền lấy thời gian của điểm skeleton gần nhất
    if strokes:
        _, (iy, ix) = ndimage.distance_transform_edt(np.isnan(skel_t), return_indices=True)
        near = skel_t[iy, ix]
        tmap[outline] = near[outline]
    else:
        tmap[outline] = 0.0

    # vùng tô màu: theo thứ tự viền quanh nó được vẽ xong
    fill = obj & ~outline
    lab, n = ndimage.label(fill, structure=np.ones((3, 3)))
    regions = []
    for r in range(1, n + 1):
        m = lab == r
        area = int(m.sum())
        if area < 40:
            tmap[m] = OUTLINE_END
            continue
        ring = ndimage.binary_dilation(m, iterations=3) & outline
        key = float(np.max(tmap[ring])) if ring.any() else OUTLINE_END
        regions.append((key, r, area))
    regions.sort()
    fill_total = sum(a for _, _, a in regions) or 1
    t0 = OUTLINE_END
    for _, r, area in regions:
        m = lab == r
        span = (1 - OUTLINE_END) * area / fill_total
        ry, rx = np.nonzero(m)
        y0, y1 = ry.min(), ry.max()
        h = max(1, y1 - y0)
        band = 16                                                       # bề rộng một lượt tô
        rows = (ry - y0) // band
        nrows = int(rows.max()) + 1
        xmin, xmax = rx.min(), rx.max()
        w = max(1, xmax - xmin)
        frac_x = (rx - xmin) / w
        frac_x = np.where(rows % 2 == 0, frac_x, 1 - frac_x)           # zig-zag trái-phải
        local = (rows + frac_x) / nrows
        tmap[ry, rx] = t0 + span * local
        for rr in range(nrows):
            yy = int(y0 + rr * band + band / 2)
            sel = rows == rr
            if not sel.any():
                continue
            xa, xb = int(rx[sel].min()), int(rx[sel].max())
            seq = [(xa, xb), (xb, xa)][rr % 2]
            path_pts.append([round(t0 + span * rr / nrows, 4), seq[0], yy])
            path_pts.append([round(t0 + span * (rr + 1) / nrows, 4), seq[1], yy])
        t0 += span

    tmap[~obj] = 2.0
    out = np.where(tmap > 1.5, 255, np.clip(np.round(tmap * 254), 0, 254)).astype(np.uint8)
    base = path[:-4]
    Image.fromarray(out, "L").save(base + ".trace.png")
    path_pts.sort(key=lambda p: p[0])
    if len(path_pts) > 800:
        path_pts = path_pts[:: len(path_pts) // 800 + 1] + [path_pts[-1]]
    json.dump({"width": W, "height": H, "outlineEnd": OUTLINE_END, "path": path_pts}, open(base + ".trace.json", "w"))
    return base, len(strokes), n


def preview(base, out, hand=None, frames=72):
    im = Image.open(base + ".png").convert("RGBA")
    tm = np.asarray(Image.open(base + ".trace.png"))
    path = json.load(open(base + ".trace.json"))["path"]
    W, H = im.size
    tmp = out + ".frames"
    os.makedirs(tmp, exist_ok=True)
    for f in range(frames + 12):
        p = min(1.0, f / frames)
        mask = (tm <= p * 254) & (tm < 255)
        a = np.asarray(im).copy()
        a[..., 3] = np.where(mask, a[..., 3], 0)
        fr = Image.new("RGB", (W + 200, H + 200), "#FCFCFA")
        fr.paste(Image.fromarray(a), (100, 100), Image.fromarray(a))
        if p < 1 and path:
            ts = [q[0] for q in path]
            i = min(range(len(ts)), key=lambda i: abs(ts[i] - p))
            x, y = path[i][1] + 100, path[i][2] + 100
            ImageDraw.Draw(fr).ellipse((x - 7, y - 7, x + 7, y + 7), fill="#E03E3E")
        fr.save(f"{tmp}/{f:04d}.png")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-framerate", "24", "-i", f"{tmp}/%04d.png",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-pix_fmt", "yuv420p", out], check=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    prev = None
    if "--preview" in args:
        i = args.index("--preview"); prev = args[i + 1]; del args[i:i + 2]
    for p in [a for a in args if not a.endswith(".trace.png")]:   # bỏ qua chính file trace khi dùng glob
        base, ns, nr = build(p)
        print(f"{os.path.basename(base)}: {ns} nét viền, {nr} vùng màu")
        if prev:
            preview(base, os.path.join(prev, os.path.basename(base) + ".mp4"))
