"""
Dual WebSocket Manager
======================
Streams metrics from BOTH simulations (Fixed + RL) simultaneously.
Frontend can switch which one to display or show both side-by-side.
"""
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import List, Dict
import asyncio
from app.sumo.dual_orchestrator import dual_orchestrator
from app.rl.inference import rl_agent
from app.config import settings


class DualConnectionManager:
    """
    Manages WebSocket connections and broadcasts metrics from dual simulations.
    
    Message format sent to clients:
    {
        "fixed": { ...metrics... },
        "rl": { ...metrics... },
        "step": 123,
        "comparison": {
            "wait_time_diff": -15.2,  # RL is 15.2s faster
            "queue_diff": -8,          # RL has 8 fewer queued
            "throughput_diff": 12      # RL processed 12 more vehicles
        }
    }
    """
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.broadcasting = False
        self.current_mode = "comparison"  # 'fixed', 'rl', or 'comparison'
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 Client connected. Total: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"🔌 Client disconnected. Total: {len(self.active_connections)}")
        
    async def broadcast(self, message: Dict):
        """Broadcast to all connected clients"""
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception as e:
                print(f"⚠️ Broadcast error: {e}")
                disconnected.append(conn)
                
        for conn in disconnected:
            self.disconnect(conn)
    
    async def start_dual_broadcasting(self, intensity: str = "peak"):
        """
        Main broadcast loop for dual simulation.
        
        Runs both simulations in lockstep:
        1. Step FIXED simulation (fixed-time control)
        2. Step RL simulation (with RL agent decisions)
        3. Collect metrics from both
        4. Calculate comparison metrics
        5. Broadcast to all clients
        """
        self.broadcasting = True
        print(f"🚀 Starting DUAL broadcast loop (intensity: {intensity})")
        
        # Load RL model
        print("🤖 Loading RL agent...")
        policy_type = rl_agent.get_policy_for_intensity(intensity)
        rl_agent.load_model(policy_type)
        
        if rl_agent.loaded:
            print(f"   ✓ RL Policy loaded: {rl_agent.current_policy}")
        else:
            print("   ⚠️ RL agent not loaded, RL sim will use default control")
        
        step_count = 0
        
        while self.broadcasting and dual_orchestrator.is_running:
            try:
                # ===== STEP BOTH SIMULATIONS =====
                
                # For RL simulation: apply RL agent decisions BEFORE stepping
                if rl_agent.loaded and dual_orchestrator.rl_sim.connected:
                    import traci
                    traci.switch(dual_orchestrator.rl_sim.label)
                    
                    for junction_id in dual_orchestrator.rl_sim.junction_ids:
                        # Get observation and predict action
                        obs = self._get_rl_observation()
                        if obs is not None:
                            action = rl_agent.predict_action(obs)
                            if action is not None:
                                try:
                                    traci.trafficlight.setPhase(junction_id, int(action))
                                except:
                                    pass
                
                # Step both simulations
                fixed_metrics, rl_metrics = dual_orchestrator.step_both()
                step_count += 1
                
                if not fixed_metrics and not rl_metrics:
                    # Both failed, simulation ended
                    print("📊 Simulation ended (no metrics)")
                    break
                
                # ===== CALCULATE COMPARISON =====
                comparison = self._calculate_comparison(fixed_metrics, rl_metrics)
                
                # ===== BUILD BROADCAST MESSAGE =====
                message = {
                    "step": step_count,
                    "time": fixed_metrics.get('time', 0),
                    "fixed": fixed_metrics,
                    "rl": rl_metrics,
                    "comparison": comparison,
                    "rl_agent_status": {
                        "loaded": rl_agent.loaded,
                        "policy": rl_agent.current_policy
                    }
                }
                
                # Broadcast to all clients
                if self.active_connections:
                    await self.broadcast(message)
                
                # Debug logging every 5 steps
                if step_count % 5 == 0:
                    fixed_q = fixed_metrics.get('queue_length', 0)
                    rl_q = rl_metrics.get('queue_length', 0)
                    diff = comparison.get('queue_diff', 0)
                    print(f"📊 Step {step_count}: "
                          f"FIXED Queue={fixed_q}, RL Queue={rl_q}, "
                          f"Diff={diff:+d} {'✅RL better' if diff < 0 else '⚠️FIXED better'}")
                
                # Wait for next step
                await asyncio.sleep(settings.WS_UPDATE_INTERVAL)
                
            except Exception as e:
                error_msg = str(e).lower()
                if "connection" in error_msg:
                    print(f"❌ Connection error: {e}")
                    self.broadcasting = False
                    dual_orchestrator.stop_all()
                    break
                else:
                    print(f"⚠️ Step error: {e}")
                    await asyncio.sleep(1)
        
        print("📊 Dual broadcast loop ended")
    
    def _get_rl_observation(self):
        """Get observation for RL agent from current SUMO state"""
        try:
            import traci
            import numpy as np
            
            lanes = [l for l in traci.lane.getIDList() if not l.startswith(':')][:8]
            
            while len(lanes) < 8:
                lanes.append(lanes[-1] if lanes else "dummy")
            
            densities = []
            queues = []
            
            for lane in lanes:
                try:
                    occ = traci.lane.getLastStepOccupancy(lane) / 100.0
                    densities.append(min(1.0, max(0.0, occ)))
                    
                    halt = traci.lane.getLastStepHaltingNumber(lane)
                    length = traci.lane.getLength(lane)
                    max_veh = max(1, length / 5.0)
                    queues.append(min(1.0, halt / max_veh))
                except:
                    densities.append(0.0)
                    queues.append(0.0)
            
            # Get current phase
            phase = 0
            try:
                junctions = traci.trafficlight.getIDList()
                if junctions:
                    phase = traci.trafficlight.getPhase(junctions[0]) / 4.0
            except:
                pass
            
            # Time and weather (placeholders)
            from datetime import datetime
            time_norm = datetime.now().hour / 24.0
            weather = 1.0
            
            obs = densities + queues + [phase, time_norm, weather]
            return np.array(obs, dtype=np.float32)
            
        except Exception as e:
            print(f"⚠️ Obs error: {e}")
            return None
    
    def _calculate_comparison(self, fixed: Dict, rl: Dict) -> Dict:
        """Calculate comparison metrics between Fixed and RL"""
        if not fixed or not rl:
            return {}
            
        return {
            "queue_diff": rl.get('queue_length', 0) - fixed.get('queue_length', 0),
            "wait_time_diff": rl.get('waiting_time', 0) - fixed.get('waiting_time', 0),
            "throughput_diff": rl.get('throughput', 0) - fixed.get('throughput', 0),
            "vehicle_diff": rl.get('vehicle_count', 0) - fixed.get('vehicle_count', 0),
            # Positive diff = RL is worse, Negative diff = RL is better
            "rl_advantage": {
                "queue": fixed.get('queue_length', 0) - rl.get('queue_length', 0),
                "wait": fixed.get('waiting_time', 0) - rl.get('waiting_time', 0),
                "throughput": rl.get('throughput', 0) - fixed.get('throughput', 0)
            }
        }
    
    def stop_broadcasting(self):
        self.broadcasting = False
        print("🛑 Stopped dual broadcasting")


# Global manager
dual_manager = DualConnectionManager()

# Router
dual_ws_router = APIRouter()


@dual_ws_router.websocket("/ws/dual")
async def dual_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for dual simulation metrics.
    
    Clients connect here to receive real-time comparison data.
    """
    await dual_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("mode:"):
                # Client requests specific mode: 'fixed', 'rl', or 'comparison'
                dual_manager.current_mode = data.split(":")[1]
                await websocket.send_json({"mode_changed": dual_manager.current_mode})
                
    except WebSocketDisconnect:
        dual_manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️ WS error: {e}")
        dual_manager.disconnect(websocket)
