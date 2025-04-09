import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label, binary_closing
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
nx, ny, nz = 500,500,50
voxel_grid = np.zeros((nx, ny, nz), dtype=int)

# Function to map real-world coordinates to voxel indices using shift/scale
def point_to_voxel_indices(x, y, z, nx, ny, nz, x_min, y_min, z_min, x_range, y_range, z_range):
    ix = int(min(((x - x_min) / x_range) * nx, nx - 1))
    iy = int(min(((y - y_min) / y_range) * ny, ny - 1))
    iz = int(min(((z - z_min) / z_range) * nz, nz - 1))
    return ix, iy, iz




# 3. Fill the Voxel Grid from Deposition Points

for point in deposition_points:
    x, y, z = point
    ix, iy, iz = point_to_voxel_indices(x, y, z, nx, ny, nz, x_min, y_min, z_min, x_range, y_range, z_range)
    voxel_grid[ix, iy, iz] = 1

voxel_grid = binary_closing(voxel_grid, structure=np.ones((2,2,2))).astype(int)

# # Example 2D anisotropic struct: merges horizontally more than vertically
# struct_2d = np.ones((2, 3,2), dtype=int)  
# # For 3D, you might shape it like (1,3,1) or (3,1,1), etc.

# voxel_grid = binary_closing(voxel_grid, structure=struct_2d).astype(int)


# 4. Visualize a 2D Slice of the Voxel Grid

# Visualize a 2D slice of the voxel grid (choose a slice that seems to contain points)
slice_index = nz // 2
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
