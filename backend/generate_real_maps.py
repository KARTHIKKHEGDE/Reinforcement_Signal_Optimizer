import os
import subprocess
import time
import requests

# Configuration for Locations (Tighter Bounding Boxes - approx 300m width)
LOCATIONS = {
    "silk_board": {
        "bbox": "77.6185,12.9160,77.6215,12.9190", # SUPER ZOOMED Silk Board
        "traffic_scale": 6 # Higher density for smaller area
    },
    "tin_factory": {
        "bbox": "77.6600,12.9925,77.6640,12.9955", # Zoomed Tin Factory
        "traffic_scale": 5
    },
    "hebbal": {
        "bbox": "77.5910,13.0345,77.5950,13.0375", # Zoomed Hebbal
        "traffic_scale": 4
    }
}

SUMO_HOME = os.environ.get("SUMO_HOME", "C:\\Program Files (x86)\\Eclipse\\Sumo")
NETCONVERT = os.path.join(SUMO_HOME, "bin", "netconvert.exe")
RANDOMTRIPS = os.path.join(SUMO_HOME, "tools", "randomTrips.py")
DUAROUTER = os.path.join(SUMO_HOME, "bin", "duarouter.exe")

def download_osm(location, bbox):
    print(f"🌍 Downloading OSM data for {location}...")
    url = f"https://api.openstreetmap.org/api/0.6/map?bbox={bbox}"
    response = requests.get(url)
    if response.status_code == 200:
        file_path = f"app/sumo/network/{location}.osm"
        with open(file_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Saved {file_path}")
        return file_path
    else:
        print(f"❌ Failed to download {location}: {response.status_code}")
        return None

def convert_to_net(location, osm_file):
    print(f"🔨 Converting {location} to SUMO Network...")
    net_file = f"app/sumo/network/{location}.net.xml"
    
    # Simple, strict conversion to avoid errors with fancy vehicle types
    cmd = [
        NETCONVERT,
        "--osm-files", osm_file,
        "--output-file", net_file,
        "--geometry.remove", "true",
        "--roundabouts.guess", "true",
        "--ramps.guess", "true",
        "--junctions.join", "true",
        "--tls.guess", "true",            # crucial: guess signals
        "--tls.discard-simple", "false",  # crucial: keep all signals!
        "--tls.join", "true",             # crucial: merge nodes
        "--tls.join-dist", "60",          # crucial: merge distance for Silk Board
        "--tls.default-type", "static",   # ensure static (controllable)
        "--tls.guess.threshold", "9",
        # crucial cleanup
        "--remove-edges.isolated", "true",
        "--keep-edges.by-vclass", "passenger,bus,taxi,delivery", # Strip weird classes
        "--no-turnarounds", "true"
    ]
    
    subprocess.run(cmd, check=True)
    print(f"✅ Created {net_file}")
    return net_file

def generate_traffic(location, net_file, scale):
    print(f"🚗 Generating Traffic for {location}...")
    trips_file = f"app/sumo/network/trips_{location}.xml"
    routes_file = f"app/sumo/network/routes_{location}.rou.xml"
    
    # 1. Generate random trips
    # Scale controls density: smaller period = more cars
    period = 3600 / (1000 * scale) 
    
    cmd_trips = [
        "python", RANDOMTRIPS,
        "-n", net_file,
        "-o", trips_file,
        "-e", "3600",
        "-p", str(period),
        "--vehicle-class", "passenger",
        "--fringe-factor", "10", # Push traffic to edges
        "--validate",
        "--remove-loops"
    ]
    subprocess.run(cmd_trips, check=True)
    
    # 2. Convert trips to routes (using duarouter for valid paths)
    cmd_routes = [
        DUAROUTER,
        "--net-file", net_file,
        "--route-files", trips_file,
        "--output-file", routes_file,
        "--ignore-errors",
        "--no-warnings"
    ]
    try:
        subprocess.run(cmd_routes, check=True)
        print(f"✅ Created {routes_file}")
        
        # Post-process: Add visualization shapes (Search replace)
        with open(routes_file, "r") as f:
            content = f.read()
        
        # Inject vehicle type definition with yellow shape
        vtype = '<vType id="car" vClass="passenger" guiShape="passenger/sedan" color="1,1,0" accel="2.6" decel="4.5" length="5.0"/>'
        content = content.replace("<routes", f"<routes>\n    {vtype}")
        content = content.replace('type="typed"', 'type="car"') # randomTrips default type
        
        with open(routes_file, "w") as f:
            f.write(content)
            
    except Exception as e:
        print(f"Warning: Route generation had issues: {e}")

def main():
    if not os.path.exists("app/sumo/network"):
        os.makedirs("app/sumo/network")
        
    for location, data in LOCATIONS.items():
        osm_file = download_osm(location, data["bbox"])
        if osm_file:
            net_file = convert_to_net(location, osm_file)
            generate_traffic(location, net_file, data["traffic_scale"])

if __name__ == "__main__":
    main()
