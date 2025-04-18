import requests
from requests.auth import HTTPDigestAuth
import time
from maping import  RealTime2DGridMap, RealTime3DMap
from geometry_reconstruction import process_deposition_points
import json

# URL for the API
# url = 'http://localhost/rw/motionsystem/mechunits/ROB_1/robtarget?coordinate=Wobj&json=1'
url = 'http://localhost/rw/motionsystem/mechunits/ROB_1/robtarget?tool=bendedTool&coordinate=Base&json=1'
url_wielding = 'http://localhost/rw/rapid/symbol/data/RAPID/T_ROB1/MainModule/wielding?json=1'
# Create a session to persist cookies
session = requests.Session()

# Use Digest Authentication
auth = HTTPDigestAuth("Default User", "robotics")

deposition_points = []

map_3d = RealTime3DMap()

# map_2d = RealTime2DGridMap(grid_size=(25, 25), x_max=500, y_max=500)  # Customize grid size and axis limits

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
                        print(z)
                        return x, y, z
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(f"Response body: {response.text}")  # Print the response body for debugging
    except Exception as e:
        print(f"An error occurred: {e}")

def fetch_welding():
    try:
        # Make the request to fetch data
        response = session.get(url_wielding, auth=auth)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON data
            data = response.json()

            # Extract and print data from the JSON object
            if '_embedded' in data:
                state = data['_embedded'].get('_state')
                if state:  # Check if the list is not empty
                    for target in state:  # Iterate through the list of targets

                        if target.get('value') =="TRUE":
                            weld = True
                        else: 
                            weld = False
                        
                        print(weld)
                        return weld
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(f"Response body: {response.text}")  # Print the response body for debugging
    except Exception as e:
        print(f"An error occurred: {e}")


# Run the loop to continuously fetch x, y, z

try:
    while True:
        x, y, z = fetch_xyz()
        weld = fetch_welding()
        if x is not None and y is not None and weld is True:
            deposition_points.append((x, y, z))
            map_3d.update_plot(x, y, z)
            # map_2d.heat_propagation(x, y)

        time.sleep(0.001)
except KeyboardInterrupt:
    print("Loop stopped by user.")
finally:
     map_3d.show()
    # map_2d.show()
    

with open("deposition_points.json", "w") as f:
    json.dump(deposition_points, f)
print("Deposition points saved to deposition_points.json")
