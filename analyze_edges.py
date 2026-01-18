import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
import json

def analyze_routes(file_path):
    print(f"Analyzing {file_path}")
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        starts = []
        ends = []
        for vehicle in root.findall('vehicle'):
            route = vehicle.find('route')
            if route is not None:
                edges = route.get('edges').split()
                if edges:
                    starts.append(edges[0])
                    ends.append(edges[-1])
        return {
            "entries": [e for e, c in Counter(starts).most_common(5)],
            "exits": [e for e, c in Counter(ends).most_common(5)]
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

network_dir = Path("backend/app/sumo/network")
results = {
    "silk_board": analyze_routes(network_dir / "routes_silk_board.rou.xml"),
    "hebbal": analyze_routes(network_dir / "routes_hebbal.rou.xml"),
    "tin_factory": analyze_routes(network_dir / "routes_tin_factory.rou.xml")
}

with open("edge_results.json", "w") as f:
    json.dump(results, f, indent=4)
print("Saved to edge_results.json")
