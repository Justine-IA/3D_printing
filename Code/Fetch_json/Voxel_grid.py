import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label, binary_closing, binary_dilation, binary_erosion
import json

with open("deposition_points.json", "r") as f:
    deposition_points = json.load(f)

print(f"Loaded {len(deposition_points)} deposition points")
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


# Use a coarser grid resolution to merge nearby points
# Define voxel grid resolution
nx, ny, nz = 2000,2000,14
voxel_grid = np.zeros((nx, ny, nz), dtype=int)

# Function to map real-world coordinates to voxel indices using shift/scale
def point_to_voxel_indices(x, y, z, nx, ny, nz, x_min, y_min, z_min, x_range, y_range, z_range):
    ix = int(min(((x - x_min) / x_range) * nx, nx - 1))
    iy = int(min(((y - y_min) / y_range) * ny, ny - 1))
    iz = int(min(((z - z_min) / z_range) * nz, nz - 1))
    return ix, iy, iz


# 3. Fill the Voxel Grid from Deposition Points
def fill_local_2d(voxel_grid, ix, iy, iz, radius=1):
    """
    Fills a local neighborhood around voxel (ix, iy, iz) in the same z slice.
    For radius=1, fills a 3x3 block.
    """
    nx, ny, nz = voxel_grid.shape
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            x_idx = ix + dx
            y_idx = iy + dy
            if 0 <= x_idx < nx and 0 <= y_idx < ny:
                voxel_grid[x_idx, y_idx, iz] = 1

# 3. Fill the Voxel Grid from Deposition Points using local 2D fill
for point in deposition_points:
    x, y, z = point
    ix, iy, iz = point_to_voxel_indices(x, y, z, nx, ny, nz, x_min, y_min, z_min, x_range, y_range, z_range)
    #voxel_grid[ix,iy,iz] = 1
    fill_local_2d(voxel_grid, ix, iy, iz, radius=3)


# voxel_grid = binary_closing(voxel_grid, structure=np.ones((2,2,2))).astype(int)
anisotropic_struct = np.ones((3,3, 5), dtype=int) # 3 3 5 best for now
voxel_grid = binary_closing(voxel_grid, structure=anisotropic_struct).astype(int)

def vertical_smoothing(voxel_grid, window=3):
    # A majority-vote smoothing across z-slices to enforce vertical continuity.
    Nz = voxel_grid.shape[2]
    smoothed = np.copy(voxel_grid)
    offset = window // 2
    for z in range(Nz):
        lower = max(z - offset, 0)
        upper = min(z + offset + 1, Nz)
        # Sum over the window of slices
        local_sum = np.sum(voxel_grid[:, :, lower:upper], axis=2)
        # If more than half of the slices in the window are filled, set current slice filled.
        smoothed[:, :, z] = (local_sum > (window // 2)).astype(int)
    return smoothed

# Uncomment the next line to apply vertical smoothing:
voxel_grid = vertical_smoothing(voxel_grid, window=2)


# 4. Visualize a 2D Slice of the Voxel Grid

# Visualize a 2D slice of the voxel grid (choose a slice that seems to contain points)
slice_index = 13
plt.imshow(voxel_grid[:, :, slice_index], cmap='gray', origin='lower',
           extent=[0, nx, 0, ny])
plt.title(f'Voxel Grid Slice at z-index {slice_index}')
plt.xlabel('Voxel X')
plt.ylabel('Voxel Y')
plt.colorbar(label='Filled (1) or Empty (0)')
plt.show()

# Segment the voxel grid using 3D connected components (26-neighbor connectivity)
structure = np.ones((3, 3, 3))
labeled_grid, num_features = label(voxel_grid, structure=structure)
print("Number of printed pieces found (before filtering):", num_features)

# Function to convert voxel indices back to real-world coordinates
def voxel_to_real(ix, iy, iz, nx, ny, nz, x_min, y_min, z_min, x_range, y_range, z_range):
    x = x_min + (ix / nx) * x_range
    y = y_min + (iy / ny) * y_range
    z = z_min + (iz / nz) * z_range
    return [x, y, z]
