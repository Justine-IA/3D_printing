import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label, binary_closing
import json
import gzip

# ---------------------------
# Function to map real-world coordinates to voxel indices using shift/scale
# ---------------------------
def point_to_voxel_indices(x, y, z,
                           nx, ny, nz,
                           x_min, y_min, z_min,
                           x_range, y_range, z_range,
                           layer_height=None):
    # X/Y unchanged
    fx = (x - x_min) / x_range if x_range > 0 else 0.0
    fy = (y - y_min) / y_range if y_range > 0 else 0.0
    ix = int(np.clip(fx * (nx - 1), 0, nx - 1))
    iy = int(np.clip(fy * (ny - 1), 0, ny - 1))

    # Z → slice by layer_height if given, else equal‐bin
    if layer_height is not None:
        iz = int(np.floor((z - z_min) / layer_height))
    else:
        fz = (z - z_min) / z_range if z_range > 0 else 0.0
        iz = fz * (nz - 1)
    iz = int(np.clip(iz, 0, nz - 1))

    return ix, iy, iz

# ---------------------------
# Local 2D Fill Function (thickens points in the same z-slice)
# ---------------------------
def fill_local_2d(voxel_grid, ix, iy, iz, radius=1):
    nx, ny, nz = voxel_grid.shape
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            x_idx = ix + dx
            y_idx = iy + dy
            if 0 <= x_idx < nx and 0 <= y_idx < ny:
                voxel_grid[x_idx, y_idx, iz] = 1

# ---------------------------
# Vertical Smoothing Function
# ---------------------------
def vertical_smoothing(voxel_grid, window=3):
    Nz = voxel_grid.shape[2]
    smoothed = np.copy(voxel_grid)
    for z in range(Nz):
        if z < window:
            window_slices = voxel_grid[:, :, 0:window]
        elif z >= Nz - window:
            window_slices = voxel_grid[:, :, Nz - window:Nz]
        else:
            offset = window // 2
            window_slices = voxel_grid[:, :, z - offset : z + offset + 1]
        threshold = window_slices.shape[2] // 2
        local_sum = np.sum(window_slices, axis=2)
        smoothed[:, :, z] = (local_sum >= threshold).astype(int)
    return smoothed

# ---------------------------
# Component Labeling and Merging
# ---------------------------
def compute_centroid(labeled_grid, label_val):
    indices = np.argwhere(labeled_grid == label_val)
    if indices.size == 0:
        return None
    return np.mean(indices, axis=0)

def merge_components_by_centroid(labeled_grid, distance_threshold):
    unique_labels = np.unique(labeled_grid)
    unique_labels = unique_labels[unique_labels != 0]
    merged = False
    for i in range(len(unique_labels)):
        for j in range(i + 1, len(unique_labels)):
            label_i = unique_labels[i]
            label_j = unique_labels[j]
            centroid_i = compute_centroid(labeled_grid, label_i)
            centroid_j = compute_centroid(labeled_grid, label_j)
            if centroid_i is None or centroid_j is None:
                continue
            distance = np.linalg.norm(centroid_i - centroid_j)
            if distance < distance_threshold:
                labeled_grid[labeled_grid == label_j] = label_i
                merged = True
    return labeled_grid, merged

def merge_all_components(labeled_grid, distance_threshold=50):
    merged = True
    while merged:
        labeled_grid, merged = merge_components_by_centroid(labeled_grid, distance_threshold)
    unique_labels = np.unique(labeled_grid)
    unique_labels = unique_labels[unique_labels != 0]
    return labeled_grid, len(unique_labels)

def relabel_components(labeled_grid):
    new_grid = np.copy(labeled_grid)
    unique_labels = np.unique(labeled_grid)
    mapping = {}
    new_label = 1
    for label_val in np.sort(unique_labels):
        if label_val == 0:
            mapping[label_val] = 0
        else:
            mapping[label_val] = new_label
            new_label += 1
    for old_val, new_val in mapping.items():
        new_grid[labeled_grid == old_val] = new_val
    return new_grid

# ---------------------------
# Store Bounding Boxes + Pixel Coordinates (no geometry analysis)
# ---------------------------
def store_voxel_bounding_boxes(labeled_grid, voxel_dump="voxel_bounding_boxes.json.gz"):
    bounding_data = {}
    unique_labels = np.unique(labeled_grid)
    unique_labels = unique_labels[unique_labels != 0]
    for label_val in unique_labels:
        indices = np.argwhere(labeled_grid == label_val)
        per_layer_voxels = {}
        for z in np.unique(indices[:, 2]):
            slice_inds = indices[indices[:, 2] == z][:, :2]
            if slice_inds.shape[0] == 0:
                continue
            min_xy = slice_inds.min(axis=0)
            max_xy = slice_inds.max(axis=0)
            rel_pixels = (slice_inds - min_xy).tolist()
            per_layer_voxels[int(z)] = {
                "bounding_box": [min_xy.tolist(), max_xy.tolist()],
                "active_pixels": rel_pixels
            }
        bounding_data[int(label_val)] = per_layer_voxels

    with gzip.open(voxel_dump, "wt") as f:
        json.dump(bounding_data, f, indent=2)
    print(f"Per-layer bounding boxes and pixel coordinates stored (gzipped) in {voxel_dump}")
    print()
    print()

# ---------------------------
# Main Voxel Processing Function
# ---------------------------

def process_voxel(deposition_points, nz, nx, ny, layer_height, fill_radius=3):
    arr = np.array(deposition_points)
    x_min, x_max = arr[:,0].min(), arr[:,0].max()
    y_min, y_max = arr[:,1].min(), arr[:,1].max()
    z_min, z_max = arr[:,2].min(), arr[:,2].max()
    x_range, y_range, z_range = x_max-x_min, y_max-y_min, z_max-z_min

    print("Data bounds:")
    print(f"  Z: {z_min:.4f} → {z_max:.4f}  (range={z_range:.4f})")

    voxel_grid = np.zeros((nx, ny, nz), dtype=int)
    for x, y, z in deposition_points:
        ix, iy, iz = point_to_voxel_indices(
            x, y, z, nx, ny, nz,
            x_min, y_min, z_min,
            x_range, y_range, z_range,
            layer_height=layer_height
        )
        fill_local_2d(voxel_grid, ix, iy, iz, radius=fill_radius)
    
    # DEBUG: which slices got any points?
    used_slices = np.unique([
        point_to_voxel_indices(x,y,z, nx,ny,nz,
                               x_min,y_min,z_min,
                               x_range,y_range,z_range, layer_height=layer_height)[2]
        for x,y,z in deposition_points
    ])
    print("→ actually used z‐slices:", used_slices)


        # 1) 3D labeling with a 3×3×3 connectivity
    struct3d = np.ones((3,3,3), dtype=bool)
    labeled_grid, initial_count = label(voxel_grid, structure=struct3d)
    print("  → initial components:", initial_count)

    # 2) merge nearby by centroid
    labeled_grid, merged_count = merge_all_components(
        labeled_grid,
        distance_threshold=100
    )
    print("  → after centroid-merge:", merged_count)

    # 3) relabel to 1…N
    labeled_grid = relabel_components(labeled_grid)
    final_labels = np.unique(labeled_grid)
    final_labels = final_labels[final_labels != 0]
    final_count = len(final_labels)
    print("  → final pieces:", final_count)

    # 4) store per-piece bounding boxes
    store_voxel_bounding_boxes(
        labeled_grid,
        voxel_dump="voxel_bounding_boxes.json.gz"
    )


    return voxel_grid, labeled_grid, final_count



def show_slices(voxel_grid):
    nz = voxel_grid.shape[2]
    for z in range(nz):
        plt.figure(figsize=(4,4))
        plt.imshow(voxel_grid[:, :, z], 
                   cmap='gray', 
                   origin='lower', 
                   interpolation='nearest')
        plt.title(f'Slice {z}')
        plt.axis('off')
        plt.show()


