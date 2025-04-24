import json
import time
from maping import RealTime3DMap
from geometry_reconstruction import process_deposition_points
from Voxel_grid import process_voxel
from heat import simulate_heat, visualize_slice
from fetch import run_fetch_loop


def recreating_the_map(deposition_points):
    # Initialize the RealTime3DMap
    map_3d = RealTime3DMap()
    
    #Simulate real-time plotting from loaded deposition points
    for point in deposition_points:
        x, y, z = point
        map_3d.update_plot(x, y, z)
        # Optional: add a small delay to mimic real-time data arrival
        time.sleep(0.001)
    
    map_3d.show()

def main():

    # run_fetch_loop()  # Uncomment if you want live fetching
    with open("deposition_points.json", "r") as f:
        deposition_points = json.load(f)

    recreating_the_map(deposition_points)

    #show the general geometry of the shape
    process_deposition_points(deposition_points, layer_height=1, eps=40, min_samples=5)

    voxel_grid, labeled_grid, num_features = process_voxel(deposition_points, nx=2000, ny=2000, nz=14, fill_radius=3)
    print("Voxel processing complete. Number of components:", num_features)

    output = simulate_heat("voxel_bounding_boxes.json.gz", steps_per_layer=1)

    visualize_slice(output, z=7)

if __name__ == "__main__":
    main()
