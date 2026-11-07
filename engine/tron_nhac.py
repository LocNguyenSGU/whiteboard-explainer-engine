"""Trộn nhạc nền THEO ĐOẠN thành một file music.wav dài đúng bằng video (khuôn "giải thích sự kiện", 0019).

Không phải một bài chạy một lèo: mỗi đoạn (thường = một chương) một bài, chuyển bài bằng tắt dần/lên dần, có chỗ tắt hẳn,
tự hạ nhạc khi có giọng.

Gọi từ khuon/dung.py khi storyboard có `nhac:` là danh sách (xem khuon/README.md):
  nhac:
    - {bai: incompetech/Investigations.mp3, tu: s1, muc: -20}       # tu: id cảnh | "cụm chữ" | số giây
    - {bai: incompetech/Hypnothis.mp3, tu: s5, bat_dau_bai: 30}     # bat_dau_bai: bắt đầu từ giây 30 của bài
    - {tat: true, tu: s9}                                            # tắt hẳn nhạc từ cảnh s9 (tới đoạn sau)
Tham số mỗi đoạn: muc (dB nhạc so với GIỌNG ở chỗ ngắt câu, mặc định -17), ha (dB hạ thêm khi có giọng, mặc định 7,3)
— hiệu chỉnh sao cho đo bằng CÙNG THƯỚC với mẫu (tách demucs rồi đo) ra đúng số của mẫu (phong-cach/minh-van-dap/am-thanh.md:
demucs phóng đại độ hạ ~3 dB); đoạn "hơi thở" dùng muc ≈ -27,
vao / ra (giây lên dần / tắt dần, mặc định 1,5 / 1,5). Bài ngắn hơn đoạn thì lặp (nối bằng mờ chéo 2 s).

Dùng tay:  .venv/bin/python pipeline/tron_nhac.py <cues.json> <voice.wav> <ra.wav> <tổng giây>
  cues.json: [{bai: đường dẫn, tu: giây, den: giây, muc, ha, vao, ra, bat_dau_bai}, …] (đã quy ra giây)
"""
import json, os, subprocess, sys
import numpy as np

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NHAC_DIR = os.path.join(ROOT, "studio", "public", "common", "nhac")


def doc_am(path, sr=SR):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()


def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)


def duong_bao_giong(voice, sr=SR):
    """0..1 mỗi mẫu: 1 = đang có giọng. Bắt nhanh (60 ms), nhả 250 ms: nhạc kịp nổi ở chỗ ngắt câu như mẫu, không nhấp nhô giữa chữ."""
    mono = np.abs(voice).mean(1) if voice.ndim == 2 else np.abs(voice)
    k = int(0.02 * sr)
    n = len(mono) // k
    e = 20 * np.log10(np.sqrt((mono[: n * k].reshape(n, k) ** 2).mean(1)) + 1e-9)
    nguong = np.percentile(e, 90) - 24
    on = (e > nguong).astype(float)
    out, cur = np.zeros(n), 0.0
    a_len, r_len = 0.02 / 0.06, 0.02 / 0.25
    for i, x in enumerate(on):
        cur = cur + (x - cur) * (a_len if x > cur else r_len)
        out[i] = cur
    bao = np.repeat(out, k)
    bao = np.pad(bao, (0, max(0, len(mono) - len(bao))), mode="edge")[: len(mono)]     # phần lẻ cuối < 20 ms
    return bao, float(np.median(e[on > 0])) if on.any() else -20.0


def muc_giong_nhu_mau(voice, sr=SR):
    """Mức giọng đo ĐÚNG cách phan_tich_am_thanh.py đo mẫu (khung 0,1 s, trung vị các khung > p90 − 22 dB),
    để "nhạc thấp hơn giọng X dB" của mình so được với số của mẫu."""
    mono = voice.mean(1) if voice.ndim == 2 else voice
    k = sr // 10
    n = len(mono) // k
    e = 20 * np.log10(np.sqrt((mono[: n * k].reshape(n, k) ** 2).mean(1)) + 1e-9)
    on = e > np.percentile(e, 90) - 22
    return float(np.median(e[on])), np.repeat(on, k)


def lap_bai(bai, dai, bat_dau=0.0, mo_cheo=2.0):
    """Cắt bài từ bat_dau, lặp nếu ngắn hơn `dai` mẫu (mờ chéo `mo_cheo` giây ở chỗ nối)."""
    x = bai[int(bat_dau * SR):]
    if len(x) >= dai:
        return x[:dai]
    c = int(mo_cheo * SR)
    out = x.copy()
    while len(out) < dai:
        nx = bai
        f = np.linspace(0, 1, c)[:, None]
        out[-c:] = out[-c:] * (1 - f) + nx[:c] * f
        out = np.concatenate([out, nx[c:]])
    return out[:dai]


def tron(cues, voice_path, ra, tong):
    voice = doc_am(voice_path)
    n = int(tong * SR)
    if len(voice) < n:
        voice = np.pad(voice, ((0, n - len(voice)), (0, 0)))
    bao, _ = duong_bao_giong(voice[:n])
    giong_db, co_giong = muc_giong_nhu_mau(voice[:n])
    co_giong = np.pad(co_giong, (0, max(0, n - len(co_giong))))[:n]
    out = np.zeros((n, 2), np.float32)
    do = []
    for c in cues:
        if c.get("tat") or not c.get("bai"):
            continue
        a, b = int(c["tu"] * SR), min(n, int(c["den"] * SR))
        vao, ra_ = int(c.get("vao", 1.5) * SR), int(c.get("ra", 1.5) * SR)
        b2 = min(n, b + ra_)                         # tắt dần tràn sang đầu đoạn sau = mờ chéo với bài sau
        if b2 <= a:
            continue
        p = c["bai"] if os.path.isabs(c["bai"]) else os.path.join(NHAC_DIR, c["bai"])
        bai = doc_am(p)
        seg = lap_bai(bai, b2 - a, c.get("bat_dau_bai", 0.0))
        seg = seg / (10 ** (rms_db(bai[int(c.get("bat_dau_bai", 0) * SR):][: 60 * SR]) / 20))     # chuẩn mức bài ≈ 0 dB RMS
        g = np.ones(b2 - a)
        g[:vao] = np.linspace(0, 1, min(vao, len(g)))[: len(g[:vao])]
        if b2 > b:
            g[b - a:] = np.linspace(1, 0, b2 - b)
        # Đích đo ĐÚNG cách đo mẫu (trung vị khung 0,1 s): ở chỗ không giọng nhạc = giọng + muc; lúc có giọng thấp hơn thêm `ha`.
        # Độ hạ thực tế phụ thuộc nhịp ngắt câu (nhạc lên lại cần thời gian) nên tự dò độ sâu hạ cho tới khi đo ra đúng `ha`.
        dich_muc, dich_ha = giong_db + c.get("muc", -17), c.get("ha", 7.3)
        mono = seg.mean(1) * g
        k = SR // 10
        nk = len(mono) // k
        cg = co_giong[a:a + nk * k].reshape(nk, k).mean(1) > 0.5
        du = (g[: nk * k].reshape(nk, k).min(1) >= 0.999)              # bỏ khung đang lên / tắt dần

        def do(sau):
            dk = 1 - (1 - 10 ** (-sau / 20)) * bao[a:a + nk * k]
            e = 20 * np.log10(np.sqrt(((mono[: nk * k] * dk) .reshape(nk, k) ** 2).mean(1)) + 1e-9)
            lg = np.median(e[~cg & du]) if (~cg & du).sum() > 10 else None
            lv = np.median(e[cg & du]) if (cg & du).sum() > 10 else None
            return lg, lv

        sau = dich_ha
        for _ in range(4):
            lg, lv = do(sau)
            if lg is None or lv is None:
                break
            sau = float(np.clip(sau + dich_ha - (lg - lv), 0, 30))
        lg, _ = do(sau)
        tang = 10 ** ((dich_muc - lg) / 20) if lg is not None else 10 ** ((giong_db + c.get("muc", -17)) / 20)
        duck = 1 - (1 - 10 ** (-sau / 20)) * bao[a:b2]
        x = seg * (g * tang * duck)[:, None]
        out[a:b2] += x.astype(np.float32)
    peak = np.abs(out).max()
    if peak > 0.98:
        out *= 0.98 / peak
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", ra], input=out.tobytes(), check=True)
    return {"giong_db": round(giong_db, 1), "so_doan": sum(1 for c in cues if c.get("bai") and not c.get("tat"))}


if __name__ == "__main__":
    cues = json.load(open(sys.argv[1]))
    print(tron(cues, sys.argv[2], sys.argv[3], float(sys.argv[4])))
