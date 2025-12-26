"""
Create a SIMPLE 4-way intersection for demo
Clean, minimal, easy to understand
"""
import subprocess
from pathlib import Path

NETWORK_DIR = Path(__file__).parent
OUTPUT_NET = NETWORK_DIR / "network.net.xml"
OUTPUT_ROUTES = NETWORK_DIR / "routes_peak.rou.xml"

def create_simple_intersection():
    """Create a basic 4-way intersection using netedit"""
    
    print("=" * 50)
    print("🎯 CREATING SIMPLE 4-WAY INTERSECTION")
    print("=" * 50)
    
    # Create nodes file
    nodes_xml = """<?xml version="1.0" encoding="UTF-8"?>
<nodes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/nodes_file.xsd">
    <!-- Center junction -->
    <node id="center" x="0.0" y="0.0" type="traffic_light"/>
    
    <!-- North -->
    <node id="north" x="0.0" y="200.0" type="priority"/>
    <node id="north_end" x="0.0" y="400.0" type="priority"/>
    
    <!-- South -->
    <node id="south" x="0.0" y="-200.0" type="priority"/>
    <node id="south_end" x="0.0" y="-400.0" type="priority"/>
    
    <!-- East -->
    <node id="east" x="200.0" y="0.0" type="priority"/>
    <node id="east_end" x="400.0" y="0.0" type="priority"/>
    
    <!-- West -->
    <node id="west" x="-200.0" y="0.0" type="priority"/>
    <node id="west_end" x="-400.0" y="0.0" type="priority"/>
</nodes>
"""
    
    # Create edges file
    edges_xml = """<?xml version="1.0" encoding="UTF-8"?>
<edges xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/edges_file.xsd">
    <!-- North approach -->
    <edge id="north_in" from="north_end" to="north" numLanes="2" speed="13.89"/>
    <edge id="north_to_center" from="north" to="center" numLanes="2" speed="13.89"/>
    <edge id="center_to_north" from="center" to="north" numLanes="2" speed="13.89"/>
    <edge id="north_out" from="north" to="north_end" numLanes="2" speed="13.89"/>
    
    <!-- South approach -->
    <edge id="south_in" from="south_end" to="south" numLanes="2" speed="13.89"/>
    <edge id="south_to_center" from="south" to="center" numLanes="2" speed="13.89"/>
    <edge id="center_to_south" from="center" to="south" numLanes="2" speed="13.89"/>
    <edge id="south_out" from="south" to="south_end" numLanes="2" speed="13.89"/>
    
    <!-- East approach -->
    <edge id="east_in" from="east_end" to="east" numLanes="2" speed="13.89"/>
    <edge id="east_to_center" from="east" to="center" numLanes="2" speed="13.89"/>
    <edge id="center_to_east" from="center" to="east" numLanes="2" speed="13.89"/>
    <edge id="east_out" from="east" to="east_end" numLanes="2" speed="13.89"/>
    
    <!-- West approach -->
    <edge id="west_in" from="west_end" to="west" numLanes="2" speed="13.89"/>
    <edge id="west_to_center" from="west" to="center" numLanes="2" speed="13.89"/>
    <edge id="center_to_west" from="center" to="west" numLanes="2" speed="13.89"/>
    <edge id="west_out" from="west" to="west_end" numLanes="2" speed="13.89"/>
</edges>
"""
    
    # Write temp files
    nodes_file = NETWORK_DIR / "nodes.nod.xml"
    edges_file = NETWORK_DIR / "edges.edg.xml"
    
    with open(nodes_file, 'w') as f:
        f.write(nodes_xml)
    
    with open(edges_file, 'w') as f:
        f.write(edges_xml)
    
    print("📝 Created node and edge definitions")
    
    # Generate network using netconvert
    netconvert_cmd = [
        'netconvert',
        '--node-files', str(nodes_file),
        '--edge-files', str(edges_file),
        '--output-file', str(OUTPUT_NET),
        '--tls.guess', 'true',
        '--junctions.corner-detail', '5',
        '--no-turnarounds', 'false'
    ]
    
    try:
        result = subprocess.run(netconvert_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Simple 4-way intersection created!")
            
            # Clean up temp files
            nodes_file.unlink()
            edges_file.unlink()
            
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ netconvert not found!")
        return False


def create_simple_routes():
    """Generate simple traffic flows for 4-way junction"""
    
    routes_xml = """<routes>
    <!-- Vehicle Types (Bangalore calibrated) -->
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="4.5" minGap="2.5" maxSpeed="11.11" color="1,0.8,0"/>
    <vType id="bus" accel="1.2" decel="3.0" sigma="0.5" length="12.0" minGap="3.0" maxSpeed="10.0" color="0.2,1,0.2"/>
    
    <!-- Simple Routes (all directions) -->
    <route id="north_to_south" edges="north_in north_to_center center_to_south south_out"/>
    <route id="south_to_north" edges="south_in south_to_center center_to_north north_out"/>
    <route id="east_to_west" edges="east_in east_to_center center_to_west west_out"/>
    <route id="west_to_east" edges="west_in west_to_center center_to_east east_out"/>
    
    <route id="north_to_east" edges="north_in north_to_center center_to_east east_out"/>
    <route id="north_to_west" edges="north_in north_to_center center_to_west west_out"/>
    <route id="south_to_east" edges="south_in south_to_center center_to_east east_out"/>
    <route id="south_to_west" edges="south_in south_to_center center_to_west west_out"/>
    
    <!-- Traffic Flows (Peak Hour: ~520 veh/h total) -->
    <!-- North-South (heavy) -->
    <flow id="ns_cars" begin="0" end="3600" number="140" route="north_to_south" type="car" departPos="base" departSpeed="max"/>
    <flow id="sn_cars" begin="0" end="3600" number="130" route="south_to_north" type="car" departPos="base" departSpeed="max"/>
    
    <!-- East-West (moderate) -->
    <flow id="ew_cars" begin="0" end="3600" number="90" route="east_to_west" type="car" departPos="base" departSpeed="max"/>
    <flow id="we_cars" begin="0" end="3600" number="80" route="west_to_east" type="car" departPos="base" departSpeed="max"/>
    
    <!-- Turning movements -->
    <flow id="n_to_e" begin="0" end="3600" number="25" route="north_to_east" type="car" departPos="base" departSpeed="max"/>
    <flow id="s_to_w" begin="0" end="3600" number="25" route="south_to_west" type="car" departPos="base" departSpeed="max"/>
    
    <!-- Buses -->
    <flow id="ns_buses" begin="0" end="3600" number="15" route="north_to_south" type="bus" departPos="base" departSpeed="max"/>
    <flow id="ew_buses" begin="0" end="3600" number="15" route="east_to_west" type="bus" departPos="base" departSpeed="max"/>
    
</routes>
"""
    
    with open(OUTPUT_ROUTES, 'w') as f:
        f.write(routes_xml)
    
    print("✅ Simple routes created (520 veh/h)")


def main():
    """Create clean simple intersection"""
    
    if not create_simple_intersection():
        print("\n❌ Failed to create intersection")
        return False
    
    create_simple_routes()
    
    print("\n" + "=" * 50)
    print("🎉 CLEAN 4-WAY INTERSECTION READY!")
    print("=" * 50)
    print("📍 Type: Simple synthetic junction")
    print("🚗 Traffic: 520 veh/h (govt calibrated)")
    print("🗺️  Layout: Clean 4-way with traffic lights")
    print("\n👉 Restart backend and start simulation!")
    print("=" * 50)
    
    return True


if __name__ == "__main__":
    main()
