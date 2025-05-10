# stats_utils.py
import numpy as np
from heat      import simulate_heat, load_piece_bbox, compute_piece_avg_temp, visualize_slice
from ABB_control import fetch_number_of_layer
from calculate_cooling_time import get_cooling_time
import json
import time
# grid size & which pieces to process
piece_ids = [1,2,3,4]
nx, ny    = 400, 400

def save_heat_stats(piece_ids, nx, ny, out_json=None):
    stats = {}
    for pid in piece_ids:
        bbox_path = f"piece_{pid}_bounding_boxes.json.gz"
        cool_time = get_cooling_time(pid)
        url_nl    = (
            "http://localhost/rw/rapid/symbol/data/"
            "RAPID/T_ROB1/MainModule/"
            f"number_of_layer_piece_{pid}?json=1"
        )        
        cool_time = get_cooling_time(pid)        
        nz        = fetch_number_of_layer(url_nl)
        output = simulate_heat(bbox_path, nz, nx, ny, cool_time, steps_per_layer=1)
        piece_bbox = load_piece_bbox(pid)
        avg_temp, heatmap = compute_piece_avg_temp(output, piece_bbox, mask_heatmap=True)

        heatmap_file = f"piece_{pid}_heatmap.npy"
        np.save(heatmap_file, heatmap)

        stats[pid] = {
            "avg_temp":     avg_temp,
            "cool_time":    cool_time,
            "heatmap_file": heatmap_file,
            "nz":           nz,
            "nx":           nx,
            "ny":           ny,
        }


    if out_json:
         # add a timestamp so you can distinguish runs
        dump = {
            "run_time": time.time(),
            "grid":     {"nx": nx, "ny": ny},
            "stats":    stats
        }
        with open(out_json, "w") as f:
            json.dump(dump, f, indent=2)
    return stats



def display_stats(stats):
    for pid, info in stats.items():
        # 2) Access average temperature:
        avg_temp = info["avg_temp"]
        print(f"Piece {pid}: average temp = {avg_temp:.2f} °C")
        
        # 3) Load the masked heatmap array:
        heatmap = np.load(info["heatmap_file"])  
        # shape (nz, ny, nx)

        # 4) (Optional) visualize layer 0 of this piece:
        visualize_slice(heatmap, z=0)