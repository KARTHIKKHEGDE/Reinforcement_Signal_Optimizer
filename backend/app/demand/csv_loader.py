"""
CSV Loader
==========
Reads real traffic data from CSV files.
This is the single source of truth for vehicle demand.
"""
import os
import csv
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class HourlyData:
    """Traffic data for a specific hour"""
    hour: int
    time_slot: str
    total_vehicles: int
    north: float
    south: float
    east: float
    west: float
    congestion_km: float


class CSVLoader:
    """
    Loads and parses real traffic data from CSV files.
    
    Supported file formats:
    - {location}_arrival_rates.csv - Contains hourly arrival rates
    - {location}_hourly_avg.csv - Contains hourly averages
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.location_data: Dict[str, List[HourlyData]] = {}
        
    def load_location_data(self, location: str) -> bool:
        """
        Load all traffic data for a location.
        
        Args:
            location: Location key (silk_board, tin_factory, hebbal)
            
        Returns:
            bool: True if loaded successfully
        """
        arrival_rates_path = os.path.join(
            self.data_dir,
            location,
            f"{location}_arrival_rates.csv"
        )
        
        if not os.path.exists(arrival_rates_path):
            print(f"❌ Data file not found: {arrival_rates_path}")
            return False
            
        try:
            hourly_data = []
            
            with open(arrival_rates_path, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    hour = int(row.get('hour', 0))
                    
                    # Calculate vehicles per hour from lambda
                    # lambda_per_hour column gives vehicles/hour directly
                    total_vph = int(float(row.get('lambda_per_hour', 0)))
                    
                    hourly_data.append(HourlyData(
                        hour=hour,
                        time_slot=row.get('time_slot', 'unknown'),
                        total_vehicles=total_vph,
                        north=float(row.get('north', 0)),
                        south=float(row.get('south', 0)),
                        east=float(row.get('east', 0)),
                        west=float(row.get('west', 0)),
                        congestion_km=float(row.get('avg_congestion_km', 0))
                    ))
            
            self.location_data[location] = hourly_data
            print(f"✅ Loaded {len(hourly_data)} hours of data for {location}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def get_hourly_data(self, location: str, hour: int) -> Optional[HourlyData]:
        """Get data for a specific hour"""
        if location not in self.location_data:
            if not self.load_location_data(location):
                return None
                
        for data in self.location_data.get(location, []):
            if data.hour == hour:
                return data
        return None
    
    def get_vehicles_for_time_window(
        self,
        location: str,
        start_hour: int,
        start_minute: int,
        end_hour: int,
        end_minute: int
    ) -> Dict:
        """
        Calculate exact vehicle count for a time window.
        
        Example:
            start: 08:10
            end: 08:25
            Duration: 15 minutes
            If hour 8 has 5200 vehicles/hour:
            Vehicles = (5200 / 60) * 15 = 1300 vehicles
        
        Args:
            location: Location key
            start_hour: Start hour (0-23)
            start_minute: Start minute (0-59)
            end_hour: End hour (0-23)  
            end_minute: End minute (0-59)
            
        Returns:
            Dict with vehicle counts per direction
        """
        if location not in self.location_data:
            if not self.load_location_data(location):
                return {}
        
        # Calculate total duration in minutes
        start_total = start_hour * 60 + start_minute
        end_total = end_hour * 60 + end_minute
        
        if end_total <= start_total:
            print("❌ End time must be after start time")
            return {}
        
        # Initialize totals
        total_vehicles = 0
        direction_vehicles = {'north': 0, 'south': 0, 'east': 0, 'west': 0}
        
        # Process each hour that overlaps with the time window
        current_minute = start_total
        
        while current_minute < end_total:
            current_hour = current_minute // 60
            
            # How many minutes of this hour are we using?
            hour_start = max(current_minute, current_hour * 60)
            hour_end = min(end_total, (current_hour + 1) * 60)
            minutes_in_hour = hour_end - hour_start
            
            # Get data for this hour
            hour_data = self.get_hourly_data(location, current_hour)
            
            if hour_data:
                # Calculate pro-rated vehicles
                fraction = minutes_in_hour / 60.0
                hour_vehicles = int(hour_data.total_vehicles * fraction)
                total_vehicles += hour_vehicles
                
                # Calculate direction breakdown
                total_rate = hour_data.north + hour_data.south + hour_data.east + hour_data.west
                if total_rate > 0:
                    direction_vehicles['north'] += int(hour_vehicles * (hour_data.north / total_rate))
                    direction_vehicles['south'] += int(hour_vehicles * (hour_data.south / total_rate))
                    direction_vehicles['east'] += int(hour_vehicles * (hour_data.east / total_rate))
                    direction_vehicles['west'] += int(hour_vehicles * (hour_data.west / total_rate))
            
            # Move to next hour
            current_minute = hour_end
        
        return {
            'location': location,
            'start_time': f"{start_hour:02d}:{start_minute:02d}",
            'end_time': f"{end_hour:02d}:{end_minute:02d}",
            'duration_minutes': end_total - start_total,
            'total_vehicles': total_vehicles,
            'by_direction': direction_vehicles
        }
    
    def get_available_hours(self, location: str) -> List[Dict]:
        """Get list of hours with their traffic intensity"""
        if location not in self.location_data:
            if not self.load_location_data(location):
                return []
                
        result = []
        for data in self.location_data.get(location, []):
            result.append({
                'hour': data.hour,
                'time_label': f"{data.hour:02d}:00",
                'time_slot': data.time_slot,
                'vehicles_per_hour': data.total_vehicles,
                'congestion_km': data.congestion_km,
                'intensity': self._classify_intensity(data.total_vehicles)
            })
        
        return result
    
    def _classify_intensity(self, vph: int) -> str:
        """Classify traffic intensity based on vehicles per hour"""
        if vph > 5000:
            return 'critical'
        elif vph > 3000:
            return 'high'
        elif vph > 1000:
            return 'moderate'
        else:
            return 'low'


# Global instance
csv_loader = CSVLoader(data_dir="data")
