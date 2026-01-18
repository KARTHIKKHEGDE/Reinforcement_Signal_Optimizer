"""
Dual Simulation API Routes
==========================
Endpoints for controlling the dual SUMO simulation (Fixed vs RL).

IMPORTANT: Vehicle demand comes ONLY from CSV.
- RL cannot influence arrivals
- Both controllers use SAME route file
- User MUST specify time window before simulation
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, validator
from typing import Literal, Optional, List
import asyncio
import os
from app.sumo.dual_orchestrator import dual_orchestrator
from app.dual_websocket import dual_manager
from app.demand.csv_loader import csv_loader
from app.demand.demand_generator import demand_generator


router = APIRouter(prefix="/api/dual", tags=["dual-simulation"])


class TimeWindow(BaseModel):
    """Time window for simulation"""
    start_hour: int
    start_minute: int = 0
    end_hour: int
    end_minute: int = 0
    
    @validator('start_hour', 'end_hour')
    def validate_hours(cls, v):
        if not 0 <= v <= 23:
            raise ValueError('Hour must be between 0 and 23')
        return v
    
    @validator('start_minute', 'end_minute')
    def validate_minutes(cls, v):
        if not 0 <= v <= 59:
            raise ValueError('Minute must be between 0 and 59')
        return v


class DualStartRequest(BaseModel):
    """
    Request to start dual simulation.
    
    REQUIRED:
    - location: Which junction to simulate
    - time_window: Start and end time (vehicles come from CSV)
    """
    location: str = "silk_board"
    time_window: TimeWindow
    use_gui: bool = True
    seed: int = 42  # For reproducibility


class DemandPreviewRequest(BaseModel):
    """Request to preview demand without starting simulation"""
    location: str
    time_window: TimeWindow


class DualResponse(BaseModel):
    """Response from dual simulation operations"""
    status: str
    message: str
    details: Optional[dict] = None


class EmergencyRequest(BaseModel):
    """Request to inject emergency vehicle"""
    vehicle_type: Literal["ambulance", "fire_truck", "police"] = "ambulance"


class WeatherRequest(BaseModel):
    """Request to apply weather condition"""
    condition: Literal["clear", "rain", "fog", "storm"] = "clear"


# ==================== DEMAND ENDPOINTS ====================

@router.get("/locations")
async def get_available_locations():
    """Get list of available simulation locations"""
    locations = [
        {"id": "silk_board", "name": "Silk Board Junction", "city": "Bangalore"},
        {"id": "tin_factory", "name": "Tin Factory Junction", "city": "Bangalore"},
        {"id": "hebbal", "name": "Hebbal Flyover", "city": "Bangalore"}
    ]
    return {"locations": locations}


@router.get("/hours/{location}")
async def get_available_hours(location: str):
    """
    Get available hours with traffic data for a location.
    
    Returns real traffic statistics from CSV.
    """
    hours = csv_loader.get_available_hours(location)
    
    if not hours:
        raise HTTPException(
            status_code=404,
            detail=f"No traffic data found for location: {location}"
        )
    
    return {
        "location": location,
        "hours": hours,
        "note": "vehicle_counts are from REAL traffic data"
    }


@router.post("/preview-demand")
async def preview_demand(request: DemandPreviewRequest):
    """
    Preview the vehicle demand for a time window WITHOUT starting simulation.
    
    Use this to show user exactly how many vehicles will spawn.
    """
    tw = request.time_window
    
    demand_info = csv_loader.get_vehicles_for_time_window(
        request.location,
        tw.start_hour, tw.start_minute,
        tw.end_hour, tw.end_minute
    )
    
    if not demand_info:
        raise HTTPException(
            status_code=404,
            detail=f"No data for {request.location} at specified time"
        )
    
    return {
        "status": "preview",
        "message": "This is what will be simulated",
        "demand": demand_info,
        "note": "These are EXACT counts from real traffic data"
    }


# ==================== SIMULATION CONTROL ====================

@router.post("/start", response_model=DualResponse)
async def start_dual_simulation(request: DualStartRequest):
    """
    Start DUAL simulation (Fixed vs RL side by side).
    
    WORKFLOW:
    1. Read CSV for exact vehicle counts
    2. Generate shared route file (BOTH controllers use this)
    3. Start two SUMO instances
    4. RL can only control signals, NOT arrivals
    
    This ensures FAIR, REPRODUCIBLE comparison.
    """
    try:
        if dual_orchestrator.is_running:
            raise HTTPException(
                status_code=400,
                detail="Dual simulation already running. Stop it first."
            )
        
        tw = request.time_window
        
        print("=" * 60)
        print("🚀 STARTING DUAL SIMULATION")
        print("=" * 60)
        print(f"   Location: {request.location}")
        print(f"   Time: {tw.start_hour:02d}:{tw.start_minute:02d} → {tw.end_hour:02d}:{tw.end_minute:02d}")
        print(f"   Seed: {request.seed}")
        
        # STEP 1: Generate demand from CSV
        print("\n📊 STEP 1: Generating demand from real traffic data...")
        
        # Reset generator with specified seed
        demand_generator.seed = request.seed
        import random
        random.seed(request.seed)
        
        vehicles, summary = demand_generator.generate_demand(
            location=request.location,
            start_hour=tw.start_hour,
            start_minute=tw.start_minute,
            end_hour=tw.end_hour,
            end_minute=tw.end_minute
        )
        
        if not vehicles:
            raise HTTPException(
                status_code=400,
                detail=f"No vehicles generated for {request.location}. Check CSV data."
            )
        
        # STEP 2: Write shared route file
        print("\n📁 STEP 2: Writing shared route file...")
        
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        route_output = os.path.join(
            current_dir, "sumo", "network", "routes_demand.rou.xml"
        )
        
        success = demand_generator.write_route_file(vehicles, route_output, summary)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate route file"
            )
        
        # STEP 3: Update SUMO config to use this route file
        print("\n⚙️ STEP 3: Updating SUMO configuration...")
        update_sumo_config_for_demand(request.location, "routes_demand.rou.xml")
        
        # STEP 4: Start both SUMO instances
        print("\n🎮 STEP 4: Starting SUMO instances...")
        
        success = dual_orchestrator.start_dual_simulation(
            location=request.location, 
            use_gui=request.use_gui
        )
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to start dual simulation"
            )
        
        # STEP 5: Start broadcasting
        print("\n📡 STEP 5: Starting metrics broadcast...")
        await asyncio.sleep(1)
        
        asyncio.create_task(
            dual_manager.start_dual_broadcasting(intensity="peak")
        )
        
        print("\n" + "=" * 60)
        print("✅ DUAL SIMULATION RUNNING")
        print("=" * 60)
        print(f"   Vehicles spawned: {len(vehicles)}")
        print(f"   Route file: routes_demand.rou.xml")
        print(f"   Seed: {request.seed}")
        print("   RL controls SIGNALS only, not arrivals")
        print("=" * 60)
        
        return DualResponse(
            status="success",
            message=f"Dual simulation started with {len(vehicles)} vehicles",
            details={
                **dual_orchestrator.get_status(),
                "demand_summary": summary,
                "seed": request.seed,
                "route_file": "routes_demand.rou.xml",
                "note": "Both controllers use IDENTICAL vehicle demand"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def update_sumo_config_for_demand(location: str, route_file: str):
    """Update simulation.sumocfg to use the demand-generated route file"""
    import xml.etree.ElementTree as ET
    
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(current_dir, "sumo", "network", "simulation.sumocfg")
    
    # Network file mapping
    net_files = {
        "silk_board": "silk_board.net.xml",
        "tin_factory": "tin_factory.net.xml",
        "hebbal": "hebbal.net.xml"
    }
    
    net_file = net_files.get(location, "silk_board.net.xml")
    
    try:
        tree = ET.parse(config_path)
        root = tree.getroot()
        
        input_elem = root.find("input")
        if input_elem is not None:
            net_elem = input_elem.find("net-file")
            if net_elem is not None:
                net_elem.set("value", net_file)
            
            route_elem = input_elem.find("route-files")
            if route_elem is not None:
                route_elem.set("value", route_file)
        
        tree.write(config_path, encoding="UTF-8", xml_declaration=True)
        print(f"   ✓ Config updated: {net_file} + {route_file}")
        
    except Exception as e:
        print(f"   ⚠️ Error updating config: {e}")


@router.post("/stop", response_model=DualResponse)
async def stop_dual_simulation():
    """Stop both SUMO simulations and clean up properly"""
    print("🛑 Stopping dual simulation...")
    dual_manager.stop_broadcasting()
    dual_orchestrator.stop_all()
    
    # Give time for complete cleanup
    await asyncio.sleep(2)
    
    print("✅ Dual simulation stopped and cleaned up")
    
    return DualResponse(
        status="success",
        message="Dual simulation stopped"
    )


@router.get("/status")
async def get_dual_status():
    """Get status of both simulations"""
    return dual_orchestrator.get_status()


# ==================== DURING-SIMULATION CONTROLS ====================

@router.post("/emergency", response_model=DualResponse)
async def inject_emergency(request: EmergencyRequest):
    """
    Inject emergency vehicle into BOTH simulations.
    
    This is ALLOWED because:
    - Externally triggered (user action)
    - Symmetric (same in both)
    - Logged separately
    """
    if not dual_orchestrator.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running")
    
    success = dual_orchestrator.inject_emergency_vehicle(
        route_id="emergency_route",
        vehicle_type=request.vehicle_type
    )
    
    return DualResponse(
        status="success" if success else "error",
        message=f"Emergency {request.vehicle_type} injected into BOTH simulations",
        details={"vehicle_type": request.vehicle_type, "injected_to": "both"}
    )


@router.post("/weather", response_model=DualResponse)
async def apply_weather(request: WeatherRequest):
    """
    Apply weather condition to BOTH simulations.
    
    Weather affects vehicle SPEEDS, not arrivals.
    """
    if not dual_orchestrator.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running")
    
    success = dual_orchestrator.apply_weather_condition(request.condition)
    
    return DualResponse(
        status="success" if success else "error",
        message=f"Weather '{request.condition}' applied to BOTH simulations"
    )


@router.post("/signal/{junction_id}/phase/{phase}")
async def set_signal_phase(junction_id: str, phase: int, target: str = "both"):
    """
    Manually set traffic light phase.
    
    This is for TESTING only. In normal operation:
    - FIXED uses predefined timing
    - RL uses learned policy
    """
    if not dual_orchestrator.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running")
    
    success = dual_orchestrator.set_traffic_light_phase(junction_id, phase, target)
    
    return {"status": "success" if success else "error", "junction": junction_id, "phase": phase}
