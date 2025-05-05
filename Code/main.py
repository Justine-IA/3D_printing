from maping import RealTime3DMap
from Voxel_grid import process_voxel, show_slices, store_voxel_bounding_boxes, save_bounding_boxes_from_grid
from heat import simulate_heat, visualize_slice, load_piece_bbox, compute_piece_avg_temp
import fetch 
from ABB_control import fetch_number_of_layer, set_piece_choice, set_pause_printing
from filter_outliers import filter_points_by_layer
from calculate_cooling_time import start_print, end_print, get_cooling_time
from policy import choose_safe_piece, choose_next_piece
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
    piece_ids  = [1, 2, 3, 4]

    for i in piece_ids:
            path_to_clean = f"deposition_points_piece_{i}.json"
            with open(path_to_clean, "w") as f:
                json.dump([], f)
    try:
        for i in piece_ids:
            print("-----------NEW LOOP-----------")
            print()

            piece_id = fetch.fetch_pieces_being_print()
            path = f"deposition_points_piece_{piece_id}.json"

            idle = start_print(piece_id)
            print(f"→ Piece {piece_id} cooled for {idle:.2f}s since last print")

            #fetch all the points in one layer printed
            fetch.run_fetch_loop(path=path)

            end_print(piece_id)

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
            ny, nx = (400,400) 

            current_piece  = fetch.current_piece
            cool_time = get_cooling_time(piece_id)
            print(f"Passing cool_time={cool_time:.2f}s for piece {piece_id}")
            print()

            #compute the voxel representation
            voxel_grid= process_voxel(deposition_points, nz, nx, ny,layer_height,  fill_radius=3)
            # show_slices(voxel_grid)

            _, bbox_path = save_bounding_boxes_from_grid(voxel_grid, current_piece)

            #compute the heat propagation inside all pieces 
            output = simulate_heat(bbox_path, nz, nx, ny,cool_time, steps_per_layer=1)

            for i in range(nz):
                visualize_slice(output, i)

            print("-----------END LOOP-----------")            
            print()
            print()

        stats      = {}

        for i in piece_ids:
            bbox_path = f"piece_{i}_bounding_boxes.json.gz"
            cool_time = cool_time = get_cooling_time(i)
            url_number_of_layers = (
                        f"http://localhost/rw/rapid/symbol/data/"
                        f"RAPID/T_ROB1/MainModule/"
                        f"number_of_layer_piece_{i}?json=1"
                    )

            nz = fetch_number_of_layer(url_number_of_layers)
            output = simulate_heat(bbox_path, nz, nx, ny,cool_time, steps_per_layer=1)

            # 3) Load only this piece’s bounding‐box data
            piece_bbox = load_piece_bbox(i)

            # 4) Compute avg temperature & masked heatmap
            avg_temp, heatmap = compute_piece_avg_temp(
                output,
                piece_bbox,
                mask_heatmap=True
            )

            # 5) Save the mask-filtered heatmap, record stats
            heatmap_file = f"piece_{i}_heatmap.npy"
            np.save(heatmap_file, heatmap)

            stats[i] = {
                "avg_temp":     avg_temp,
                "cool_time":    cool_time,
                "heatmap_file": heatmap_file,
                "nz":           nz,
                "nx":           nx,
                "ny":           ny,
            }

        for pid, info in stats.items():
            # 2) Access average temperature:
            avg_temp = info["avg_temp"]
            print(f"Piece {pid}: average temp = {avg_temp:.2f} °C")

            # 3) Load the masked heatmap array:
            heatmap = np.load(info["heatmap_file"])  # shape (nz, ny, nx)

            # 4) (Optional) visualize layer 0 of this piece:
            visualize_slice(heatmap, z=0)

        # AI FOR FIRST CHOICE THEN ENTER THE LOOP

        while True:
            print("-----------NEW LOOP-----------")
            print()
            # BLABLA BLA CALL AI THEN DECISION USING:
            #while possible = false
            #   choice = AI DECISION
            #   if avg_temp(choice) < temp_max_require
            #       possible = true
            #   else 
            #       time.sleep(10)
            #   set_piece_choice(choice)
            choice = int(input("Enter the piece number you want to print (1-4): "))

            # choice = choose_safe_piece(stats, model=None)  
            # set_piece_choice(choice)
            # print(f"→ Printing piece {choice}")

            set_piece_choice(choice)

            if choice == 0:
                set_pause_printing(False)
                break

            time.sleep(1)
            piece_id = choice
            path = f"deposition_points_piece_{piece_id}.json"

            idle = start_print(piece_id)
            print(f"→ Piece {piece_id} cooled for {idle:.2f}s since last print")

            #fetch all the points in one layer printed
            fetch.run_fetch_loop(path=path)

            end_print(piece_id)

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
            cool_time = get_cooling_time(piece_id)
            print(f"Passing cool_time={cool_time:.2f}s for piece {current_piece}")
            print()

            #compute the voxel representation
            voxel_grid= process_voxel(deposition_points, nz, nx, ny,layer_height,  fill_radius=3)
            # show_slices(voxel_grid)

            _, bbox_path = save_bounding_boxes_from_grid(voxel_grid, current_piece)

            #compute the heat propagation inside all pieces 
            output = simulate_heat(bbox_path, nz, nx, ny,cool_time, steps_per_layer=1)

            for i in range(nz):
                visualize_slice(output, i)
            


            # export_pixel_temperatures(output, voxel_data_path=bbox_path, out_csv="piece_pixel_temps.csv")




            print("-----------END LOOP-----------")            
            print()
            print()


    except KeyboardInterrupt:
        set_pause_printing(False)
        print("🏁 All done — exiting.")
        



if __name__ == "__main__":
    main()