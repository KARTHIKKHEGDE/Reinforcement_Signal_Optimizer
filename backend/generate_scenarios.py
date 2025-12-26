
import json
import random

def generate_routes_for_location(location_key, config):
    print(f"Generating routes for {location_key}...")
    
    # Scale traffic based on the config
    scale = config["simulation_config"]["traffic_scale"]
    
    # Base flows (Drastically increased base for visual impact)
    base_flow_rate = 1500 # Base volume
    
    base_flows = [
        {"id": "horizontal_1", "route": "horizontal_1", "vehsPerHour": int(base_flow_rate * scale)},
        {"id": "horizontal_2", "route": "horizontal_2", "vehsPerHour": int(base_flow_rate * 0.9 * scale)},
        {"id": "vertical_1", "route": "vertical_1", "vehsPerHour": int(base_flow_rate * 0.6 * scale)},
        {"id": "vertical_2", "route": "vertical_2", "vehsPerHour": int(base_flow_rate * 0.7 * scale)},
        {"id": "through_1", "route": "through_1", "vehsPerHour": int(base_flow_rate * 0.8 * scale)},
        {"id": "through_2", "route": "through_2", "vehsPerHour": int(base_flow_rate * 0.85 * scale)},
    ]
    
    # Template
    content = """<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    
    <!-- Vehicle Types -->
    <!-- Force 'passenger/sedan' shape for realistic car look -->
    <vType id="car" vClass="passenger" guiShape="passenger/sedan" accel="2.6" decel="4.5" sigma="0.5" length="5.0" width="1.8" minGap="2.5" maxSpeed="55.56" color="1,1,0"/>
    <vType id="emergency" vClass="emergency" guiShape="emergency" accel="3.0" decel="5.0" sigma="0.2" length="7.0" maxSpeed="69.44" color="1,0,0"/>
    <vType id="bus" vClass="bus" guiShape="bus" accel="1.5" decel="3.5" sigma="0.3" length="12.0" width="2.5" maxSpeed="44.44" color="1,1,0"/>
    
    <!-- Routes -->
    <route id="horizontal_1" edges="h_0_0_to_1_0 h_1_0_to_2_0"/>
    <route id="horizontal_2" edges="h_2_0_to_1_0 h_1_0_to_0_0"/>
    <route id="vertical_1" edges="v_0_0_to_0_1"/>
    <route id="vertical_2" edges="v_0_1_to_0_0"/>
    <route id="through_1" edges="v_1_0_to_1_1 v_1_1_to_1_0"/>
    <route id="through_2" edges="v_1_1_to_1_0 v_1_0_to_1_1"/>
    
    <!-- Traffic flows -->
"""
    
    for flow in base_flows:
        content += f'    <flow id="{flow["id"]}" route="{flow["route"]}" begin="0" end="3600" vehsPerHour="{flow["vehsPerHour"]}" type="car"/>\n'
        
    # Emergency vehicles (occasional)
    content += f'    <flow id="emergency_flow" route="horizontal_1" begin="300" end="3600" period="{int(600/scale)}" type="emergency"/>\n'
    
    # Bus routes
    content += f'    <flow id="bus_flow" route="horizontal_1" begin="120" end="3600" period="{int(300/scale)}" type="bus"/>\n'
    
    content += """</routes>"""
    
    with open(f"app/sumo/network/routes_{location_key}.rou.xml", "w") as f:
        f.write(content)

# Load locations
with open("data/govt_congestion/locations.json", "r") as f:
    locations = json.load(f)

for key, data in locations.items():
    generate_routes_for_location(key, data)

print("All route files generated!")
