"""
Generate traffic for the focused Silk Board network
Uses SUMO's randomTrips to create realistic traffic
"""
import subprocess
import os
from pathlib import Path

NETWORK_DIR = Path(__file__).parent
NETWORK_FILE = NETWORK_DIR / "network.net.xml"
ROUTE_FILE = NETWORK_DIR / "routes_peak.rou.xml"

# Try to find randomTrips.py
SUMO_HOME = os.environ.get('SUMO_HOME', 'C:/Program Files (x86)/Eclipse/Sumo')
RANDOM_TRIPS = Path(SUMO_HOME) / 'tools' / 'randomTrips.py'

if not RANDOM_TRIPS.exists():
    print(f"❌ randomTrips.py not found at: {RANDOM_TRIPS}")
    print("Creating manual routes instead...")
    
    # Fallback: Create manual routes
    route_xml = """<routes>
    <!-- Vehicle Types -->
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="4.5" minGap="2.5" maxSpeed="11.11" color="1,0.8,0"/>
    <vType id="bus" accel="1.2" decel="3.0" sigma="0.5" length="12.0" minGap="3.0" maxSpeed="10.0" color="0.2,1,0.2"/>
    
    <!-- Manual Trips - will auto-route -->
    <trip id="trip_0" depart="0" from="gneE0" to="gneE5" type="car"/>
    <trip id="trip_1" depart="5" from="gneE1" to="gneE6" type="car"/>
    <trip id="trip_2" depart="10" from="gneE2" to="gneE7" type="car"/>
    <trip id="trip_3" depart="15" from="gneE0" to="gneE8" type="bus"/>
    <trip id="trip_4" depart="20" from="gneE3" to="gneE9" type="car"/>
    <trip id="trip_5" depart="25" from="gneE4" to="gneE10" type="car"/>
    <trip id="trip_6" depart="30" from="gneE0" to="gneE11" type="car"/>
    <trip id="trip_7" depart="35" from="gneE1" to="gneE12" type="car"/>
    <trip id="trip_8" depart="40" from="gneE2" to="gneE5" type="car"/>
    <trip id="trip_9" depart="45" from="gneE3" to="gneE6" type="car"/>
</routes>"""
    
    with open(ROUTE_FILE, 'w') as f:
        f.write(route_xml)
    
    print(f"✅ Manual routes created: {ROUTE_FILE}")
else:
    # Use randomTrips
    cmd = [
        'python', str(RANDOM_TRIPS),
        '-n', str(NETWORK_FILE),
        '-r', str(ROUTE_FILE),
        '-b', '0',
        '-e', '3600',
        '-p', '7',  # One vehicle every 7 seconds = ~520/hour
        '--fringe-factor', '10',
        '--min-distance', '50',
        '--trip-attributes', 'departLane="best" departSpeed="max"',
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Random trips generated: {ROUTE_FILE}")
        else:
            print(f"❌ Error: {result.stderr}")
    except Exception as e:
        print(f"❌ Failed: {e}")

print("\n🎯 Routes ready for simulation!")
