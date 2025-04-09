from heat_map import  RealTime2DGridMap, RealTime3DMap
from geometry_reconstruction import process_deposition_points
import json
import time

with open("deposition_points.json", "r") as f:
    deposition_points = json.load(f)
print(f"Loaded {len(deposition_points)} deposition points.")


def main():
    # Initialize the RealTime3DMap
    map_3d = RealTime3DMap()
    
    #Simulate real-time plotting from loaded deposition points
    for point in deposition_points:
        x, y, z = point
        map_3d.update_plot(x, y, z)
        # Optional: add a small delay to mimic real-time data arrival
        # time.sleep(0.001)
    
    map_3d.show()

    #show the general geometry of the shape
    process_deposition_points(deposition_points, layer_height=1, eps=40, min_samples=5)

if __name__ == "__main__":
    main()
