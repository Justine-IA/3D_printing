from maping import RealTime3DMap
from Voxel_grid import process_voxel, show_slices, store_voxel_bounding_boxes, save_bounding_boxes_from_grid
from heat import simulate_heat, visualize_slice, compute_piece_avg_temp, load_piece_bbox
import fetch 
from ABB_control import fetch_number_of_layer, set_piece_choice, set_pause_printing
from filter_outliers import filter_points_by_layer
from calculate_cooling_time import start_print, end_print, get_cooling_time
import json
import numpy as np

nx,ny = (500,500)
cool_time = 10
nz = 2
layer_height = 1
min_pts     = 50
with open("deposition_points_piece_1.json", "r") as f:
    raw_pts = json.load(f)   # raw_pts should be a list of [x,y,z] triples
deposition_points = raw_pts
deposition_points = filter_points_by_layer(deposition_points, layer_height=layer_height, min_points=min_pts )
voxel_grid= process_voxel(deposition_points, nz, nx, ny,layer_height,  fill_radius=3)
# show_slices(voxel_grid)
bbox_path = "piece_1_bounding_boxes.json.gz"




piece_ids  = [0, 1, 2, 3]

def save_stats(piece_ids):
    stats = {}
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

        return stats


