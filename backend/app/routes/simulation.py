"""
Simulation control routes
Start/stop SUMO with Fixed-Time or RL control
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal
import asyncio
from app.sumo.runner import sumo_runner
from app.sumo.traci_handler import traci_handler
from app.websocket import manager


router = APIRouter(prefix="/api/simulation", tags=["simulation"])


from typing import Literal, Optional
import xml.etree.ElementTree as ET
import os
import json

# Load locations data
LOCATIONS_FILE = "data/govt_congestion/locations.json"
locations_data = {}
try:
    with open(LOCATIONS_FILE, "r") as f:
        locations_data = json.load(f)
except FileNotFoundError:
    print("Warning: locations.json not found")

class SimulationRequest(BaseModel):
    mode: Literal["fixed", "rl"] = "fixed"
    use_gui: bool = True
    traffic_scenario: Literal["peak", "offpeak"] = "peak"
    location: str = "silk_board"  # Default location


class SimulationResponse(BaseModel):
    status: str
    message: str
    mode: str = None
    traffic_scenario: str = None
    location: str = None


@router.get("/locations")
async def get_locations():
    """Get available simulation locations"""
    return locations_data


def update_sumo_config(location: str):
    """Update simulation.sumocfg to use the correct network and route file"""
    try:
        config_path = "app/sumo/network/simulation.sumocfg"
        tree = ET.parse(config_path)
        root = tree.getroot()
        
        # Determine files
        # Check if real map exists, otherwise fall back to grid
        real_net = f"{location}.net.xml"
        if os.path.exists(f"app/sumo/network/{real_net}"):
            net_file = real_net
            route_file = f"routes_{location}.rou.xml"
            print(f"✅ Using Real Map: {net_file}")
        else:
            # Fallback to grid
            net_file = "network.net.xml" 
            route_file = f"routes_{location}.rou.xml"
            print(f"⚠️ Using Grid Map (Real map not found)")
        
        input_node = root.find("input")
        if input_node is not None:
            # Update Net File
            net_node = input_node.find("net-file")
            if net_node is not None:
                net_node.set("value", net_file)
            
            # Update Route File
            routes_node = input_node.find("route-files")
            if routes_node is not None:
                routes_node.set("value", route_file)
                
            tree.write(config_path)
            return True
            
    except Exception as e:
        print(f"Failed to update SUMO config: {e}")
        return False


@router.post("/start", response_model=SimulationResponse)
async def start_simulation(request: SimulationRequest):
    """
    Start SUMO simulation
    """
    try:
        # Check if already running
        if sumo_runner.is_running:
            raise HTTPException(status_code=400, detail="Simulation is already running")
        
        # Update Config for Location
        if request.location in locations_data:
            update_sumo_config(request.location)
        else:
            # Fallback to silk_board if valid location provided but not found? 
            # Or just use default routes_peak. Since we generated routes_silk_board, let's allow it.
            # If user sends "peak" (old param), likely ignored if location is sent.
            pass

        # Start SUMO process (this also initializes TraCI)
        success = sumo_runner.start(use_gui=request.use_gui)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start SUMO")
        
        # Wait for SUMO to fully initialize
        await asyncio.sleep(1)
        
        # Start broadcasting metrics
        asyncio.create_task(manager.start_broadcasting())
        
        return SimulationResponse(
            status="success",
            message=f"Simulation started in {request.mode} mode for {request.location}",
            mode=request.mode,
            traffic_scenario=request.traffic_scenario,
            location=request.location
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting simulation: {str(e)}")


@router.post("/stop", response_model=SimulationResponse)
async def stop_simulation():
    """
    Stop SUMO simulation
    
    Returns:
        Simulation status
    """
    try:
        # Stop broadcasting
        manager.stop_broadcasting()
        
        # Disconnect TraCI
        traci_handler.disconnect()
        
        # Stop SUMO
        success = sumo_runner.stop()
        if not success:
            raise HTTPException(status_code=500, detail="Failed to stop SUMO")
        
        return SimulationResponse(
            status="success",
            message="Simulation stopped successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping simulation: {str(e)}")


@router.post("/reset", response_model=SimulationResponse)
async def reset_simulation():
    """
    Reset SUMO simulation
    Stops current simulation and clears all state
    
    Returns:
        Simulation status
    """
    try:
        # Stop broadcasting
        manager.stop_broadcasting()
        
        # Disconnect TraCI
        traci_handler.disconnect()
        
        # Stop SUMO
        sumo_runner.stop()
        
        # Small delay to ensure clean shutdown
        await asyncio.sleep(1)
        
        return SimulationResponse(
            status="success",
            message="Simulation reset successfully. Ready to start new simulation."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting simulation: {str(e)}")


@router.get("/status")
async def get_simulation_status():
    """
    Get current simulation status
    
    Returns:
        Current status and metrics
    """
    try:
        sumo_status = sumo_runner.get_status()
        
        metrics = None
        if traci_handler.connected:
            metrics = traci_handler.get_metrics()
        
        return {
            "running": sumo_status["running"],
            "pid": sumo_status["pid"],
            "traci_connected": traci_handler.connected,
            "active_connections": len(manager.active_connections),
            "current_metrics": metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")
