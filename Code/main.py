from maping import RealTime3DMap
from Voxel_grid import process_voxel, show_slices, store_voxel_bounding_boxes, save_bounding_boxes_from_grid
from heat import simulate_heat, visualize_slice, load_piece_bbox, compute_piece_avg_temp
import fetch 
from ABB_control import fetch_number_of_layer, set_piece_choice, set_pause_printing
from filter_outliers import filter_points_by_layer
from calculate_cooling_time import start_print, end_print, get_cooling_time
from save_heat_stats import save_heat_stats, display_stats
from q_agent import QAgent

import json, os
import time
from scipy.ndimage import label
import numpy as np 
from glob import glob
import matplotlib.pyplot as plt



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
    agent = QAgent()
    reward_history = []

    start_time = time.time()
    # Charger la table Q si elle existe
    if os.path.exists("q_table.pkl"):
        print("🧠 Loading existing Q-table...")
        agent.load("q_table.pkl")
    else:
        print("🧠 Starting with new Q-table.")

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
        number_of_layers_to_print = 10

        episode_reward = 0
        prev_state = None
        prev_action = None


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

                    threshold = 5 if piece_id == 1 else number_of_layers_to_print

                    if nz >= threshold :   
                        to_remove.append(piece_id)
                        print(f"Piece {piece_id} has reached {threshold} layers - removing from queue")
                except Exception as e:
                    print(f"Error checking layers for piece {piece_id}: {e}")
                    continue
            
            # Remove completed pieces
            for piece_id in to_remove:
                if piece_id in piece_ids:
                    piece_ids.remove(piece_id)
            
            # Exit condition - all pieces completed
            if not piece_ids:
                print("All pieces have reached their final layers. Printing complete!")
                set_piece_choice(0)
                set_pause_printing(False)
                stats = save_heat_stats(piece_ids, nx, ny)
                display_stats(stats)
                print("💾 Saving Q-table...")
                print()
                agent.save("q_table.pkl")
                plt.figure(figsize=(10, 4))
                plt.plot(reward_history, label="Total reward per episode")
                plt.xlabel("episode")
                plt.ylabel("Reward total")
                plt.title("evolution of AI performance")
                plt.legend()
                plt.grid()
                plt.tight_layout()
                plt.savefig("reward_progress.png")  # sauvegarde image
                plt.show()
                with open("reward_history.csv", "w") as f:
                    f.write("episode,reward\n")
                    for i, r in enumerate(reward_history):
                        f.write(f"{i},{r}\n")
                total_time = time.time() - start_time
                print(f" AI total time: {total_time}")
                break

            #update thermal stats
            stats = save_heat_stats(piece_ids, nx, ny)
            for pid, info in stats.items():
                    avg_temp = info["avg_temp"]
                    print(f"Piece {pid}: average temp = {avg_temp:.2f} °C")


            state = agent.encode_state(stats, piece_ids)

            valid_actions = [pid for pid in piece_ids if stats[pid]["avg_temp"] < agent.temp_threshold]

            # trying every 10 seconds if no pieces available
            waiting_time = 0
            while not valid_actions:
                print()
                print("No pieces is cold enough. waiting of 10s...")

                time.sleep(10)
                waiting_time += 10  
                stats = save_heat_stats(piece_ids, nx, ny)
                for pid, info in stats.items():
                    avg_temp = info["avg_temp"]
                    print(f"Piece {pid}: average temp = {avg_temp:.2f} °C")
                    cool_time = get_cooling_time(pid)
                    print(f"pieces cool time: {cool_time}")
                valid_actions = [pid for pid in piece_ids if stats[pid]["avg_temp"] < agent.temp_threshold]


            reward = -1
            if waiting_time == 0:
                reward += 5
            elif waiting_time < 30:
                reward += 1
            else:
                reward -= 5


            # choose a valid action
            choice = agent.choose_action(state, valid_actions)

            # memorized the state of the action
            prev_state = state
            prev_action = choice

            print("----------- AGENT CHOICE -------------")
            print()
            print(f"→ Ml chose : {choice}")
            cool_time = get_cooling_time(choice)
            print(f"cool time passed : {cool_time:.2f} s")
            print(f"actual temp of the pieces {choice}: {stats[choice]['avg_temp']:.2f} °C")
            print()
              
            # choice = int(input("Enter the piece number you want to print (1-4): "))
            set_piece_choice(choice)



            print(f"[auto] → Printing piece {choice}")

            piece_id = choice
            path = f"deposition_points_piece_{piece_id}.json"

            idle = start_print(piece_id)
            print(f"→ Piece {piece_id} cooled for {idle:.2f}s since last print")

            #fetch all the points in one layer printed and print the layer
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

            _, bbox_path = save_bounding_boxes_from_grid(voxel_grid, current_piece)

            print("⏳ Pause simulated for thermo stabilisation ...")

            time.sleep(5) 

            print(f"🔁 Total reward for this episode: {episode_reward}")
            reward_history.append(episode_reward)
            episode_reward = 0

            if prev_state is not None and prev_action is not None:
                agent.update(prev_state, prev_action, reward, state, valid_actions)
                episode_reward += reward


            agent.decay_epsilon()

            print("-----------END LOOP-----------")            
            print()
            print()


    except KeyboardInterrupt:
        set_piece_choice(0)
        set_pause_printing(False)
        stats = save_heat_stats(piece_ids, nx, ny)
        display_stats(stats)
        print("💾 Saving Q-table...")
        print()
        agent.save("q_table.pkl")
        plt.figure(figsize=(10, 4))
        plt.plot(reward_history, label="Total reward per episode")
        plt.xlabel("episode")
        plt.ylabel("Reward total")
        plt.title("evolution of AI performance")
        plt.legend()
        plt.grid()
        plt.tight_layout()
        plt.savefig("reward_progress.png")
        plt.show()
        with open("reward_history.csv", "w") as f:
            f.write("episode,reward\n")
            for i, r in enumerate(reward_history):
                f.write(f"{i},{r}\n")
        total_time = time.time() - start_time
        print(f" AI total time: {total_time}")
        print("🏁 All done — exiting.")
        



if __name__ == "__main__":
    main()