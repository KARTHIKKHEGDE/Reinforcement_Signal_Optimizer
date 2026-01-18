"""
Demand Generator
================
Creates SUMO-ready vehicle spawn schedules from real traffic data.

This is the CRITICAL module that ensures:
- Exact vehicle counts from CSV
- Same demand for both Fixed and RL controllers  
- Research-grade reproducibility

RULE: RL must NEVER influence arrivals. Only signal control.
"""
import os
import random
from typing import Dict, List, Tuple
from dataclasses import dataclass
from app.demand.csv_loader import csv_loader, HourlyData


@dataclass
class VehicleSpawn:
    """A single vehicle spawn event"""
    vehicle_id: str
    spawn_time: float  # Seconds from simulation start
    from_edge: str
    to_edge: str
    vehicle_type: str


class DemandGenerator:
    """
    Generates exact vehicle spawn schedules from CSV data.
    """
    
    # Vehicle type distribution
    VEHICLE_TYPES = [
        ('car', 0.70),
        ('motorcycle', 0.15),
        ('bus', 0.05),
        ('truck', 0.10)
    ]
    
    # Edge mapping for each location based on network analysis
    # Format: { location: { direction: (entry_edge, exit_edge) } }
    # We map North -> South, South -> North, East -> West, West -> East as primary flows
    LOCATION_EDGES = {
        'silk_board': {
            'north': ('491889865#0', '519734960'),     # N entry -> S exit
            'south': ('-1424147361', '464465162#1'),  # S entry -> N exit
            'east': ('27994464#0', '-27994446#0'),    # E entry -> W exit
            'west': ('-40696199#1', '688608667')       # W entry -> E exit
        },
        'tin_factory': {
            'north': ('799366215', '-1103814252#0'),  # N entry -> S exit
            'south': ('-1182409051#1', '1182408480'), # S entry -> N exit
            'east': ('-1183856191', '155830602#3'),  # E entry -> W exit
            'west': ('142865622#0', '338103118')       # W entry -> E exit
        },
        'hebbal': {
            'north': ('114817854#0', '326557690#17'), # N entry -> S exit
            'south': ('-667001220#1', '-1182399616'), # S entry -> N exit
            'east': ('-995100109', '-1102785244'),    # E entry -> W exit
            'west': ('325929768#0', '1102785245')      # W entry -> E exit
        }
    }
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        
    def generate_demand(
        self,
        location: str,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int
    ) -> Tuple[List[VehicleSpawn], Dict]:
        """Generate exact vehicle spawn schedule for a time window."""
        demand_info = csv_loader.get_vehicles_for_time_window(
            location, start_hour, start_minute, end_hour, end_minute
        )
        
        if not demand_info or demand_info['total_vehicles'] == 0:
            return [], {}
        
        total_vehicles = demand_info['total_vehicles']
        duration_seconds = demand_info['duration_minutes'] * 60
        by_direction = demand_info['by_direction']
        
        # Get edges for this location
        edges_map = self.LOCATION_EDGES.get(location, self.LOCATION_EDGES['silk_board'])
        
        vehicles = []
        vehicle_id = 0
        
        for direction, count in by_direction.items():
            if count <= 0:
                continue
                
            spawn_times = self._generate_poisson_arrivals(count, duration_seconds)
            
            # Get edges for this direction
            entry, exit_edge = edges_map.get(direction, edges_map['north'])
            
            for spawn_time in spawn_times:
                vehicle_id += 1
                veh_type = self._choose_vehicle_type()
                
                # Add some variation in exit edges (20% chance to turn)
                actual_exit = exit_edge
                if random.random() < 0.20:
                    other_exits = [e[1] for d, e in edges_map.items() if d != direction]
                    if other_exits:
                        actual_exit = random.choice(other_exits)
                
                vehicles.append(VehicleSpawn(
                    vehicle_id=f"v_{direction[0]}_{vehicle_id}",
                    spawn_time=round(spawn_time, 1),
                    from_edge=entry,
                    to_edge=actual_exit,
                    vehicle_type=veh_type
                ))
        
        vehicles.sort(key=lambda v: v.spawn_time)
        
        summary = {
            **demand_info,
            'actual_vehicles_generated': len(vehicles),
            'seed': self.seed
        }
        
        print(f"✅ Generated {len(vehicles)} vehicles for {location}")
        return vehicles, summary
    
    def _generate_poisson_arrivals(self, count: int, duration: float) -> List[float]:
        if count <= 0: return []
        rate = count / duration
        times = []
        current_time = 0
        while len(times) < count:
            interval = random.expovariate(rate) if rate > 0 else 1.0
            current_time += interval
            if current_time < duration:
                times.append(current_time)
            else:
                # Add remaining vehicles spread out if we hit the duration limit
                remaining = count - len(times)
                for _ in range(remaining):
                    times.append(random.uniform(0, duration))
                break
        return sorted(times)[:count]
    
    def _choose_vehicle_type(self) -> str:
        r = random.random()
        cumulative = 0.0
        for veh_type, prob in self.VEHICLE_TYPES:
            cumulative += prob
            if r <= cumulative:
                return veh_type
        return 'car'
    
    def write_route_file(
        self,
        vehicles: List[VehicleSpawn],
        output_path: str,
        summary: Dict
    ) -> bool:
        """Write SUMO route file using TRIPS instead of ROUTES for path flexibility."""
        try:
            location = summary.get("location", "silk_board")
            edges_map = self.LOCATION_EDGES.get(location, self.LOCATION_EDGES['silk_board'])
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
                f.write('xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">\n\n')
                
                f.write('    <!-- Vehicle Types -->\n')
                f.write('    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="4.5" maxSpeed="50" guiShape="passenger"/>\n')
                f.write('    <vType id="motorcycle" accel="4.0" decel="6.0" sigma="0.5" length="2.0" maxSpeed="60" guiShape="motorcycle"/>\n')
                f.write('    <vType id="bus" accel="1.2" decel="3.0" sigma="0.5" length="12.0" maxSpeed="30" guiShape="bus"/>\n')
                f.write('    <vType id="truck" accel="1.0" decel="3.0" sigma="0.5" length="10.0" maxSpeed="25" guiShape="truck"/>\n')
                f.write('    <vType id="emergency" accel="3.0" decel="5.0" sigma="0.3" length="5.5" maxSpeed="60" guiShape="emergency" vClass="emergency" color="1,0,0"/>\n\n')
                
                # Vehicle departures using <trip> instead of <vehicle>
                # Using trip allows SUMO to calculate the path dynamically
                f.write(f'    <!-- Vehicle Trips ({len(vehicles)} total) -->\n')
                for veh in vehicles:
                    f.write(f'    <trip id="{veh.vehicle_id}" type="{veh.vehicle_type}" depart="{veh.spawn_time}" ')
                    f.write(f'from="{veh.from_edge}" to="{veh.to_edge}" ')
                    f.write('departLane="best" departSpeed="max"/>\n')
                
                f.write('\n</routes>\n')
            
            print(f"✅ Route file (trips) written: {output_path}")
            return True
        except Exception as e:
            print(f"❌ Error writing route file: {e}")
            return False


demand_generator = DemandGenerator(seed=42)

