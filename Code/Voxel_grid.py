import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label, binary_closing
import json
import gzip

# ---------------------------
# Function to map real-world coordinates to voxel indices using shift/scale
# ---------------------------
def point_to_voxel_indices(x, y, z, nx, ny, nz, x_min, y_min, z_min, x_range, y_range, z_range):
    ix = int(min(((x - x_min) / x_range) * nx, nx - 1))
    iy = int(min(((y - y_min) / y_range) * ny, ny - 1))
    iz = int(min(((z - z_min) / z_range) * nz, nz - 1))
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

# ---------------------------
# Main Voxel Processing Function
# ---------------------------
def process_voxel(deposition_points, nx=2000, ny=2000, nz=14, fill_radius=3):
    arr = np.array(deposition_points)
    x_min, x_max_data = arr[:,0].min(), arr[:,0].max()
    y_min, y_max_data = arr[:,1].min(), arr[:,1].max()
    z_min, z_max_data = arr[:,2].min(), arr[:,2].max()
    x_range = x_max_data - x_min
    y_range = y_max_data - y_min
    z_range = z_max_data - z_min

    print("Data bounds:")
    print(f"  X: {x_min} to {x_max_data} (range={x_range})")
    print(f"  Y: {y_min} to {y_max_data} (range={y_range})")
    print(f"  Z: {z_min} to {z_max_data} (range={z_range})")

    voxel_grid = np.zeros((nx, ny, nz), dtype=int)

    for point in deposition_points:
        x, y, z = point
        ix, iy, iz = point_to_voxel_indices(x, y, z, nx, ny, nz,
                                             x_min, y_min, z_min,
                                             x_range, y_range, z_range)
        fill_local_2d(voxel_grid, ix, iy, iz, radius=fill_radius)

    anisotropic_struct = np.ones((3, 3, 5), dtype=int)
    voxel_grid = binary_closing(voxel_grid, structure=anisotropic_struct).astype(int)
    voxel_grid = vertical_smoothing(voxel_grid, window=3)
    struct_2d = np.ones((3, 3), dtype=int)
    for z in range(1, nz - 1):
        slice_2d = voxel_grid[:, :, z]
        slice_closed = binary_closing(slice_2d, structure=struct_2d)
        voxel_grid[:, :, z] = slice_closed

    # # Optional: visualize a slice for debugging
    # slice_to_show = nz//2
    # plt.imshow(voxel_grid[:, :, slice_to_show], cmap='gray', origin='lower', extent=[0, nx, 0, ny])
    # plt.title(f'Voxel Slice {slice_to_show}')
    # plt.show()


    structure = np.ones((3, 3, 3))
    labeled_grid, num_features = label(voxel_grid, structure=structure)
    print("Number of printed pieces found (before merging):", num_features)

    labeled_grid, final_num_pieces = merge_all_components(labeled_grid, distance_threshold=100)
    print("Number of printed pieces after merging by centroid:", final_num_pieces)

    labeled_grid = relabel_components(labeled_grid)
    unique_labels = np.unique(labeled_grid)
    unique_labels = unique_labels[unique_labels != 0]
    final_num_pieces = len(unique_labels)
    print("Number of printed pieces after relabeling:", final_num_pieces)

    store_voxel_bounding_boxes(labeled_grid, voxel_dump="voxel_bounding_boxes.json.gz")

    return voxel_grid, labeled_grid, final_num_pieces
