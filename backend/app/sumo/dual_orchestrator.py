"""
Dual SUMO Simulation Orchestrator
==================================
Runs TWO parallel SUMO instances for fair comparison:
- Instance A: Fixed-Time Controller (baseline)
- Instance B: RL Controller (experimental)

Uses subprocess.Popen + traci.init() approach which is more reliable
for running multiple SUMO instances.
"""
import os
import time
import subprocess
import socket
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from app.config import settings


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def wait_for_port(port: int, timeout: int = 30) -> bool:
    """Wait for a port to become available (SUMO listening)"""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_in_use(port):
            return True
        time.sleep(0.5)
    return False


@dataclass
class SimulationInstance:
    """Represents a single SUMO simulation instance"""
    name: str
    port: int
    mode: str  # 'fixed' or 'rl'
    connected: bool = False
    junction_ids: list = field(default_factory=list)
    lane_ids: list = field(default_factory=list)
    label: str = ""
    process: subprocess.Popen = None
    

class DualSimulationOrchestrator:
    """
    Orchestrates two parallel SUMO simulations for comparison.
    """
    
    PORT_FIXED = 8813
    PORT_RL = 8814
    
    def __init__(self):
        self.fixed_sim = SimulationInstance(
            name="FIXED",
            port=self.PORT_FIXED,
            mode="fixed",
            label="fixed_conn"
        )
        self.rl_sim = SimulationInstance(
            name="RL",
            port=self.PORT_RL,
            mode="rl",
            label="rl_conn"
        )
        self.is_running = False
        self.current_step = 0
        self.config_file = ""
        self.location = ""
        
    def start_dual_simulation(self, location: str, use_gui: bool = True) -> bool:
        """Start both SUMO instances in parallel."""
        if self.is_running:
            print("⚠️ Dual simulation already running")
            return False
            
        self.location = location
            
        try:
            import traci
            
            # Set environment
            os.environ['SUMO_HOME'] = settings.SUMO_HOME
            
            # Build config path
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_file = os.path.join(current_dir, "sumo", "network", "simulation.sumocfg")
            
            binary = settings.SUMO_GUI_BINARY if use_gui else settings.SUMO_BINARY
            sumo_binary = os.path.join(settings.SUMO_HOME, 'bin', binary)
            
            # Close any existing connections
            self._cleanup_connections()
            
            # ===== START FIXED-TIME INSTANCE =====
            print(f"🚦 Starting FIXED-TIME simulation on port {self.PORT_FIXED}...")
            
            fixed_cmd = [
                sumo_binary,
                "-c", self.config_file,
                "--remote-port", str(self.PORT_FIXED),
                "--num-clients", "1",
                "--step-length", str(settings.STEP_LENGTH),
                "--no-warnings",
                "--window-pos", "0,50",
                "--window-size", "800,600"
            ]
            
            print(f"   Command: {' '.join(fixed_cmd)}")
            self.fixed_sim.process = subprocess.Popen(fixed_cmd)
            
            # Wait for SUMO to open its port
            if not wait_for_port(self.PORT_FIXED, timeout=25):
                raise Exception(f"SUMO did not open port {self.PORT_FIXED} in time")
            
            # Connect TraCI with retries
            print(f"   Connecting TraCI to {self.PORT_FIXED}...")
            connected = False
            for i in range(5):
                try:
                    traci.init(port=self.PORT_FIXED, label=self.fixed_sim.label)
                    connected = True
                    break
                except:
                    print(f"   Retrying TraCI FIXED ({i+1}/5)...")
                    time.sleep(1.5)
            
            if not connected:
                raise Exception(f"Failed to connect TraCI to port {self.PORT_FIXED}")
            
            # Small delay to ensure SUMO is ready
            time.sleep(1)
            
            traci.switch(self.fixed_sim.label)
            self.fixed_sim.connected = True
            self.fixed_sim.junction_ids = list(traci.trafficlight.getIDList())
            self.fixed_sim.lane_ids = list(traci.lane.getIDList())
            print(f"   ✅ FIXED connected: {len(self.fixed_sim.junction_ids)} junctions")
            
            # ===== START RL INSTANCE =====
            print(f"🤖 Starting RL simulation on port {self.PORT_RL}...")
            
            rl_cmd = [
                sumo_binary,
                "-c", self.config_file,
                "--remote-port", str(self.PORT_RL),
                "--num-clients", "1",
                "--step-length", str(settings.STEP_LENGTH),
                "--no-warnings",
                "--window-pos", "820,50",
                "--window-size", "800,600"
            ]
            
            print(f"   Command: {' '.join(rl_cmd)}")
            self.rl_sim.process = subprocess.Popen(rl_cmd)
            
            # Wait for SUMO to open its port
            if not wait_for_port(self.PORT_RL, timeout=25):
                raise Exception(f"SUMO did not open port {self.PORT_RL} in time")
            
            # Connect TraCI with retries
            print(f"   Connecting TraCI to {self.PORT_RL}...")
            connected = False
            for i in range(5):
                try:
                    traci.init(port=self.PORT_RL, label=self.rl_sim.label)
                    connected = True
                    break
                except:
                    print(f"   Retrying TraCI RL ({i+1}/5)...")
                    time.sleep(1.5)
            
            if not connected:
                raise Exception(f"Failed to connect TraCI to port {self.PORT_RL}")
            
            time.sleep(1)
            traci.switch(self.rl_sim.label)
            self.rl_sim.connected = True
            self.rl_sim.junction_ids = list(traci.trafficlight.getIDList())
            self.rl_sim.lane_ids = list(traci.lane.getIDList())
            print(f"   ✅ RL connected: {len(self.rl_sim.junction_ids)} junctions")
            
            self.is_running = True
            self.current_step = 0
            print("🚀 DUAL SIMULATION STARTED!")
            print("   Left window: FIXED-TIME")
            print("   Right window: RL-CONTROLLED")
            return True
            
        except Exception as e:
            print(f"❌ Error starting dual simulation: {e}")
            import traceback
            traceback.print_exc()
            self.stop_all()
            return False
    
    def _cleanup_connections(self):
        """Clean up any existing TraCI connections"""
        import traci
        
        for label in [self.fixed_sim.label, self.rl_sim.label]:
            try:
                traci.switch(label)
                traci.close()
            except:
                pass
        
        # Kill any existing processes
        for sim in [self.fixed_sim, self.rl_sim]:
            if sim.process:
                try:
                    sim.process.terminate()
                    sim.process.wait(timeout=5)
                except:
                    pass
                sim.process = None
    
    def step_both(self) -> Tuple[Dict, Dict]:
        """Advance both simulations by one step."""
        import traci
        
        if not self.is_running:
            return {}, {}
            
        fixed_metrics = {}
        rl_metrics = {}
        
        try:
            # Step FIXED simulation
            if self.fixed_sim.connected:
                traci.switch(self.fixed_sim.label)
                traci.simulationStep()
                fixed_metrics = self._get_metrics(self.fixed_sim)
                fixed_metrics['controller'] = 'FIXED'
                
            # Step RL simulation
            if self.rl_sim.connected:
                traci.switch(self.rl_sim.label)
                traci.simulationStep()
                rl_metrics = self._get_metrics(self.rl_sim)
                rl_metrics['controller'] = 'RL'
                
            self.current_step += 1
            
        except Exception as e:
            error_msg = str(e).lower()
            if "connection" in error_msg or "closed" in error_msg:
                print(f"❌ Connection lost: {e}")
                self.stop_all()
            else:
                print(f"⚠️ Step error: {e}")
                
        return fixed_metrics, rl_metrics
    
    def _get_metrics(self, sim: SimulationInstance) -> Dict:
        """Get metrics from a specific simulation instance"""
        import traci
        try:
            return {
                'time': traci.simulation.getTime(),
                'vehicle_count': traci.vehicle.getIDCount(),
                'arrived_vehicles': traci.simulation.getArrivedNumber(),
                'departed_vehicles': traci.simulation.getDepartedNumber(),
                'waiting_time': self._get_avg_waiting_time(),
                'queue_length': self._get_total_queue(),
                'throughput': traci.simulation.getArrivedNumber(),
            }
        except:
            return {}
    
    def _get_avg_waiting_time(self) -> float:
        """Calculate average waiting time across all vehicles"""
        import traci
        try:
            vehicles = traci.vehicle.getIDList()
            if not vehicles:
                return 0.0
            total_wait = sum(traci.vehicle.getWaitingTime(v) for v in vehicles)
            return total_wait / len(vehicles)
        except:
            return 0.0
    
    def _get_total_queue(self) -> int:
        """Get total halting vehicles (queue length)"""
        import traci
        try:
            return sum(
                traci.lane.getLastStepHaltingNumber(lane)
                for lane in traci.lane.getIDList()
                if not lane.startswith(':')
            )
        except:
            return 0
    
    def inject_emergency_vehicle(self, route_id: str = "emergency_route", 
                                  vehicle_type: str = "ambulance") -> bool:
        """Inject the SAME emergency vehicle into BOTH simulations."""
        import traci
        from app.demand.demand_generator import demand_generator
        
        vehicle_id = f"emergency_{int(time.time())}"
        success = True
        
        # Get edges for current location
        edges_map = demand_generator.LOCATION_EDGES.get(self.location, demand_generator.LOCATION_EDGES['silk_board'])
        entry, exit_edge = edges_map.get('north', edges_map['north']) # Default to north entry
        
        try:
            for label in [self.fixed_sim.label, self.rl_sim.label]:
                traci.switch(label)
                # Create route on the fly if it doesn't exist
                if route_id not in traci.route.getIDList():
                    traci.route.add(route_id, [entry, exit_edge])
                
                traci.vehicle.add(vehicle_id, routeID=route_id, typeID=vehicle_type)
                print(f"🚑 Emergency added to {label}: {vehicle_id} ({entry} -> {exit_edge})")
                
        except Exception as e:
            print(f"⚠️ Error injecting emergency: {e}")
            success = False
            
        return success
    
    def apply_weather_condition(self, condition: str) -> bool:
        """Apply weather effects to BOTH simulations."""
        import traci
        
        speed_factor = {
            "rain": 0.7,
            "fog": 0.5,
            "storm": 0.4
        }.get(condition, 1.0)
            
        try:
            for sim in [self.fixed_sim, self.rl_sim]:
                if sim.connected:
                    traci.switch(sim.label)
                    for veh_id in traci.vehicle.getIDList():
                        max_speed = traci.vehicle.getMaxSpeed(veh_id)
                        traci.vehicle.setMaxSpeed(veh_id, max_speed * speed_factor)
                    print(f"🌧️ Weather '{condition}' applied to {sim.name}")
                    
            return True
        except Exception as e:
            print(f"⚠️ Error applying weather: {e}")
            return False
    
    def set_traffic_light_phase(self, junction_id: str, phase: int, 
                                  target: str = "both") -> bool:
        """Set traffic light phase."""
        import traci
        try:
            if target in ['fixed', 'both'] and self.fixed_sim.connected:
                traci.switch(self.fixed_sim.label)
                traci.trafficlight.setPhase(junction_id, phase)
                
            if target in ['rl', 'both'] and self.rl_sim.connected:
                traci.switch(self.rl_sim.label)
                traci.trafficlight.setPhase(junction_id, phase)
                
            return True
        except Exception as e:
            print(f"⚠️ Error setting phase: {e}")
            return False
    
    def stop_all(self) -> bool:
        """Stop both simulations and cleanup"""
        import traci
        print("🛑 Stopping dual simulation...")
        
        for sim in [self.fixed_sim, self.rl_sim]:
            try:
                if sim.connected:
                    traci.switch(sim.label)
                    traci.close()
                    sim.connected = False
                    print(f"   ✓ {sim.name} TraCI closed")
            except Exception as e:
                print(f"   ⚠️ Error closing {sim.name} TraCI: {e}")
                # Force disconnect
                sim.connected = False
                
            try:
                if sim.process:
                    sim.process.terminate()
                    sim.process.wait(timeout=5)
                    sim.process = None
                    print(f"   ✓ {sim.name} process terminated")
            except Exception as e:
                print(f"   ⚠️ Error terminating {sim.name} process: {e}")
                sim.process = None
            
            # Reset simulation state
            sim.junction_ids = []
            sim.lane_ids = []
            sim.total_departed = 0
            sim.total_arrived = 0
            
        self.is_running = False
        self.current_step = 0
        print("✅ Dual simulation stopped and state reset")
        return True
    
    def get_status(self) -> Dict:
        """Get status of both simulations"""
        return {
            'running': self.is_running,
            'current_step': self.current_step,
            'fixed': {
                'connected': self.fixed_sim.connected,
                'port': self.fixed_sim.port,
                'junctions': len(self.fixed_sim.junction_ids)
            },
            'rl': {
                'connected': self.rl_sim.connected,
                'port': self.rl_sim.port,
                'junctions': len(self.rl_sim.junction_ids)
            }
        }


# Global orchestrator instance
dual_orchestrator = DualSimulationOrchestrator()
