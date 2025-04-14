import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label, binary_closing, binary_dilation, binary_erosion
import json

# Load deposition points from file
with open("deposition_points.json", "r") as f:
    deposition_points = json.load(f)

print(f"Loaded {len(deposition_points)} deposition points")

# 2. Function to map real-world coordinates to voxel indices using shift/scale
def point_to_voxel_indices(x, y, z, nx, ny, nz, x_min, y_min, z_min, x_range, y_range, z_range):
    ix = int(min(((x - x_min) / x_range) * nx, nx - 1))
    iy = int(min(((y - y_min) / y_range) * ny, ny - 1))
    iz = int(min(((z - z_min) / z_range) * nz, nz - 1))
    return ix, iy, iz

# 3. Local 2D Fill Function
def fill_local_2d(voxel_grid, ix, iy, iz, radius=1):
    """
    Fills a local neighborhood around voxel (ix, iy, iz) on the same z-slice.
    For radius=1, fills a 3x3 block; for radius=3, fills a 7x7 block.
    """
    nx, ny, nz = voxel_grid.shape
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            x_idx = ix + dx
            y_idx = iy + dy
            if 0 <= x_idx < nx and 0 <= y_idx < ny:
                voxel_grid[x_idx, y_idx, iz] = 1

# 6. Modified Vertical Smoothing Function
def vertical_smoothing(voxel_grid, window=3):
    """
    Applies majority-vote smoothing across z-slices to enforce vertical continuity.
    For extreme slices, uses a fixed window from the top or bottom.
    
    Parameters:
        voxel_grid: 3D numpy array of the voxel grid.
        window: Number of slices to use in the smoothing window.
                For example, window=3 uses 3 consecutive slices.
                
    Returns:
        A new voxel grid after vertical smoothing.
    """
    Nz = voxel_grid.shape[2]
    smoothed = np.copy(voxel_grid)
    
    # For each slice, choose the window as follows:
    # - For slices near the top (z < window), use slices 0 to window-1.
    # - For slices near the bottom (z >= Nz - window), use the last "window" slices.
    # - Otherwise, use a centered window (z-window//2 to z+window//2).
    for z in range(Nz):
        if z < window:
            # Extreme top: use the first 'window' slices
            window_slices = voxel_grid[:, :, 0:window]
        elif z >= Nz - window:
            # Extreme bottom: use the last 'window' slices
            window_slices = voxel_grid[:, :, Nz - window:Nz]
        else:
            offset = window // 2
            window_slices = voxel_grid[:, :, z - offset : z + offset + 1]
        
        # Use a majority vote in the window (threshold = half the window size)
        threshold = window_slices.shape[2] // 2
        local_sum = np.sum(window_slices, axis=2)
        smoothed[:, :, z] = (local_sum >= threshold).astype(int)
    
    return smoothed

# 1. Define the Build Volume and Voxel Grid
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

# Define voxel grid resolution (for example, 2000x2000 in-plane and 14 slices)
nx, ny, nz = 2000, 2000, 14
voxel_grid = np.zeros((nx, ny, nz), dtype=int)


# 4. Fill the Voxel Grid from Deposition Points using local 2D fill
for point in deposition_points:
    x, y, z = point
    ix, iy, iz = point_to_voxel_indices(x, y, z, nx, ny, nz,
                                         x_min, y_min, z_min,
                                         x_range, y_range, z_range)
    # Replace the single-voxel set with a local 2D fill.
    fill_local_2d(voxel_grid, ix, iy, iz, radius=3)

# 5. Apply Morphological Operations
# Apply an anisotropic closing: 3x3 in-plane and 5 voxels deep in z.
anisotropic_struct = np.ones((3, 3, 5), dtype=int)
voxel_grid = binary_closing(voxel_grid, structure=anisotropic_struct).astype(int)


# Apply vertical smoothing (try window=3; adjust as needed)
voxel_grid = vertical_smoothing(voxel_grid, window=3)

# 7. Additionally, Apply a Gentle 2D Morphological Closing on Each Slice
struct_2d = np.ones((3, 3), dtype=int)  # 3x3 structure for 2D closing
for z in range(voxel_grid.shape[2]):
    slice_2d = voxel_grid[:, :, z]
    slice_closed = binary_closing(slice_2d, structure=struct_2d)
    voxel_grid[:, :, z] = slice_closed

# 8. Visualize a 2D Slice of the Voxel Grid
slice_index = 13
plt.imshow(voxel_grid[:, :, slice_index], cmap='gray', origin='lower',
           extent=[0, nx, 0, ny])
plt.title(f'Voxel Grid Slice at z-index {slice_index}')
plt.xlabel('Voxel X')
plt.ylabel('Voxel Y')
plt.colorbar(label='Filled (1) or Empty (0)')
plt.show()

# 9. Segment the Voxel Grid Using 3D Connected Components (26-neighbor connectivity)
structure = np.ones((3, 3, 3))
labeled_grid, num_features = label(voxel_grid, structure=structure)
print("Number of printed pieces found (before filtering):", num_features)

# 10. Function to Convert Voxel Indices Back to Real-World Coordinates
def voxel_to_real(ix, iy, iz, nx, ny, nz, x_min, y_min, z_min, x_range, y_range, z_range):
    x = x_min + (ix / nx) * x_range
    y = y_min + (iy / ny) * y_range
    z = z_min + (iz / nz) * z_range
    return [x, y, z]
