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



    return voxel_grid


def save_bounding_boxes_from_grid(voxel_grid, piece_id):
    """
    Given a boolean 3D grid for one piece, do one label() and
    dump the bboxes to piece_{piece_id}_bounding_boxes.json.gz.
    """


    struct3d = np.ones((3,3,3), dtype=bool)
    labeled, n = label(voxel_grid, structure=struct3d)
    print(f"[Voxel_grid] piece {piece_id}: found {n} blob(s)")

    bbox_path = f"piece_{piece_id}_bounding_boxes.json.gz"
    store_voxel_bounding_boxes(labeled, voxel_dump=bbox_path)
    print(f"[Voxel_grid] piece {piece_id}: saved bboxes → {bbox_path}")
    print()
    print()
    return labeled, bbox_path



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