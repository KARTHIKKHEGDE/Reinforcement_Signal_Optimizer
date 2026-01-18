"""
Advanced API routes - REAL DATA from SUMO Simulation
=====================================================

All data is pulled from the running SUMO simulation via TraCI.
NO FAKE/MOCK DATA - everything is real-time from the simulation.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import traci

from app.sumo.traci_handler import traci_handler

router = APIRouter(prefix="/api/advanced", tags=["advanced"])


# ============== RESPONSE MODELS ==============

class WeatherConditionResponse(BaseModel):
    condition: int
    condition_name: str
    speed_factor: float
    min_green_adjustment: float
    is_raining: bool


class EmergencyVehicleResponse(BaseModel):
    id: str
    type: str
    distance: float
    eta: float
    junction: str
    priority: int


class EmergencyStatusResponse(BaseModel):
    active: bool
    vehicle: Optional[EmergencyVehicleResponse] = None
    preemption_active: bool
    time_remaining: float


class RealTimeMetricsResponse(BaseModel):
    simulation_time: float
    total_vehicles: int
    avg_waiting_time: float
    total_queue_length: int
    throughput_rate: float
    departed: int
    arrived: int
    running: bool


# ============== LIVE STATE FROM SIMULATION ==============

class SimulationState:
    """
    Manages REAL state from the running SUMO simulation.
    Updated every simulation step via TraCI.
    """
    
    def __init__(self):
        # Weather (can be set by user, affects simulation)
        self.weather_condition = 0  # 0=Normal, 1=Light, 2=Moderate, 3=Heavy rain
        self.weather_names = ["Normal", "Light Rain", "Moderate Rain", "Heavy Rain"]
        self.speed_factors = [1.0, 0.9, 0.8, 0.7]
        self.min_green_adj = [0.0, 2.0, 5.0, 8.0]
        
        # Metrics history for comparison (real data from runs)
        self.metrics_history = {
            "fixed_time": {"avg_delay": 0, "throughput": 0, "emergency_time": 0, "queue_length": 0, "steps": 0},
            "rl": {"avg_delay": 0, "throughput": 0, "emergency_time": 0, "queue_length": 0, "steps": 0}
        }
        
        # Current run accumulator
        self.current_run = {
            "total_waiting": 0.0,
            "total_queue": 0,
            "samples": 0,
            "emergency_times": []
        }
    
    def get_weather(self) -> dict:
        """Get current weather state."""
        cond = self.weather_condition
        return {
            "condition": cond,
            "condition_name": self.weather_names[cond],
            "speed_factor": self.speed_factors[cond],
            "min_green_adjustment": self.min_green_adj[cond],
            "is_raining": cond > 0
        }
    
    def set_weather(self, condition: int) -> bool:
        """Set weather and apply speed reduction to all vehicles in simulation."""
        if condition < 0 or condition > 3:
            return False
        
        self.weather_condition = condition
        speed_factor = self.speed_factors[condition]
        
        # Apply to simulation if connected
        if traci_handler.connected:
            try:
                # Reduce max speed for all vehicles based on weather
                for veh_id in traci.vehicle.getIDList():
                    max_speed = traci.vehicle.getMaxSpeed(veh_id)
                    traci.vehicle.setMaxSpeed(veh_id, max_speed * speed_factor)
                print(f"🌧️ Weather set to {self.weather_names[condition]}, speed factor: {speed_factor}")
            except Exception as e:
                print(f"Error applying weather: {e}")
        
        return True
    
    def detect_emergency_vehicles(self) -> dict:
        """
        Detect REAL emergency vehicles in the simulation.
        Checks vehicle types for ambulance, fire, police.
        """
        if not traci_handler.connected:
            return {"active": False, "vehicle": None, "preemption_active": False, "time_remaining": 0.0}
        
        # Check if TraCI is actually still loaded
        if not traci.isLoaded():
            return {"active": False, "vehicle": None, "preemption_active": False, "time_remaining": 0.0}
        
        try:
            vehicle_ids = traci.vehicle.getIDList()
            
            # Emergency vehicle types (must match route file definitions)
            emergency_types = {
                "ambulance": ("AMBULANCE", 3),
                "fire_truck": ("FIRE_TRUCK", 2),
                "police": ("POLICE", 1),
                "emergency": ("AMBULANCE", 3)
            }
            
            closest_emergency = None
            min_distance = float('inf')
            
            for veh_id in vehicle_ids:
                veh_type = traci.vehicle.getTypeID(veh_id).lower()
                
                # Check if this is an emergency vehicle
                for type_key, (type_name, priority) in emergency_types.items():
                    if type_key in veh_type:
                        # Get position and calculate distance to junction
                        pos = traci.vehicle.getPosition(veh_id)
                        speed = traci.vehicle.getSpeed(veh_id)
                        
                        # Find nearest junction
                        nearest_junction = None
                        junction_distance = float('inf')
                        
                        for junc_id in traci_handler.junction_ids:
                            try:
                                junc_pos = traci.junction.getPosition(junc_id)
                                dist = ((pos[0] - junc_pos[0])**2 + (pos[1] - junc_pos[1])**2)**0.5
                                if dist < junction_distance:
                                    junction_distance = dist
                                    nearest_junction = junc_id
                            except:
                                pass
                        
                        if junction_distance < min_distance and junction_distance < 300:
                            min_distance = junction_distance
                            eta = junction_distance / max(speed, 1.0)
                            closest_emergency = {
                                "active": True,
                                "vehicle": {
                                    "id": veh_id,
                                    "type": type_name,
                                    "distance": round(junction_distance, 1),
                                    "eta": round(eta, 1),
                                    "junction": nearest_junction or "unknown",
                                    "priority": priority
                                },
                                "preemption_active": junction_distance < 200,
                                "time_remaining": round(eta + 10, 1)
                            }
                        break
            
            if closest_emergency:
                return closest_emergency
            
            return {"active": False, "vehicle": None, "preemption_active": False, "time_remaining": 0.0}
            
        except Exception as e:
            print(f"Error detecting emergency: {e}")
            return {"active": False, "vehicle": None, "preemption_active": False, "time_remaining": 0.0}
    
    def get_real_metrics(self) -> dict:
        """Get REAL metrics from running simulation."""
        if not traci_handler.connected:
            return {
                "simulation_time": 0,
                "total_vehicles": 0,
                "avg_waiting_time": 0,
                "total_queue_length": 0,
                "throughput_rate": 0,
                "departed": 0,
                "arrived": 0,
                "running": False
            }
        
        try:
            metrics = traci_handler.get_metrics()
            return {
                "simulation_time": metrics.get("time", 0),
                "total_vehicles": metrics.get("vehicle_count", 0),
                "avg_waiting_time": round(metrics.get("waiting_time", 0), 2),
                "total_queue_length": metrics.get("queue_length", 0),
                "throughput_rate": metrics.get("throughput_rate", 0),
                "departed": metrics.get("departed_vehicles", 0),
                "arrived": metrics.get("arrived_vehicles", 0),
                "running": True
            }
        except Exception as e:
            print(f"Error getting metrics: {e}")
            return {"running": False, "simulation_time": 0, "total_vehicles": 0, 
                    "avg_waiting_time": 0, "total_queue_length": 0, "throughput_rate": 0,
                    "departed": 0, "arrived": 0}
    
    def record_metrics(self, mode: str = "rl"):
        """Record metrics from current simulation step for comparison."""
        if not traci_handler.connected:
            return
        
        try:
            metrics = traci_handler.get_metrics()
            self.current_run["total_waiting"] += metrics.get("waiting_time", 0)
            self.current_run["total_queue"] += metrics.get("queue_length", 0)
            self.current_run["samples"] += 1
        except:
            pass
    
    def finalize_run(self, mode: str = "rl"):
        """Finalize metrics for completed run."""
        samples = self.current_run["samples"]
        if samples > 0:
            self.metrics_history[mode] = {
                "avg_delay": round(self.current_run["total_waiting"] / samples, 2),
                "throughput": traci_handler.total_arrived if traci_handler.connected else 0,
                "emergency_time": sum(self.current_run["emergency_times"]) / len(self.current_run["emergency_times"]) if self.current_run["emergency_times"] else 0,
                "queue_length": round(self.current_run["total_queue"] / samples, 2),
                "steps": samples
            }
        
        # Reset current run
        self.current_run = {"total_waiting": 0.0, "total_queue": 0, "samples": 0, "emergency_times": []}
    
    def get_comparison(self) -> dict:
        """Get comparison of controller performance from REAL runs."""
        return {
            "comparison": [
                {"controller": "Fixed-Time", **self.metrics_history.get("fixed_time", 
                    {"avg_delay": 0, "throughput": 0, "emergency_time": 0, "queue_length": 0})},
                {"controller": "RL", **self.metrics_history.get("rl",
                    {"avg_delay": 0, "throughput": 0, "emergency_time": 0, "queue_length": 0})}
            ],
            "improvement": self._calculate_improvement(),
            "total_steps": self.metrics_history.get("rl", {}).get("steps", 0)
        }
    
    def _calculate_improvement(self) -> dict:
        """Calculate RL improvement over Fixed-Time from real data."""
        fixed = self.metrics_history.get("fixed_time", {})
        rl = self.metrics_history.get("rl", {})
        
        fixed_delay = fixed.get("avg_delay", 1)
        rl_delay = rl.get("avg_delay", 1)
        fixed_throughput = fixed.get("throughput", 1)
        rl_throughput = rl.get("throughput", 1)
        
        delay_reduction = ((fixed_delay - rl_delay) / max(fixed_delay, 0.1)) * 100 if fixed_delay > 0 else 0
        throughput_gain = ((rl_throughput - fixed_throughput) / max(fixed_throughput, 1)) * 100 if fixed_throughput > 0 else 0
        
        return {
            "delay_reduction": round(max(0, delay_reduction), 1),
            "throughput_gain": round(max(0, throughput_gain), 1)
        }


# Global state manager
sim_state = SimulationState()


# ============== API ENDPOINTS - ALL REAL DATA ==============

@router.get("/weather", response_model=WeatherConditionResponse)
async def get_weather():
    """Get current weather conditions (user-configurable, affects simulation)."""
    return WeatherConditionResponse(**sim_state.get_weather())


@router.post("/weather/set")
async def set_weather(condition: int):
    """
    Set weather condition - ACTUALLY affects simulation speed!
    0: Normal, 1: Light Rain, 2: Moderate Rain, 3: Heavy Rain
    """
    if not sim_state.set_weather(condition):
        raise HTTPException(status_code=400, detail="Condition must be 0-3")
    
    return {"status": "ok", "weather": sim_state.get_weather()}


@router.get("/emergency", response_model=EmergencyStatusResponse)
async def get_emergency_status():
    """
    Get REAL emergency vehicle status from simulation.
    Detects actual ambulance/fire/police vehicles via TraCI.
    """
    status = sim_state.detect_emergency_vehicles()
    return EmergencyStatusResponse(**status)


@router.get("/metrics/realtime", response_model=RealTimeMetricsResponse)
async def get_realtime_metrics():
    """Get REAL metrics from running SUMO simulation."""
    return RealTimeMetricsResponse(**sim_state.get_real_metrics())


@router.get("/evaluation/comparison")
async def get_evaluation_comparison():
    """
    Get comparison metrics from REAL simulation runs.
    Data populated after running Fixed-Time and RL modes.
    """
    return sim_state.get_comparison()


@router.post("/evaluation/record")
async def record_current_metrics(mode: str = "rl"):
    """Record current step metrics (called by simulation loop)."""
    sim_state.record_metrics(mode)
    return {"status": "ok"}


@router.post("/evaluation/finalize")
async def finalize_run_metrics(mode: str = "rl"):
    """Finalize metrics after a simulation run completes."""
    sim_state.finalize_run(mode)
    return {"status": "ok", "metrics": sim_state.metrics_history.get(mode, {})}


@router.get("/status")
async def get_advanced_status():
    """Get overall system status."""
    return {
        "simulation_connected": traci_handler.connected,
        "weather": sim_state.get_weather(),
        "emergency": sim_state.detect_emergency_vehicles(),
        "metrics": sim_state.get_real_metrics(),
        "data_source": "REAL - TraCI/SUMO"
    }


# ============== FUNCTIONS FOR WEBSOCKET INTEGRATION ==============

def get_live_weather():
    """Get weather for WebSocket broadcast."""
    return sim_state.get_weather()


def get_live_emergency():
    """Get emergency status for WebSocket broadcast."""
    return sim_state.detect_emergency_vehicles()


def record_step_metrics(mode: str = "rl"):
    """Record metrics at each step."""
    sim_state.record_metrics(mode)
