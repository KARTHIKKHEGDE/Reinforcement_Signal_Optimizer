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


class SimulationRequest(BaseModel):
    mode: Literal["fixed", "rl"]
    use_gui: bool = True


class SimulationResponse(BaseModel):
    status: str
    message: str
    mode: str = None


@router.post("/start", response_model=SimulationResponse)
async def start_simulation(request: SimulationRequest):
    """
    Start SUMO simulation
    
    Args:
        mode: "fixed" for fixed-time control, "rl" for reinforcement learning
        use_gui: Whether to show SUMO GUI
        
    Returns:
        Simulation status
    """
    try:
        # Check if already running
        if sumo_runner.is_running:
            raise HTTPException(status_code=400, detail="Simulation is already running")
        
        # Start SUMO process
        success = sumo_runner.start(use_gui=request.use_gui)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to start SUMO")
        
        # Wait for SUMO to initialize
        await asyncio.sleep(2)
        
        # Connect TraCI
        traci_connected = traci_handler.connect()
        if not traci_connected:
            sumo_runner.stop()
            raise HTTPException(status_code=500, detail="Failed to connect to SUMO via TraCI")
        
        # Start broadcasting metrics
        asyncio.create_task(manager.start_broadcasting())
        
        return SimulationResponse(
            status="success",
            message=f"Simulation started in {request.mode} mode",
            mode=request.mode
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
