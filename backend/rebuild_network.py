"""
Script to rebuild the SUMO network file
This ensures the .net.xml file is valid and consistent
"""
import os
import subprocess
import sys

# Define the paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NETWORK_DIR = os.path.join(BASE_DIR, "app", "sumo", "network")
NETCONVERT_BIN = "netconvert"

if "SUMO_HOME" in os.environ:
    NETCONVERT_BIN = os.path.join(os.environ["SUMO_HOME"], "bin", "netconvert")

def create_nodes_file():
    """Create nodes.nod.xml"""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<nodes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/nodes_file.xsd">
    <node id="junction_1" x="0.0" y="0.0" type="traffic_light"/>
    <node id="north" x="0.0" y="200.0" type="priority"/>
    <node id="south" x="0.0" y="-200.0" type="priority"/>
    <node id="east" x="200.0" y="0.0" type="priority"/>
    <node id="west" x="-200.0" y="0.0" type="priority"/>
</nodes>
"""
    with open(os.path.join(NETWORK_DIR, "nodes.nod.xml"), "w") as f:
        f.write(content)

def create_edges_file():
    """Create edges.edg.xml"""
    # 2 lanes per edge to match routes
    content = """<?xml version="1.0" encoding="UTF-8"?>
<edges xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/edges_file.xsd">
    <edge id="north_in" from="north" to="junction_1" priority="78" numLanes="2" speed="13.89"/>
    <edge id="north_out" from="junction_1" to="north" priority="78" numLanes="2" speed="13.89"/>
    
    <edge id="south_in" from="south" to="junction_1" priority="78" numLanes="2" speed="13.89"/>
    <edge id="south_out" from="junction_1" to="south" priority="78" numLanes="2" speed="13.89"/>
    
    <edge id="east_in" from="east" to="junction_1" priority="78" numLanes="2" speed="13.89"/>
    <edge id="east_out" from="junction_1" to="east" priority="78" numLanes="2" speed="13.89"/>
    
    <edge id="west_in" from="west" to="junction_1" priority="78" numLanes="2" speed="13.89"/>
    <edge id="west_out" from="junction_1" to="west" priority="78" numLanes="2" speed="13.89"/>
</edges>
"""
    with open(os.path.join(NETWORK_DIR, "edges.edg.xml"), "w") as f:
        f.write(content)

def build_network():
    """Run netconvert to generate network.net.xml"""
    print(f"Building network in {NETWORK_DIR}")
    
    cmd = [
        NETCONVERT_BIN,
        "--node-files", os.path.join(NETWORK_DIR, "nodes.nod.xml"),
        "--edge-files", os.path.join(NETWORK_DIR, "edges.edg.xml"),
        "--output-file", os.path.join(NETWORK_DIR, "network.net.xml"),
        "--tls.guess", "true",  # Guess TLS logic
        "--junctions.join", "true"
    ]
    
    try:
        if sys.platform == 'win32':
             # Handle Windows executable extension
             if not NETCONVERT_BIN.endswith('.exe'):
                 cmd[0] += '.exe'
                 
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Network built successfully!")
            print(result.stdout)
        else:
            print("❌ Error building network:")
            print(result.stderr)
            
    except Exception as e:
        print(f"Failed to run netconvert: {e}")
        print("Make sure SUMO_HOME is set correctly in environment variables.")

if __name__ == "__main__":
    create_nodes_file()
    create_edges_file()
    build_network()
