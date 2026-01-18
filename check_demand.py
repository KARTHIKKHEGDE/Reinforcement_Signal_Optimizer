"""
Check Demand Script
===================
Debugs demand generation and verifies CSV loading.
"""
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.demand.demand_generator import demand_generator
from app.demand.csv_loader import csv_loader

def check_location(location):
    print(f"\n🔍 Checking demand for {location}...")
    
    # 1. Check data file
    data_dir = os.path.join("backend", "data")
    csv_path = os.path.join(data_dir, location, f"{location}_arrival_rates.csv")
    
    if not os.path.exists(csv_path):
        print(f"❌ Data file NOT FOUND: {csv_path}")
        return
    else:
        print(f"✅ Data file found: {csv_path}")

    # 2. Try loading via csv_loader
    # We need to set the data_dir correctly
    csv_loader.data_dir = data_dir
    success = csv_loader.load_location_data(location)
    
    if not success:
        print(f"❌ Failed to load data for {location}")
        return

    # 3. Test demand generation for Peak Hour (9:00 - 10:00)
    try:
        vehicles, summary = demand_generator.generate_demand(
            location=location,
            start_hour=9,
            start_minute=0,
            end_hour=10,
            end_minute=0
        )
        
        print(f"✅ Generated {len(vehicles)} vehicles")
        if vehicles:
            print(f"   First vehicle: {vehicles[0]}")
            print(f"   Last vehicle: {vehicles[-1]}")
    except IndexError as e:
        print(f"❌ IndexError during demand generation: {e}")
    except Exception as e:
        print(f"❌ Error during demand generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    locations = ["silk_board", "tin_factory", "hebbal"]
    for loc in locations:
        check_location(loc)
