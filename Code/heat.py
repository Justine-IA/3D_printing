import numpy as np
import json
import gzip
import matplotlib.pyplot as plt
from scipy.spatial import KDTree
from geometry_analysis import analyze_geometry
from ABB_control import fetch_number_of_layer
import csv

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

def voxel_parameters(neighbor_temp, geom, nz, time_cooling):
    compactness = geom["compactness"]
    thickness = geom["avg_wall_thickness"]
    distance = geom["avg_distance"]
    density = geom["density"]
    gap = geom["max_internal_gap"]
    number_layer = nz

    alpha = (0.8 * compactness + 0.9 * (1 / (1 + thickness)) + 0.8 * density)*((number_layer+23)/25)
    beta = (0.03 + 0.01 * (1 - compactness) + 0.05 * (gap / 50.0))*(((time_cooling))**2) #for more realism divide cooling time by 10
    gamma = (1e-6 + 5e-6 * compactness + 1e-6 * (distance /50.0))*(((time_cooling))**1.05) #for more realism divide cooling time by 12

    return alpha, beta, gamma

def simulate_heat(voxel_data_path, nz, nx, ny,time_cooling,  T_init=20.0, T_amb=20.0, Q_val=660.0, dt=1.0, steps_per_layer=1):

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

                for rel_x, rel_y  in active_pixels:
                    y = bbox_min[1] + rel_y
                    x = bbox_min[0] + rel_x
                    if 0 <= x < nx and 0 <= y < ny:
                        local_T = T[z, y, x]
                        neighbor_T = get_voxel_neighbors(T, z, y, x)
                        averaged_T = 0.6 * local_T + 0.4 * neighbor_T

                        alpha, beta, gamma = voxel_parameters(neighbor_T, geometry_stats, nz, time_cooling)

                        T_new[z, y, x] += dt * heat_equation_ode(averaged_T, Q_val, T_amb, alpha, beta, gamma)

            T = T_new

    return T

def load_piece_bbox(piece_id, path_template="piece_{id}_bounding_boxes.json.gz"):
    """
    Load and return the JSON for one piece’s connected components.
    The JSON maps component‐labels → per‐layer bounding_box/active_pixels.+    """
    fname = path_template.format(id=piece_id)
    with gzip.open(fname, "rt") as f:
        return json.load(f)
    
def compute_piece_avg_temp(output, piece_bbox, mask_heatmap=False):
    """
    output: 3D array shape (nz, ny, nx)
    piece_bbox: dict mapping component_label(str) → layer dict,
                where layer dict maps str(z) → {
                  "bounding_box": [ [xmin,ymin], [xmax,ymax] ],
                  "active_pixels": [ [rel_x,rel_y], ... ]
                }
    """
    nz, ny, nx = output.shape
    mask = np.zeros_like(output, dtype=bool)

    # Walk each connected component, then each layer within it
    for comp_label, layers in piece_bbox.items():
        for z_str, layer_data in layers.items():
            z = int(z_str)
            bbox_min, _ = layer_data["bounding_box"]
            for rel_x, rel_y in layer_data["active_pixels"]:
                x = bbox_min[0] + rel_x
                y = bbox_min[1] + rel_y
                if 0 <= x < nx and 0 <= y < ny and 0 <= z < nz:
                    mask[z, y, x] = True

    # Gather only the temperatures for your piece’s voxels
    temps = output[mask]
    avg_temp = float(np.mean(temps)) if temps.size else 0.0

    if mask_heatmap:
        heatmap = np.zeros_like(output)
        heatmap[mask] = output[mask]
        return avg_temp, heatmap

    return avg_temp, None



def visualize_slice(T, z):
    plt.figure(figsize=(6, 6))
    plt.imshow(
        T[z].T,
        cmap="hot",
        origin="lower",      # so (0,0) is bottom-left
        interpolation="none",# no smoothing between pixels
        aspect="equal"       # square pixels
    )
    plt.title(f"Temperature, layer {z}")
    plt.colorbar(label="°C")
    plt.show()