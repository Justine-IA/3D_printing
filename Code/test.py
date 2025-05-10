from maping import RealTime3DMap
from Voxel_grid import process_voxel, show_slices, store_voxel_bounding_boxes, save_bounding_boxes_from_grid
from heat import simulate_heat, visualize_slice, load_piece_bbox, compute_piece_avg_temp
import fetch 
from ABB_control import fetch_number_of_layer, set_piece_choice, set_pause_printing
from filter_outliers import filter_points_by_layer
from calculate_cooling_time import start_print, end_print, get_cooling_time
from save_heat_stats import save_heat_stats, display_stats

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
    start_time = time.time()


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
            # print(f"Passing cool_time={cool_time:.2f}s for piece {piece_id}")
            print()

            #compute the voxel representation
            voxel_grid= process_voxel(deposition_points, nz, nx, ny,layer_height,  fill_radius=3)
            show_slices(voxel_grid)

            _, bbox_path = save_bounding_boxes_from_grid(voxel_grid, current_piece)

            #compute the heat propagation inside all pieces 
            print("Starting the simulation of the heat")
            output = simulate_heat(bbox_path, nz, nx, ny,cool_time, steps_per_layer=1)

            for i in range(nz):
                visualize_slice(output, i)

            print("-----------END LOOP-----------")            
            print()
            print()

        print("Finished manual printing and visualization.")
        input()  


        piece_ids = [1, 2, 3, 4]
        number_of_layers_to_print = 5

        stats = save_heat_stats(piece_ids, nx, ny)
        display_stats(stats)
        while True:
            
            print("-----------NEW LOOP-----------")
            print()
            to_remove = []
            for piece_id in piece_ids.copy():  # Use copy to avoid modification during iteration
                url = (
                    f"http://localhost/rw/rapid/symbol/data/"
                    f"RAPID/T_ROB1/MainModule/"
                    f"number_of_layer_piece_{piece_id}?json=1"
                )
                try:
                    nz = fetch_number_of_layer(url)
                    print(f"Piece {piece_id} has {nz} layers")
                    
                    if nz >= number_of_layers_to_print:
                        to_remove.append(piece_id)
                        print(f"Piece {piece_id} has reached {number_of_layers_to_print} layers - removing from queue")
                except Exception as e:
                    print(f"Error checking layers for piece {piece_id}: {e}")
                    continue
            
            # Remove completed pieces
            for piece_id in to_remove:
                if piece_id in piece_ids:
                    piece_ids.remove(piece_id)
            
            # Exit condition - all pieces completed
            if not piece_ids:
                print("All pieces have reached 6 layers. Printing complete!")
                total_time = time.time() - start_time
                print(f"total time: {total_time}")
                break
    
            
            possible = False
            temp_max_require = 200
            while possible == False: 
                for pid, info in stats.items():
                    avg_temp = info["avg_temp"]
                    print(f"Piece {pid}: average temp = {avg_temp:.2f} °C")

                stats  = save_heat_stats(piece_ids, nx, ny)
                choice = min(stats.keys(), key=lambda pid: stats[pid]["avg_temp"])

                print(f"piece selected: {choice}")
                cool_time = get_cooling_time(choice)
                print(f"pieces cool time: {cool_time}")
                avg_temp_of_choice = stats[choice]["avg_temp"]
                print(f"pieces temperature: {avg_temp_of_choice}")

                if avg_temp_of_choice < temp_max_require:
                    possible = True
                else :
                    time.sleep(10)
              
            # choice = int(input("Enter the piece number you want to print (1-4): "))
            set_piece_choice(choice)

            print(f"[auto] → Printing piece {choice}")

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
            ny, nx = (400,400) 

            current_piece  = fetch.current_piece
            cool_time = get_cooling_time(piece_id)
            print(f"Passing cool_time={cool_time:.2f}s for piece {current_piece}")
            print()

            #compute the voxel representation
            voxel_grid= process_voxel(deposition_points, nz, nx, ny,layer_height,  fill_radius=3)
            # show_slices(voxel_grid)

            _, bbox_path = save_bounding_boxes_from_grid(voxel_grid, current_piece)

            time.sleep(5) 


            print("-----------END LOOP-----------")            
            print()
            print()


    except KeyboardInterrupt:
        set_piece_choice(0)
        set_pause_printing(False)
        total_time = time.time() - start_time
        print(f"total time: {total_time}")
        print("🏁 All done — exiting.")
        



if __name__ == "__main__":
    main()