from maping import RealTime3DMap
from geometry_reconstruction import process_deposition_points
from Voxel_grid import process_voxel
from heat import simulate_heat, visualize_slice
from fetch import run_fetch_loop
from ABB_control import set_pause_printing

import json
import time

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
    with open("deposition_points_test.json", "w") as f:
        json.dump([], f)
    while True:

        #fetch all the points in one layer printed
        run_fetch_loop(path = "deposition_points_test.json")
        
    
        with open("deposition_points_test.json", "r") as f:
             deposition_points = json.load(f)

        #show the points collected
        # recreating_the_map(deposition_points)

        #show the general geometry of the shape
        # process_deposition_points(deposition_points, layer_height=1, eps=40, min_samples=5)


        #compute the voxel representation
        voxel_grid, labeled_grid, num_features = process_voxel(deposition_points, nx=2000, ny=2000, nz=1, fill_radius=3)
        print("Voxel processing complete. Number of components:", num_features)

        #compute the heat propagation inside all pieces 
        output = simulate_heat("voxel_bounding_boxes.json.gz", nz=1, nx=2000, ny=2000,steps_per_layer=1)

        visualize_slice(output, z=0)



if __name__ == "__main__":
    main()
