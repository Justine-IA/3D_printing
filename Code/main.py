from maping import RealTime3DMap
from Voxel_grid import process_voxel, show_slices, store_voxel_bounding_boxes, save_bounding_boxes_from_grid
from heat import simulate_heat, visualize_slice, export_pixel_temperatures, run_real_time_simulation
import fetch 
from ABB_control import fetch_number_of_layer, set_piece_choice
from filter_outliers import filter_points_by_layer

import json, os
import time
from scipy.ndimage import label
import numpy as np 
from glob import glob

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
    for i in range(1,5):
            path_to_clean = f"deposition_points_piece_{i}.json"
            with open(path_to_clean, "w") as f:
                json.dump([], f)
    try:
        for i in range(4):
            print("-----------NEW LOOP-----------")
            print()

            piece_id = fetch.fetch_pieces_being_print()
            path = f"deposition_points_piece_{piece_id}.json"

            #fetch all the points in one layer printed
            fetch.run_fetch_loop(path=path)

            deposition_points = json.load(open(path))


            layer_height =  1.0     #printer’s layer height in mm
            min_pts     = 50
            deposition_points = filter_points_by_layer(deposition_points, layer_height=layer_height, min_points=min_pts )

            #show the points collected
            #recreating_the_map(deposition_points)

            print()
            url_number_of_layers = (
                f"http://localhost/rw/rapid/symbol/data/"
                f"RAPID/T_ROB1/MainModule/"
                f"number_of_layer_piece_{piece_id}?json=1"
            )

            nz = fetch_number_of_layer(url_number_of_layers)
            print(f"number of layers:{nz}")
            ny, nx = (500,500) 

            current_piece  = fetch.current_piece
            cool_time = fetch.cooling_times[current_piece]
            print(f"Passing cool_time={cool_time:.2f}s for piece {current_piece}")
            print()

            #compute the voxel representation
            voxel_grid= process_voxel(deposition_points, nz, nx, ny,layer_height,  fill_radius=3)
            # print("Voxel processing complete. Number of components:", num_features)
            show_slices(voxel_grid)

            _, bbox_path = save_bounding_boxes_from_grid(voxel_grid, current_piece)

            #compute the heat propagation inside all pieces 
            output = simulate_heat(bbox_path, nz, nx, ny,cool_time, steps_per_layer=1)

            # output = run_real_time_simulation(voxel_data_path=bbox_path,nz=nz,  nx=nx,  ny=ny,dt=0.1,print_time=6.0,
            #      cool_time=10.0, Q_val=660.0,T_init=20.0,T_amb=20.0)

            for i in range(nz):
                visualize_slice(output, i)


            print("-----------END LOOP-----------")            
            print()
            print()

        
        while True:
            print("-----------NEW LOOP-----------")
            print()
            choice = int(input("Enter the piece number you want to print (1–4): "))
            set_piece_choice(choice)

            time.sleep(1)
            piece_id = choice
            path = f"deposition_points_piece_{piece_id}.json"

            #fetch all the points in one layer printed
            fetch.run_fetch_loop(path=path)

            deposition_points = json.load(open(path))


            layer_height =  1.0     #printer’s layer height in mm
            min_pts     = 100
            deposition_points = filter_points_by_layer(deposition_points, layer_height=layer_height, min_points=min_pts )

            #show the points collected
            #recreating_the_map(deposition_points)

            print()
            url_number_of_layers = (
                f"http://localhost/rw/rapid/symbol/data/"
                f"RAPID/T_ROB1/MainModule/"
                f"number_of_layer_piece_{piece_id}?json=1"
            )

            nz = fetch_number_of_layer(url_number_of_layers)
            print(f"number of layers:{nz}")
            ny, nx = (500,500) 

            current_piece  = fetch.current_piece
            cool_time = fetch.cooling_times[current_piece]
            print(f"Passing cool_time={cool_time:.2f}s for piece {current_piece}")
            print()

            #compute the voxel representation
            voxel_grid= process_voxel(deposition_points, nz, nx, ny,layer_height,  fill_radius=3)
            # print("Voxel processing complete. Number of components:", num_features)
            show_slices(voxel_grid)

            _, bbox_path = save_bounding_boxes_from_grid(voxel_grid, current_piece)

            #compute the heat propagation inside all pieces 
            output = simulate_heat(bbox_path, nz, nx, ny,cool_time, steps_per_layer=1)

            # output = run_real_time_simulation(voxel_data_path=bbox_path,nz=nz,  nx=nx,  ny=ny,dt=0.1,print_time=6.0,
            #      cool_time=10.0, Q_val=660.0,T_init=20.0,T_amb=20.0)

            for i in range(nz):
                visualize_slice(output, i)


            # export_pixel_temperatures(output, voxel_data_path=bbox_path, out_csv="piece_pixel_temps.csv")


            # BLABLA BLA CALL AI THEN DECISION USING:
            #set_piece_choice(choice)
            print("-----------END LOOP-----------")            
            print()
            print()


    except KeyboardInterrupt:
        print("🏁 All done — exiting.")
        



if __name__ == "__main__":
    main()
