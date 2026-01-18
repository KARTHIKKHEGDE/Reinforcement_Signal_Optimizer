"""
Dynamic Route Generator from Real Data
=======================================
Generates SUMO route files (.rou.xml) from real-world arrival rate CSVs.

Uses the arrival_rates.csv files containing hourly vehicle arrival rates 
per direction (North, South, East, West) to create realistic traffic demand.

This ensures simulations match real-world congestion patterns.
"""
import os
import csv
import random
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class VehicleSpawn:
    """Represents a vehicle to spawn in simulation"""
    vehicle_id: str
    depart_time: float
    route_id: str
    vehicle_type: str = "car"


class DynamicRouteGenerator:
    """
    Generates SUMO routes from real arrival rate data.
    
    Flow:
    1. Read arrival_rates.csv for chosen location
    2. Get rates for chosen simulation hour
    3. Generate vehicle departures matching those rates
    4. Write to temporary route file
    """
    
    # Vehicle type distribution
    VEHICLE_TYPES = {
        "car": 0.70,       # 70% cars
        "bus": 0.05,       # 5% buses
        "motorcycle": 0.15, # 15% motorcycles
        "truck": 0.10      # 10% trucks
    }
    
    # Route IDs for each direction (must match network edges)
    DIRECTION_ROUTES = {
        "north": "route_north",
        "south": "route_south", 
        "east": "route_east",
        "west": "route_west"
    }
    
    def __init__(self, data_dir: str = "data"):
        """
        Args:
            data_dir: Base directory containing location subdirectories
        """
        self.data_dir = data_dir
        self.arrival_rates: Dict[str, float] = {}
        self.current_hour: int = 8  # Default to morning peak
        self.current_location: str = "silk_board"
        
    def load_arrival_rates(self, location: str) -> bool:
        """
        Load arrival rates CSV for a location.
        
        Args:
            location: Location key (e.g., 'silk_board', 'tin_factory')
            
        Returns:
            bool: True if loaded successfully
        """
        self.current_location = location
        csv_path = os.path.join(
            self.data_dir, 
            location, 
            f"{location}_arrival_rates.csv"
        )
        
        if not os.path.exists(csv_path):
            print(f"⚠️ Arrival rates not found: {csv_path}")
            return False
            
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                self.rate_data = list(reader)
            print(f"✅ Loaded arrival rates for {location}: {len(self.rate_data)} hours")
            return True
        except Exception as e:
            print(f"❌ Error loading rates: {e}")
            return False
    
    def get_rates_for_hour(self, hour: int) -> Dict[str, float]:
        """
        Get arrival rates for a specific hour.
        
        Args:
            hour: Hour of day (0-23)
            
        Returns:
            Dict with rates per direction: {'north': 0.5, 'south': 0.6, ...}
        """
        self.current_hour = hour
        
        for row in self.rate_data:
            if int(row.get('hour', -1)) == hour:
                return {
                    'north': float(row.get('north', 0)),
                    'south': float(row.get('south', 0)),
                    'east': float(row.get('east', 0)),
                    'west': float(row.get('west', 0)),
                    'total': float(row.get('total_lambda_final', 0))
                }
        
        # Default rates if hour not found
        print(f"⚠️ Hour {hour} not found, using defaults")
        return {'north': 0.3, 'south': 0.3, 'east': 0.2, 'west': 0.2, 'total': 1.0}
    
    def get_available_hours(self) -> List[Dict]:
        """
        Get list of available hours with their traffic intensity.
        
        Returns:
            List of dicts with hour info for UI display
        """
        hours = []
        for row in self.rate_data:
            hour = int(row.get('hour', 0))
            total = float(row.get('total_lambda_final', 0))
            time_slot = row.get('time_slot', 'unknown')
            
            # Classify intensity
            if total > 2.0:
                intensity = "critical"
            elif total > 1.0:
                intensity = "high"
            elif total > 0.5:
                intensity = "moderate"
            else:
                intensity = "low"
                
            hours.append({
                'hour': hour,
                'time_label': f"{hour:02d}:00",
                'time_slot': time_slot,
                'total_rate': round(total, 3),
                'vehicles_per_hour': int(total * 3600),
                'intensity': intensity
            })
        
        return hours
    
    def generate_vehicles(
        self, 
        hour: int, 
        simulation_duration: int = 3600
    ) -> List[VehicleSpawn]:
        """
        Generate vehicle spawn list for a specific hour.
        
        Args:
            hour: Hour to simulate (0-23)
            simulation_duration: Duration in seconds
            
        Returns:
            List of VehicleSpawn objects
        """
        rates = self.get_rates_for_hour(hour)
        vehicles = []
        vehicle_counter = 0
        
        print(f"📊 Generating vehicles for hour {hour}:00")
        print(f"   Rates: N={rates['north']:.3f}, S={rates['south']:.3f}, "
              f"E={rates['east']:.3f}, W={rates['west']:.3f}")
        
        for direction in ['north', 'south', 'east', 'west']:
            rate = rates.get(direction, 0)
            if rate <= 0:
                continue
                
            # Calculate inter-arrival time (Poisson process)
            avg_interval = 1.0 / rate if rate > 0 else 10.0
            
            current_time = 0.0
            while current_time < simulation_duration:
                # Exponential inter-arrival time
                interval = random.expovariate(rate) if rate > 0 else avg_interval
                current_time += interval
                
                if current_time >= simulation_duration:
                    break
                
                # Choose vehicle type
                veh_type = self._choose_vehicle_type()
                
                vehicle_counter += 1
                vehicles.append(VehicleSpawn(
                    vehicle_id=f"veh_{direction}_{vehicle_counter}",
                    depart_time=round(current_time, 1),
                    route_id=f"route_{direction}",
                    vehicle_type=veh_type
                ))
        
        # Sort by departure time
        vehicles.sort(key=lambda v: v.depart_time)
        
        print(f"   ✅ Generated {len(vehicles)} vehicles")
        return vehicles
    
    def _choose_vehicle_type(self) -> str:
        """Choose vehicle type based on distribution"""
        r = random.random()
        cumulative = 0.0
        for veh_type, prob in self.VEHICLE_TYPES.items():
            cumulative += prob
            if r <= cumulative:
                return veh_type
        return "car"
    
    def generate_route_file(
        self, 
        location: str,
        hour: int,
        output_path: str,
        simulation_duration: int = 3600
    ) -> bool:
        """
        Generate a complete SUMO route file for a specific hour.
        
        Args:
            location: Location key
            hour: Hour to simulate
            output_path: Where to save the .rou.xml file
            simulation_duration: Simulation length in seconds
            
        Returns:
            bool: True if generated successfully
        """
        # Load rates
        if not self.load_arrival_rates(location):
            return False
        
        # Generate vehicles
        vehicles = self.generate_vehicles(hour, simulation_duration)
        
        if not vehicles:
            print("⚠️ No vehicles generated!")
            return False
        
        # Write XML
        try:
            with open(output_path, 'w') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ')
                f.write('xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">\n\n')
                
                # Vehicle types
                f.write('    <!-- Vehicle Types -->\n')
                f.write('    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" ')
                f.write('length="4.5" maxSpeed="50" guiShape="passenger"/>\n')
                f.write('    <vType id="bus" accel="1.2" decel="3.0" sigma="0.5" ')
                f.write('length="12.0" maxSpeed="30" guiShape="bus"/>\n')
                f.write('    <vType id="motorcycle" accel="4.0" decel="6.0" sigma="0.5" ')
                f.write('length="2.0" maxSpeed="60" guiShape="motorcycle"/>\n')
                f.write('    <vType id="truck" accel="1.0" decel="3.0" sigma="0.5" ')
                f.write('length="10.0" maxSpeed="25" guiShape="truck"/>\n')
                f.write('    <vType id="ambulance" accel="3.0" decel="5.0" sigma="0.3" ')
                f.write('length="5.5" maxSpeed="60" guiShape="emergency" ')
                f.write('vClass="emergency" color="1,0,0"/>\n\n')
                
                # Write vehicle departures
                f.write(f'    <!-- Vehicles for Hour {hour}:00 ({len(vehicles)} total) -->\n')
                f.write(f'    <!-- Location: {location}, Generated from real arrival rates -->\n\n')
                
                for veh in vehicles:
                    f.write(f'    <vehicle id="{veh.vehicle_id}" type="{veh.vehicle_type}" ')
                    f.write(f'depart="{veh.depart_time}" route="{veh.route_id}"/>\n')
                
                f.write('\n</routes>\n')
            
            print(f"✅ Route file generated: {output_path}")
            print(f"   Location: {location}")
            print(f"   Hour: {hour}:00")
            print(f"   Vehicles: {len(vehicles)}")
            return True
            
        except Exception as e:
            print(f"❌ Error writing route file: {e}")
            return False
    
    def get_hour_summary(self, location: str, hour: int) -> Dict:
        """
        Get summary info for a specific hour.
        
        Returns:
            Dict with hour details for display
        """
        if not self.load_arrival_rates(location):
            return {}
            
        rates = self.get_rates_for_hour(hour)
        
        # Find time slot
        time_slot = "unknown"
        for row in self.rate_data:
            if int(row.get('hour', -1)) == hour:
                time_slot = row.get('time_slot', 'unknown')
                break
        
        total_vph = int(rates['total'] * 3600)
        
        return {
            'hour': hour,
            'time_label': f"{hour:02d}:00",
            'time_slot': time_slot,
            'rates': rates,
            'vehicles_per_hour': total_vph,
            'intensity': 'critical' if total_vph > 7000 else 'high' if total_vph > 3500 else 'moderate'
        }


# Global instance
route_generator = DynamicRouteGenerator(data_dir="data")


if __name__ == "__main__":
    # Test generation
    gen = DynamicRouteGenerator(data_dir="backend/data")
    
    # Load and show available hours
    gen.load_arrival_rates("silk_board")
    hours = gen.get_available_hours()
    
    print("\n📋 Available simulation hours:")
    print("-" * 60)
    for h in hours:
        print(f"  {h['time_label']} ({h['time_slot']:15s}) | "
              f"{h['vehicles_per_hour']:5d} veh/hr | {h['intensity']}")
    
    # Generate sample route file
    gen.generate_route_file(
        location="silk_board",
        hour=8,  # 8 AM peak
        output_path="backend/app/sumo/network/routes_dynamic.rou.xml",
        simulation_duration=3600
    )
