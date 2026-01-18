"""
WebSocket Manager for real-time data streaming
Broadcasts REAL simulation metrics to connected clients
"""
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import List, Dict
import asyncio
import json
from app.sumo.traci_handler import traci_handler
from app.config import settings
from app.rl.inference import rl_agent
from app.routes.advanced import sim_state, get_live_weather, get_live_emergency, record_step_metrics


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.broadcasting = False
    
    async def connect(self, websocket: WebSocket):
        """Accept and store new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def start_broadcasting(self, mode: str = "fixed", intensity: str = None):
        """Start broadcasting simulation metrics"""
        self.broadcasting = True
        print(f"Started broadcasting simulation metrics in {mode} mode (intensity: {intensity})")
        
        # Load RL model if in RL mode
        if mode == "rl":
            print("🤖 RL Mode: Loading agent with time-based policy selection...")
            policy_type = rl_agent.get_policy_for_intensity(intensity)
            print(f"   Detected policy type: {policy_type}")
            rl_agent.load_model(policy_type)
            if rl_agent.loaded:
                print(f"   ✓ Policy loaded successfully: {rl_agent.current_policy}")
                print(f"   ✓ Agent status: {rl_agent.get_status()}")
        
        step_count = 0
        while self.broadcasting:
            try:
                # ⚡ RL CONTROL LOGIC
                if mode == "rl" and rl_agent.loaded:
                    # Check if policy needs switching (time-based)
                    rl_agent.switch_policy_if_needed(intensity)
                    
                    # Control all traffic lights
                    for junction_id in traci_handler.junction_ids:
                        rl_agent.control_traffic_light(junction_id, intensity)

                # ⚡ STEP THE SIMULATION (this makes vehicles move!)
                step_success = traci_handler.simulation_step()
                step_count += 1
                
                # Get current metrics from SUMO (REAL DATA)
                metrics = traci_handler.get_metrics()
                
                # Add weather and emergency data (REAL from simulation)
                metrics["weather"] = get_live_weather()
                metrics["emergency"] = get_live_emergency()
                metrics["controller_mode"] = mode
                
                # Record metrics for comparison
                record_step_metrics(mode)
                
                # 🔍 DEBUG LOGGING - Print every 5 seconds
                if step_count % 5 == 0:
                    emergency_status = "🚨 ACTIVE" if metrics["emergency"]["active"] else "✓ Clear"
                    weather_name = metrics["weather"]["condition_name"]
                    print(f"📊 Step {step_count}: Time={metrics.get('time', 0):.0f}s, "
                          f"Vehicles={metrics.get('vehicle_count', 0)}, "
                          f"Queue={metrics.get('queue_length', 0)}, "
                          f"Mode={mode.upper()}, Weather={weather_name}, Emergency={emergency_status}")
                
                # Broadcast to all connected clients
                if self.active_connections:
                    await self.broadcast(metrics)
                
                # Wait for configured interval
                await asyncio.sleep(settings.WS_UPDATE_INTERVAL)
                
            except Exception as e:
                error_msg = str(e).lower()
                if "connection closed" in error_msg or "connection already closed" in error_msg or "fataltracierror" in error_msg:
                    print(f"❌ SUMO Connection lost: {e}")
                    print("🛑 Stopping simulation automatically...")
                    self.broadcasting = False
                    from app.sumo.runner import sumo_runner
                    sumo_runner.stop()
                    break
                
                print(f"❌ Error in broadcast loop: {e}")
                import traceback
                traceback.print_exc()
                await asyncio.sleep(1)
    
    def stop_broadcasting(self):
        """Stop broadcasting simulation metrics"""
        self.broadcasting = False
        print("Stopped broadcasting simulation metrics")


# Global connection manager
manager = ConnectionManager()

# WebSocket router
ws_router = APIRouter()


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time simulation data
    Clients connect here to receive live metrics
    """
    await manager.connect(websocket)
    
    try:
        # Keep connection alive and listen for client messages
        while True:
            # Receive any client messages (ping/pong, etc.)
            data = await websocket.receive_text()
            
            # Echo back for connection health check
            if data == "ping":
                await websocket.send_text("pong")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)
