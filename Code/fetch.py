from requests.auth import HTTPDigestAuth
from ABB_control import fetch_layer, fetch_welding, set_pause_printing, fetch_pieces_being_print
import requests
import time
import json
import os
import time
from collections import defaultdict

# URL for the API
# url = 'http://localhost/rw/motionsystem/mechunits/ROB_1/robtarget?coordinate=Wobj&json=1'
url = 'http://localhost/rw/motionsystem/mechunits/ROB_1/robtarget?tool=bendedTool&coordinate=Base&json=1'
url_weld = 'http://localhost/rw/rapid/symbol/data/RAPID/T_ROB1/MainModule/wielding?json=1'
url_layer = 'http://localhost/rw/rapid/symbol/data/RAPID/T_ROB1/MainModule/layer_finished?json=1'

# Create a session to persist cookies
session = requests.Session()

# Use Digest Authentication
auth = HTTPDigestAuth("Default User", "robotics")

deposition_points = []


# Function to fetch and print x, y, z values
def fetch_xyz():
    try:
        # Make the request to fetch data
        response = session.get(url, auth=auth)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON data
            data = response.json()

            # Extract and print data from the JSON object
            if '_embedded' in data:
                state = data['_embedded'].get('_state')
                if state:  # Check if the list is not empty
                    for target in state:  # Iterate through the list of targets
                        x = float(target.get('x'))
                        y = float(target.get('y'))
                        z = float(target.get('z'))
                        # print(z)
                        return x, y, z
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(f"Response body: {response.text}")  # Print the response body for debugging
    except Exception as e:
        print(f"An error occurred: {e}")



# Run the loop to continuously fetch x, y, z

def run_fetch_loop(path):
    global current_piece

    deposition_points = []

    # ——— 1) Un-pause the printer ———
    set_pause_printing(False)
    print()             

    # ——— 2) Immediately read the piece ID ———
    current_piece = fetch_pieces_being_print()
    print(f"→ Now printing piece {current_piece}")
    print()  # blank line

    # ——— 3) Start your print timer ———
    start = time.perf_counter()

    try:
        while True:
            # a) Fetch XYZ & weld
            x, y, z = fetch_xyz()
            weld    = fetch_welding()

            # b) Check if the printer switched to another piece mid-layer
            pid = fetch_pieces_being_print()
            if pid != current_piece:
                current_piece = pid
                print(f"→ Switched to printing piece {current_piece}")
                print()     # blank line

            # c) Collect points
            if x is not None and y is not None and weld:
                deposition_points.append((x, y, z))

            # d) Detect layer completion
            if fetch_layer():
                print("Layer finished! Pausing printing...")
                set_pause_printing(True)
                print()   # blank line
                break

            time.sleep(0.001)

        # … your JSON save logic …

        if os.path.exists(path):
                with open(path, "r") as f:
                    try:
                        all_points = json.load(f)
                    except json.JSONDecodeError:
                        all_points = []  # file is empty or broken
        else:
                all_points = []

        # Append new points
        all_points.extend(deposition_points)

        # Save updated points
        with open(path, "w") as f:
            json.dump(all_points, f)

        print(f"Saved {len(deposition_points)} new points. Total points now: {len(all_points)}")

    except KeyboardInterrupt:
        print("Loop stopped by user.")
    finally:
        duration = time.perf_counter() - start

    print(f"Printed piece {current_piece} in {duration:.2f}s")
    print()