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

def voxel_parameters(neighbor_temp, geom, nz):
    compactness = geom["compactness"]
    thickness = geom["avg_wall_thickness"]
    distance = geom["avg_distance"]
    density = geom["density"]
    gap = geom["max_internal_gap"]
    number_layer = nz

    alpha = (0.4 * compactness + 0.5 * (1 / (1 + thickness)) + 0.9 * density)*(number_layer*0.5)
    beta = 0.002 + 0.003 * (1 - compactness) + 0.001 * (gap / 50.0)
    gamma = 1e-8 + 5e-8 * compactness + 1e-8 * (distance / 10.0)

    return alpha, beta, gamma

def simulate_heat(voxel_data_path, nz, nx, ny, T_init=20.0, T_amb=20.0, Q_val=660.0, dt=1.0, steps_per_layer=1):
    print("Starting the simulation of the heat")
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

                        alpha, beta, gamma = voxel_parameters(neighbor_T, geometry_stats, nz)

                        T_new[z, y, x] += dt * heat_equation_ode(averaged_T, Q_val, T_amb, alpha, beta, gamma)

            T = T_new

    return T


def step_heat(T, voxel_data, active_layer, Q_val, T_amb, dt,nx,ny):
    """
    Advance T by dt seconds.
    Only voxels in `active_layer` get the Q_val heating; the rest just cool + diffuse.
    """
    nz, ny, nx = T.shape
    T_new = T.copy()

    # loop exactly like your simulate_heat inner loop
    for piece_id, layers in voxel_data.items():
        for z_str, info in layers.items():
            z = int(z_str)
            bb_min, _ = info["bounding_box"]
            active_pixels = info["active_pixels"]

            # skip this piece if it's not the active_layer and we're heating
            is_heating_layer = (active_layer == z)

            # precompute geometry once per layer
            geom = analyze_geometry(active_pixels,
                      [info["bounding_box"][1][0] - bb_min[0] + 1,
                       info["bounding_box"][1][1] - bb_min[1] + 1])

            for rel_y, rel_x in active_pixels:
                y = bb_min[1] + rel_y
                x = bb_min[0] + rel_x
                if not (0 <= x < nx and 0 <= y < ny):
                   continue

                # conduction: average 8 neighbors in the same slice
                neighs = []
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        if dx==0 and dy==0: continue
                        yy, xx = y+dy, x+dx
                        if 0 <= yy < ny and 0 <= xx < nx:
                            neighs.append(T[z, yy, xx])
                neighbor_T = np.mean(neighs) if neighs else T[z,y,x]

                # mix local+neighbor
                avgT = 0.6 * T[z,y,x] + 0.4 * neighbor_T

                # decide heat input: Q_val on this layer, 0 otherwise
                Q = Q_val if is_heating_layer else 0.0

                # your alpha/beta/gamma
                α, β, γ = voxel_parameters(neighbor_T, geom)

                # ODE step
                dT = α*Q - β*(avgT - T_amb) - γ*(avgT**4 - T_amb)
                T_new[z, y, x] += dt * dT

    return T_new



def run_real_time_simulation(voxel_data_path,
                             nz, nx, ny,
                             dt, print_time, cool_time,
                             Q_val, T_init, T_amb):
    # load your voxel bounding boxes once
    with gzip.open(voxel_data_path, "rt") as f:
        voxel_data = json.load(f)

    # initialize the field once
    T = np.full((nz, ny, nx), T_init, dtype=float)

    # compute how many steps to do for each phase
    n_print = int(print_time / dt)
    n_cool  = int(cool_time  / dt)

    # loop over layers
    for z in range(nz):
        # 1) HEATING PHASE: heat layer z for print_time seconds
        for _ in range(n_print):
            T = step_heat(T, voxel_data, z, Q_val, T_amb, dt, nx, ny)

        # 2) COOLING PHASE: no heating for cool_time seconds
        for _ in range(n_cool):
            T = step_heat(T, voxel_data, None, 0.0, T_amb, dt, nx, ny)

    return T




def export_pixel_temperatures(T, voxel_data_path, out_csv="piece_pixel_temps.csv"):
    """
    Given the 3D temperature array T[z,y,x] and the voxel dump,
    writes out CSV rows: piece_id, z, x, y, temperature
    """
    # 1) load your bounding-box + active_pixels info
    with gzip.open(voxel_data_path, "rt") as f:
        bbox_data = json.load(f)

    # 2) open CSV
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["piece_id", "z", "x", "y", "temperature"])

        # 3) iterate pieces → layers → pixels
        for pid_str, layers in bbox_data.items():
            pid = int(pid_str)
            for z_str, info in layers.items():
                z = int(z_str)
                bb_min, _ = info["bounding_box"]
                for rel_y, rel_x in info["active_pixels"]:
                    x = bb_min[0] + rel_x
                    y = bb_min[1] + rel_y
                    # bounds-check
                    if (0 <= z < T.shape[0]
                        and 0 <= y < T.shape[1]
                        and 0 <= x < T.shape[2]):
                        writer.writerow([pid, z, x, y, T[z,y,x]])

    print(f"→ Exported pixel temperatures for {len(bbox_data)} pieces to {out_csv}")

def visualize_slice(T, z):
    plt.figure(figsize=(6, 6))
    plt.imshow(T[z], cmap="hot")
    plt.title(f"Voxel Slice {z}")
    plt.colorbar(label="Temperature (°C")
    plt.show()

if __name__ == "__main__":
    output = simulate_heat("voxel_bounding_boxes.json.gz")
    visualize_slice(output, z=0)
