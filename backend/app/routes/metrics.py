"""
Metrics routes
Expose historical and current simulation metrics
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from app.sumo.traci_handler import traci_handler


router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/current")
async def get_current_metrics():
    """
    Get current simulation metrics
    
    Returns:
        Current real-time metrics
    """
    try:
        if not traci_handler.connected:
            raise HTTPException(status_code=400, detail="Simulation is not running")
        
        metrics = traci_handler.get_metrics()
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")


@router.get("/summary")
async def get_metrics_summary():
    """
    Get summary statistics
    
    Returns:
        Summary of key metrics
    """
    try:
        if not traci_handler.connected:
            return {
                "status": "not_running",
                "message": "Simulation is not running"
            }
        
        metrics = traci_handler.get_metrics()
        
        return {
            "status": "running",
            "summary": {
                "total_vehicles": metrics["vehicle_count"],
                "average_queue": metrics["queue_length"],
                "average_waiting_time": round(metrics["waiting_time"], 2),
                "simulation_time": metrics["time"],
                "throughput": {
                    "departed": metrics["departed_vehicles"],
                    "arrived": metrics["arrived_vehicles"]
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting summary: {str(e)}")
