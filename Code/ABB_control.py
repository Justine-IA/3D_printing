import requests
import time
from requests.auth import HTTPDigestAuth

# --- CONFIG ---
url_layer = 'http://localhost/rw/rapid/symbol/data/RAPID/T_ROB1/MainModule/layer_finished?json=1'
url_pause = 'http://localhost/rw/rapid/symbol/data/RAPID/T_ROB1/MainModule/pause_printing?json=1'
url_weld = 'http://localhost/rw/rapid/symbol/data/RAPID/T_ROB1/MainModule/wielding?json=1'
url_number_of_layer = 'http://localhost/rw/rapid/symbol/data/RAPID/T_ROB1/MainModule/number_of_layer?json=1'
auth = HTTPDigestAuth("Default User", "robotics")
session = requests.Session()

# --- FETCH if ABB finished a layer ---
def fetch_layer():
    try:
        # Make the request to fetch data
        response = session.get(url_layer, auth=auth)

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
                            layer_finished = True
                        else: 
                            layer_finished = False
                        
                        return layer_finished
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(f"Response body: {response.text}")  # Print the response body for debugging
    except Exception as e:
        print(f"An error occurred: {e}")
    
def fetch_welding():
    try:
        # Make the request to fetch data
        response = session.get(url_weld, auth=auth)

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
                        
                        return weld
        else:
            print(f"Failed to fetch data. Status code: {response.status_code}")
            print(f"Response body: {response.text}")  # Print the response body for debugging
    except Exception as e:
        print(f"An error occurred: {e}")

def fetch_number_of_layer():
    try:
        resp = session.get(url_number_of_layer, auth=auth)
        resp.raise_for_status()
        data = resp.json()

        state = data.get('_embedded', {}).get('_state', [])
        # find the rap-data entry
        for entry in state:
            if entry.get('_type') == 'rap-data' and 'value' in entry:
                # value is a string, e.g. "1"
                try:
                    return int(entry['value'])
                except ValueError:
                    print(f"Cannot parse layer value {entry['value']!r}, defaulting to 0")
                    return 0

        # if we never found it
        print("⚠️ No rap-data/value entry found; defaulting to 0")
        return 0

    except requests.RequestException as e:
        print(f"HTTP error fetching layer count: {e}")
    except Exception as e:
        print(f"Unexpected error in fetch_number_of_layer: {e}")

    return 0


# --- Tell ABB to pause/resume printing ---
def set_pause_printing(value: bool):
    # IMPORTANT: add ?action=set to the URL
    url = "http://localhost/rw/rapid/symbol/data/RAPID/T_ROB1/MainModule/pause_printing?action=set"

    payload = {"value": "TRUE" if value else "FALSE"}

    try:
        response = session.post(
            url,
            auth=auth,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        if response.status_code == 204:
            print(f"pause_printing set to {value}")
        else:
            print(f"Failed to set pause_printing: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error setting pause_printing: {e}")

