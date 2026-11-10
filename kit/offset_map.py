import warnings
import numpy as np
from scipy.ndimage import generic_filter, label

def red_map(v, window, tile=64, search=7, min_valid=0.8):
    """Papyrus offset per tile (searched near the middle), smoothed, then layers outside the window."""
    L, H, W = v.shape
    c = L // 2
    lo_s, hi_s = max(c - search, 0), min(c + search + 1, L)
    m = np.full((H // tile, W // tile), np.nan)
    for i in range(H // tile):
        for j in range(W // tile):
            t = v[:, i*tile:(i+1)*tile, j*tile:(j+1)*tile].astype(np.float32)
            if (t > 0).all(axis=0).mean() < min_valid:
                continue
            p = t.reshape(L, -1).mean(axis=1)
            m[i, j] = lo_s + int(p[lo_s:hi_s].argmax()) - c
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sm = generic_filter(m, np.nanmedian, size=5, mode="constant", cval=np.nan)
    sm[np.isnan(m)] = np.nan
    lo_w, hi_w = window
    dist = np.maximum(np.maximum(lo_w - sm, sm - hi_w), 0)
    return m, dist

def map_summary(m, dist, tile=64, search=7, voxel_um=9.36):
    ok = np.isfinite(dist)
    good = ok & (dist == 0)
    lab, n = label(good)
    tile_cm2 = (tile * voxel_um * 1e-4) ** 2
    biggest = int(np.bincount(lab.ravel())[1:].max()) if n else 0
    return {"inside_window": round(float(good.sum() / max(ok.sum(), 1)), 3),
            "measured_cm2": round(float(ok.sum() * tile_cm2), 2),
            "biggest_good_cm2": round(biggest * tile_cm2, 2),
            "good_pieces": int(n),
            "search_edge": round(float((np.abs(m[ok]) >= search).mean()), 3)}

def draw_red(ax, ink, dist, tile=64, step=4):
    """Ink map in gray with strong red where the surface is outside the window (shown at 1/step size)."""
    ink = ink[::step, ::step]
    t = tile // step
    dpx = np.full(ink.shape, np.nan, dtype=np.float32)
    h, w = min(ink.shape[0], dist.shape[0] * t), min(ink.shape[1], dist.shape[1] * t)
    dpx[:h, :w] = np.kron(dist, np.ones((t, t)))[:h, :w]
    d = np.nan_to_num(dpx)
    ax.imshow(ink * 0.75, cmap="gray", vmin=0, vmax=1)
    ov = np.zeros(d.shape + (4,), dtype=np.float32)
    ov[..., 0] = 1.0; ov[..., 1] = 0.05; ov[..., 2] = 0.05
    ov[..., 3] = np.where(d >= 1, 0.55 + 0.35 * np.clip((d - 1) / 5, 0, 1), 0)
    ax.imshow(ov); ax.axis("off")
