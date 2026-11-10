import numpy as np
def sheet_check(v, tile=64, min_valid=0.8):
    L, H, W = v.shape; c = L // 2
    contrasts, offsets = [], []
    for y in range(0, H - tile + 1, tile):
        for x in range(0, W - tile + 1, tile):
            t = v[:, y:y+tile, x:x+tile].astype(np.float32)
            if (t > 0).all(axis=0).mean() < min_valid: continue
            p = t.reshape(L, -1).mean(axis=1)
            contrasts.append((p.max() - p.min()) / p.mean()); offsets.append(int(p.argmax()) - c)
    contrasts, offsets = np.array(contrasts), np.array(offsets)
    return {"tiles": len(offsets), "contrast_median": round(float(np.median(contrasts)), 3),
            "peak_within3": round(float((np.abs(offsets) <= 3).mean()), 3),
            "peak_edge": round(float((np.abs(offsets) >= c - 1).mean()), 3),
            "offset_median": float(np.median(offsets)), "offsets": offsets}
