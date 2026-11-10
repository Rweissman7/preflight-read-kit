import argparse, json, os, subprocess, sys
import numpy as np, zarr
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tifffile
sys.path.insert(0, os.path.dirname(__file__))
from sheet_check import sheet_check
from direction import fr_ratio
from offset_map import red_map, map_summary, draw_red

MODEL = "/kaggle/working/models/reader-v3.pth"
# Pass lines = weakest known-good segment per scan type. 9.36 um from B5 (PHerc0841 w00, ag144, ag174).
# Other scan types are added to refs.json next to this file (8.64 um: set from the PHerc0009B controls).
REFS = {"9.36": {"contrast": 0.436, "peak": 0.248, "window": 0.328}}
REF_FILE = os.path.join(os.path.dirname(__file__), "refs.json")
if os.path.exists(REF_FILE):
    REFS.update(json.load(open(REF_FILE)))
WINDOWS = {"forward": (-6, 2), "reverse": (-2, 6)}   # window side follows reading direction

def open_vol(path):
    g = zarr.open(path, mode="r")
    return g["0"] if hasattr(g, "keys") and "0" in g else g

def stretch(img):
    img = img.astype(float)
    lo, hi = np.median(img), np.percentile(img, 99.5)
    return np.clip((img - lo) / max(hi - lo, 1e-9), 0, 1)

def window_share(o, lo, hi):
    return round(float(((o >= lo) & (o <= hi)).mean()), 3)

def readiness(s, direction, ref):
    return round(min(s["contrast_median"] / ref["contrast"],
                     s["peak_within3"] / ref["peak"],
                     s["window_" + direction] / ref["window"]), 3)

def score_avg(s, direction, ref):
    r = [s["contrast_median"] / ref["contrast"], s["peak_within3"] / ref["peak"],
         s["window_" + direction] / ref["window"]]
    return round(float(np.prod(r)) ** (1 / 3), 3)

FLOOR = 0.6   # any one number below 60% of its pass line still fails the surface
def verdict(avg, lowest):
    if lowest < FLOOR:
        return "FAIL"
    return "PASS" if avg >= 1.0 else ("BORDERLINE" if avg >= 0.9 else "FAIL")

ap = argparse.ArgumentParser()
ap.add_argument("--volume", required=True)
ap.add_argument("--name", required=True)
ap.add_argument("--source", choices=["published", "rendered"], default="published")
ap.add_argument("--out", default="/kaggle/working/reports")
ap.add_argument("--model", default=MODEL, help="ink model checkpoint (Reader V3 by default)")
ap.add_argument("--voxel-um", type=float, default=9.36, help="voxel size: picks the pass line and the cm2 numbers")
ap.add_argument("--force-read", action="store_true", help="read even when the verdict is FAIL (for checking the kit)")
ap.add_argument("--check-only", action="store_true", help="papyrus check, verdict and map only, no reading (works on CPU)")
a = ap.parse_args()

# 1. Data checks, and which pass line to use
arr = open_vol(a.volume)
comp = getattr(arr, "compressor", None) or getattr(arr, "compressors", None)
rep = {"name": a.name, "volume": a.volume, "shape": list(arr.shape),
       "dtype": str(arr.dtype), "compression": str(comp), "voxel_um": a.voxel_um}
rep["data_ok"] = rep["dtype"] in ("uint8", "uint16")
rep["kit_version"] = "0.1.1"
scan = min(REFS, key=lambda k: abs(float(k) - a.voxel_um))
if abs(float(scan) - a.voxel_um) > 0.3:
    rep["warning_ref"] = f"no pass line for {a.voxel_um} um scans yet: used the {scan} um one"
ref = REFS[scan]
rep["pass_line"] = {"scan_um": scan, **ref}

# 2. Direction first (it also decides the window side)
rep["direction"] = "forward" if a.source == "published" else "reverse"

# 3. Sheet check, window share both ways, scores, verdict
v = arr[:]
s = sheet_check(v)
offsets = s.pop("offsets")
for d, (lo, hi) in WINDOWS.items():
    s["window_" + d] = window_share(offsets, lo, hi)
rep["sheet"] = s
rep["readiness"] = readiness(s, rep["direction"], ref)   # score A: decides the verdict
rep["score_avg"] = score_avg(s, rep["direction"], ref)   # score B: saved for E5
rep["verdict"] = verdict(rep["score_avg"], rep["readiness"])
rep["rule"] = "B: average >= 1 PASS, >= 0.9 BORDERLINE; FAIL if any number < 0.6; direction fixed before reading"

other = "reverse" if rep["direction"] == "forward" else "forward"
if s["window_" + other] > s["window_" + rep["direction"]] + 0.05:
    rep["warning_papyrus"] = f"papyrus fits the {other} window better: check the direction"

# 3b. Offset map: where the surface sits outside the window (search +-7, smoothed 5x5)
m, dist = red_map(v, WINDOWS[rep["direction"]])
rep["map"] = map_summary(m, dist, voxel_um=a.voxel_um)   # score C numbers
MAP_FLOOR = 0.5   # less than half the page inside the window fails the surface
if rep["map"]["inside_window"] < MAP_FLOOR:
    rep["verdict"] = "FAIL"
    rep["map_fail"] = f"only {rep['map']['inside_window']:.0%} of the page is inside the readable window"

# 4. Read only if worth it (or forced), then check the direction with the ratio
os.makedirs(a.out, exist_ok=True)
stem = os.path.join(a.out, a.name)
if rep["data_ok"] and not a.check_only and (rep["verdict"] != "FAIL" or a.force_read):
    if rep["verdict"] == "FAIL":
        rep["forced_read"] = True
    subprocess.run([sys.executable, "-m", "koine_machines.inference.infer", a.volume, a.model,
                    stem + ".tif", "--overlap", "0.5", "--blend-mode", "hann",
                    "--direction", "both"], check=True)
    rep["ratio"] = fr_ratio(stem + ".tif", stem + "_reverse.tif")
    vals = list(rep["ratio"].values())
    evidence = "forward" if all(x > 1 for x in vals) else ("reverse" if all(x < 1 for x in vals) else None)
    rep["direction_rule"] = rep["direction"]
    rep["direction_evidence"] = evidence or "unclear"
    if evidence is None:
        rep["warning"] = "direction uncertain: ratio unclear, kept the rule"
        rep["next_step"] = ("map may be blank: run Diego's Ink Recoverability Protocol (IRP) to find out why, "
                            "https://github.com/dlescanogithub/vesuvius-inkcheck")
    elif evidence != rep["direction"]:
        rep["warning"] = (f"ink ratio says {evidence}, the rule says {rep['direction']}: kept {rep['direction']} "
                          "(the score never uses the other side). Check both maps by eye")
    # 5. Report image: forward, reverse, offset histogram, red map on the chosen direction
    fwd = stretch(tifffile.imread(stem + ".tif"))
    rev = stretch(tifffile.imread(stem + "_reverse.tif"))
    fig, ax = plt.subplots(1, 4, figsize=(24, 6))
    ax[0].imshow(fwd, cmap="gray"); ax[0].set_title("forward")
    ax[1].imshow(rev, cmap="gray"); ax[1].set_title("reverse")
    ax[2].hist(offsets, bins=range(-16, 17)); ax[2].set_title("papyrus offset (layers)")
    for x in ax[:2]: x.axis("off")
    draw_red(ax[3], fwd if rep["direction"] == "forward" else rev, dist)
    mp = rep["map"]
    ax[3].set_title(f"red = outside window: {mp['inside_window']:.0%} inside, "
                    f"biggest good area {mp['biggest_good_cm2']} cm2")
    forced = " (read anyway)" if rep.get("forced_read") else ""
    fig.suptitle(f"{a.name}: {rep['verdict']}{forced}, readiness {rep['readiness']}, {rep['direction']}")
    fig.savefig(stem + "_report.png", dpi=80, bbox_inches="tight")
else:
    rep["skipped"] = ("checked only, not read: run again without check_only (GPU on) to read it"
                      if a.check_only else "not read: data check or sheet check failed")

json.dump(rep, open(stem + "_report.json", "w"), indent=2)
print(json.dumps(rep, indent=2))
