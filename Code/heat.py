import numpy as np
import json
import gzip
import matplotlib.pyplot as plt
from scipy.spatial import KDTree


def load_voxel_data(gz_file):
    with gzip.open(gz_file, "rt") as f:
        return json.load(f)

def heat_equation_ode(T, Q, T_amb, alpha, beta, gamma):
    return alpha * Q - beta * (T - T_amb) - gamma * (T**4 - T_amb)

def get_voxel_neighbors(temp_grid, z, y, x):
    offsets = [(dz, dy, dx) for dz in [0] for dy in [-1, 0, 1] for dx in [-1, 0, 1] if not (dy == 0 and dx == 0)]
    neighbors = [
        temp_grid[z+dz, y+dy, x+dx]
        for dz, dy, dx in offsets
        if 0 <= z+dz < temp_grid.shape[0] and 0 <= y+dy < temp_grid.shape[1] and 0 <= x+dx < temp_grid.shape[2]
    ]
    return np.mean(neighbors) if neighbors else temp_grid[z, y, x]

def voxel_parameters(neighbor_temp, geom):
    compactness = geom["compactness"]
    thickness = geom["avg_wall_thickness"]
    distance = geom["avg_distance"]
    density = geom["density"]
    gap = geom["max_internal_gap"]

    alpha = 0.4 * compactness + 0.5 * (1 / (1 + thickness)) + 0.9 * density
    beta = 0.002 + 0.003 * (1 - compactness) + 0.001 * (gap / 50.0)
    gamma = 1e-8 + 5e-8 * compactness + 1e-8 * (distance / 10.0)

    return alpha, beta, gamma

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

def simulate_heat(voxel_data_path, nz=14, nx=2000, ny=2000, T_init=20.0, T_amb=20.0, Q_val=660.0, dt=1.0, steps_per_layer=1):
    voxel_data = load_voxel_data(voxel_data_path)
    T = np.full((nz, ny, nx), T_init, dtype=np.float64)

    for z in range(nz):
        for _ in range(steps_per_layer):
            T_new = T.copy()
            for piece_id, layers in voxel_data.items():
                if str(z) not in layers:
                    continue
                layer_data = layers[str(z)]
                bbox_min = layer_data["bounding_box"][0]
                bbox_max = layer_data["bounding_box"][1]
                bbox_dims = [bbox_max[0] - bbox_min[0] + 1, bbox_max[1] - bbox_min[1] + 1]
                active_pixels = layer_data["active_pixels"]

                geometry_stats = analyze_geometry(active_pixels, bbox_dims)

                for rel_y, rel_x in active_pixels:
                    y = bbox_min[1] + rel_y
                    x = bbox_min[0] + rel_x
                    if 0 <= x < nx and 0 <= y < ny:
                        local_T = T[z, y, x]
                        neighbor_T = get_voxel_neighbors(T, z, y, x)
                        averaged_T = 0.6 * local_T + 0.4 * neighbor_T

                        alpha, beta, gamma = voxel_parameters(neighbor_T, geometry_stats)

                        T_new[z, y, x] += dt * heat_equation_ode(averaged_T, Q_val, T_amb, alpha, beta, gamma)

            T = T_new

    return T

def visualize_slice(T, z):
    plt.figure(figsize=(6, 6))
    plt.imshow(T[z], cmap="hot")
    plt.title(f"Voxel Slice {z}")
    plt.colorbar(label="Temperature (°C")
    plt.show()

if __name__ == "__main__":
    output = simulate_heat("voxel_bounding_boxes.json.gz")
    visualize_slice(output, z=0)
