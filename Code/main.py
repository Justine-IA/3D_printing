from maping import RealTime3DMap
from geometry_reconstruction import process_deposition_points
from Voxel_grid import process_voxel
from heat import simulate_heat, visualize_slice, export_pixel_temperatures, run_real_time_simulation
from fetch import run_fetch_loop
from ABB_control import fetch_number_of_layer

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

        nz = fetch_number_of_layer()
        print(f"number of layers:{nz}")
        ny, nx = (1000,1000) if nz == 1 else (2000,2000)

        #compute the voxel representation
        voxel_grid, labeled_grid, num_features = process_voxel(deposition_points,nz, nx, ny, fill_radius=3)
        print("Voxel processing complete. Number of components:", num_features)

        #compute the heat propagation inside all pieces 
        output = simulate_heat("voxel_bounding_boxes.json.gz", nz, nx, ny,steps_per_layer=1)

        # output = run_real_time_simulation(voxel_data_path="voxel_bounding_boxes.json.gz",nz=nz,  nx=nx,  ny=ny,dt=0.1,print_time=6.0,
        # cool_time=10.0, Q_val=660.0,T_init=20.0,T_amb=20.0)


        visualize_slice(output, z=nz-1)

        # export_pixel_temperatures(output, voxel_data_path="voxel_bounding_boxes.json.gz", out_csv="piece_pixel_temps.csv")



if __name__ == "__main__":
    main()
