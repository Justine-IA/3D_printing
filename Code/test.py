from maping import RealTime3DMap
from Voxel_grid import process_voxel, show_slices, store_voxel_bounding_boxes, save_bounding_boxes_from_grid
from heat import simulate_heat, visualize_slice, export_pixel_temperatures, run_real_time_simulation
import fetch 
from ABB_control import fetch_number_of_layer, set_piece_choice, set_pause_printing
from filter_outliers import filter_points_by_layer
from calculate_cooling_time import start_print, end_print, get_cooling_time
import json

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
show_slices(voxel_grid)
bbox_path = "piece_1_bounding_boxes.json.gz"
output = simulate_heat(bbox_path, nz, nx, ny,cool_time, steps_per_layer=1)

visualize_slice(output, 0)

