import numpy as np
from scipy.spatial import KDTree

def analyze_geometry(active_pixels, bbox_dims):
    if len(active_pixels) < 2:
        return {
            "avg_wall_thickness": 0,
            "avg_distance": 0,
            "bounding_box_area": 0,
            "filled_area": 0,
            "compactness": 0,
            "density": 0,
            "wall_count_estimate": 0,
            "max_internal_gap": 0,
        }

    coords = np.array(active_pixels)
    tree = KDTree(coords)
    dists, _ = tree.query(coords, k=6)  # 5 nearest neighbors + self
    wall_thickness = np.mean(dists[:, 1])  # skip self (0 distance)
    avg_distance = np.mean(dists[:, 1:])
    max_gap = np.max(dists[:, 1:])

    bbox_area = bbox_dims[0] * bbox_dims[1]
    filled_area = len(active_pixels)
    compactness = filled_area / bbox_area if bbox_area > 0 else 0
    density = filled_area / max(bbox_area, 1)

    return {
        "avg_wall_thickness": wall_thickness,
        "avg_distance": avg_distance,
        "bounding_box_area": bbox_area,
        "filled_area": filled_area,
        "compactness": compactness,
        "density": density,
        "wall_count_estimate": 1,
        "max_internal_gap": max_gap,
    }