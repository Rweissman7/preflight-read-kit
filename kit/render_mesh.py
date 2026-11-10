"""Render a tifxyz mesh into a surface volume (layers, height, width) for Reader V3 and the papyrus check.
Layer order and offsets match the team's published surface volumes: checked on PHerc0841 w00 and ag144
(9.366 um, 28 layers) and PHerc0800 (8.64 um, 31 layers): pixel correlation 0.96 to 0.975."""
import io, json, time
import numpy as np, tifffile, zarr, fsspec
from functools import lru_cache
from scipy.ndimage import map_coordinates

def read_tif(path):
    with fsspec.open(path, "rb") as f:
        return tifffile.imread(io.BytesIO(f.read()))

@lru_cache(maxsize=4)
def load_mesh(mesh_dir):
    X, Y, Z = [read_tif(f"{mesh_dir}/{a}.tif").astype(np.float64) for a in "xyz"]
    valid = (X > 0) & (Y > 0) & (Z > 0)
    P = np.stack([X, Y, Z], -1); P[~valid] = np.nan
    du, dv = np.gradient(P, axis=1), np.gradient(P, axis=0)
    N = np.cross(du, dv); N /= np.linalg.norm(N, axis=-1, keepdims=True)
    return P, N

def bilinear(G, r, c):
    h, w = G.shape[:2]
    r0 = np.clip(np.floor(r).astype(int), 0, h - 2); c0 = np.clip(np.floor(c).astype(int), 0, w - 2)
    fr = (r - r0)[..., None]; fc = (c - c0)[..., None]
    return (G[r0, c0] * (1 - fr) * (1 - fc) + G[r0 + 1, c0] * fr * (1 - fc)
            + G[r0, c0 + 1] * (1 - fr) * fc + G[r0 + 1, c0 + 1] * fr * fc)

def render_tile(mesh_dir, ct, scale, rows, cols, offsets, pad=4):
    P, N = load_mesh(mesh_dir)
    rr, cc = np.meshgrid(np.arange(*rows), np.arange(*cols), indexing="ij")
    p = bilinear(P, rr * scale, cc * scale); n = bilinear(N, rr * scale, cc * scale)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    ok = np.isfinite(p).all(-1) & np.isfinite(n).all(-1)
    L = len(offsets)
    if not ok.any():
        return np.zeros((L, rr.shape[0], rr.shape[1]), np.uint8)
    pts = p[..., None, :] + np.asarray(offsets)[None, None, :, None] * n[..., None, :]
    lo = np.maximum(np.floor(pts[ok].reshape(-1, 3).min(0)).astype(int) - pad, 0)
    hi = np.ceil(pts[ok].reshape(-1, 3).max(0)).astype(int) + pad
    block = np.asarray(ct[lo[2]:hi[2], lo[1]:hi[1], lo[0]:hi[0]], dtype=np.float32)
    q = np.nan_to_num(pts - lo, nan=-1)
    coords = np.stack([q[..., 2], q[..., 1], q[..., 0]]).reshape(3, -1)
    out = map_coordinates(block, coords, order=1, mode="constant", cval=0).reshape(pts.shape[:3])
    out[~ok] = 0
    return np.clip(np.rint(out), 0, 255).astype(np.uint8).transpose(2, 0, 1)

def render_mesh(mesh_dir, ct_url, out_zarr, layers=None, tile=512):
    meta = json.load(fsspec.open(f"{mesh_dir}/meta.json").open())
    scale = meta["scale"][0]
    if layers is None:   # match the team: 28 layers at 9.36 um, 31 at 8.64 um
        layers = 31 if abs(meta.get("voxel_size_um", 9.362) - 8.64) < 0.1 else 28
    P, _ = load_mesh(mesh_dir)
    H, W = int(round(P.shape[0] / scale)), int(round(P.shape[1] / scale))
    offs = (layers - 1) / 2 - np.arange(layers)
    ct = zarr.open(ct_url, mode="r")
    grp = zarr.open_group(out_zarr, mode="w")
    try:   # zarr 2
        arr = grp.create_dataset("0", shape=(layers, H, W), chunks=(layers, 128, 128), dtype="u1",
                                 compressor=None, fill_value=0)
    except TypeError:   # zarr 3
        arr = grp.create_array("0", shape=(layers, H, W), chunks=(layers, 128, 128), dtype="u1",
                               compressors=None, fill_value=0)
    t = time.time()
    for i in range(0, H, tile):
        for j in range(0, W, tile):
            r1, c1 = min(i + tile, H), min(j + tile, W)
            arr[:, i:r1, j:c1] = render_tile(mesh_dir, ct, scale, (i, r1), (j, c1), offs)
    print(f"rendered {out_zarr}: {arr.shape} in {time.time() - t:.0f}s")
    return out_zarr
