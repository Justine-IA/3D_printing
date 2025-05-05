from collections import Counter
import numpy as np 
def filter_points_by_layer(deposition_points, layer_height, min_points=100):
    """
    Keeps only those points that fall into Z‐layers containing
    at least `min_points` points.
    """
    # Convert to array for easy slicing
    pts = np.array(deposition_points)
    z_min = pts[:, 2].min()
    # Compute integer layer index for each point
    layer_idxs = np.floor((pts[:, 2] - z_min) / layer_height).astype(int)
    # Count points per layer
    counts = Counter(layer_idxs)
    # Select only “valid” layers
    valid = {layer for layer, cnt in counts.items() if cnt >= min_points}
    print(f"Layer counts: {dict(counts)} → keeping layers {sorted(valid)}")
    # Filter
    mask = np.array([idx in valid for idx in layer_idxs])
    return pts[mask].tolist()