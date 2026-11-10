import tifffile

def fr_ratio(forward_path, reverse_path, thresholds=(128, 153, 179)):
    """How much more 'ink' the forward map finds than the reverse map (capped at 100)."""
    f = tifffile.imread(forward_path)
    r = tifffile.imread(reverse_path)
    valid = (f > 0) | (r > 0)
    out = {}
    for t in thresholds:
        fa = ((f >= t) & valid).mean()
        ra = ((r >= t) & valid).mean()
        out[str(t)] = round(min(float(fa / max(ra, 1e-9)), 100.0), 2)
    return out
