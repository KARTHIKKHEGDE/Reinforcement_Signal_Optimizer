import traci
import time
import os
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
from collections import defaultdict, deque
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VehicleType(Enum):
    REGULAR = "regular"
    EMERGENCY = "emergency"
    PUBLIC_TRANSPORT = "bus"
    FREIGHT = "truck"

class TrafficPhase(Enum):
    GREEN = 0
    YELLOW = 1
    RED = 2

@dataclass
class VehicleInfo:
    id: str
    type: VehicleType
    speed: float
    position: float
    lane: str
    waiting_time: float
    co2_emission: float
    
@dataclass
class TrafficLightState:
    id: str
    current_phase: int
    phase_duration: int
    last_phase_change: int
    emergency_mode: bool = False
    priority_queue: List[str] = field(default_factory=list)
    vehicle_count: Dict[str, int] = field(default_factory=dict)
    average_waiting_time: float = 0.0
    throughput: int = 0

class TrafficController(ABC):
    @abstractmethod
    def decide_phase(self, tls_state: TrafficLightState, vehicles: List[VehicleInfo], step: int) -> int:
        pass

class AdaptiveTrafficController(TrafficController):
    """Advanced adaptive traffic controller using vehicle density and waiting times"""
    
    def __init__(self, min_phase_duration=10, max_phase_duration=60):
        self.min_phase_duration = min_phase_duration
        self.max_phase_duration = max_phase_duration
        self.phase_weights = defaultdict(float)
        
    def decide_phase(self, tls_state: TrafficLightState, vehicles: List[VehicleInfo], step: int) -> int:
        # Emergency vehicle priority
        emergency_vehicles = [v for v in vehicles if v.type == VehicleType.EMERGENCY]
        if emergency_vehicles:
            return self._get_emergency_phase(tls_state.id, emergency_vehicles)
        
        # Calculate phase scores based on multiple factors
        phase_scores = self._calculate_phase_scores(tls_state, vehicles)
        
        # Check if current phase should be extended or changed
        current_duration = step - tls_state.last_phase_change
        
        if current_duration < self.min_phase_duration:
            return tls_state.current_phase
            
        if current_duration >= self.max_phase_duration:
            return self._get_best_phase(phase_scores, tls_state.current_phase)
            
        # Adaptive decision based on traffic conditions
        current_score = phase_scores.get(tls_state.current_phase, 0)
        best_phase = max(phase_scores.keys(), key=lambda x: phase_scores[x])
        best_score = phase_scores[best_phase]
        
        # Change phase if significant improvement is possible
        if best_score > current_score * 1.3:  # 30% improvement threshold
            return best_phase
            
        return tls_state.current_phase
    
    def _calculate_phase_scores(self, tls_state: TrafficLightState, vehicles: List[VehicleInfo]) -> Dict[int, float]:
        scores = defaultdict(float)
        
        # Group vehicles by lane
        lane_vehicles = defaultdict(list)
        for vehicle in vehicles:
            lane_vehicles[vehicle.lane].append(vehicle)
        
        # Calculate scores for each phase (simplified - would need actual phase-lane mapping)
        for phase in range(len(traci.trafficlight.getAllProgramLogics(tls_state.id)[0].phases)):
            # Factors: vehicle count, waiting time, priority vehicles
            vehicle_count_score = sum(len(vehs) for vehs in lane_vehicles.values())
            waiting_time_score = sum(v.waiting_time for v in vehicles)
            priority_score = sum(2.0 for v in vehicles if v.type == VehicleType.PUBLIC_TRANSPORT)
            
            scores[phase] = vehicle_count_score + waiting_time_score * 0.1 + priority_score
            
        return scores
    
    def _get_emergency_phase(self, tls_id: str, emergency_vehicles: List[VehicleInfo]) -> int:
        # Return phase that gives green light to emergency vehicle lane
        # This would need actual implementation based on your network topology
        return 0  # Simplified
    
    def _get_best_phase(self, phase_scores: Dict[int, float], current_phase: int) -> int:
        if not phase_scores:
            return current_phase
        return max(phase_scores.keys(), key=lambda x: phase_scores[x])

class TrafficAnalyzer:
    """Analyzes traffic patterns and provides insights"""
    
    def __init__(self):
        self.historical_data = defaultdict(list)
        self.congestion_threshold = 0.8
        
    def analyze_traffic_flow(self, step: int, tls_states: Dict[str, TrafficLightState]) -> Dict[str, any]:
        analysis = {
            'timestamp': step,
            'total_vehicles': 0,
            'average_speed': 0.0,
            'congested_intersections': [],
            'emergency_events': 0,
            'throughput': 0,
            'co2_emissions': 0.0
        }
        
        all_vehicles = traci.vehicle.getIDList()
        if not all_vehicles:
            return analysis
            
        speeds = [traci.vehicle.getSpeed(veh) for veh in all_vehicles]
        analysis['total_vehicles'] = len(all_vehicles)
        analysis['average_speed'] = np.mean(speeds) if speeds else 0
        
        # Detect congestion
        for tls_id, state in tls_states.items():
            if state.average_waiting_time > 30:  # seconds
                analysis['congested_intersections'].append(tls_id)
        
        # Count emergency events
        analysis['emergency_events'] = sum(1 for state in tls_states.values() if state.emergency_mode)
        
        # Calculate total throughput
        analysis['throughput'] = sum(state.throughput for state in tls_states.values())
        
        # Estimate CO2 emissions
        analysis['co2_emissions'] = sum(traci.vehicle.getCO2Emission(veh) for veh in all_vehicles)
        
        self.historical_data[step] = analysis
        return analysis

class SUMOSimulationManager:
    """Enhanced SUMO simulation manager with advanced features"""
    
    def __init__(self, config_file: str, gui: bool = True):
        self.connected = False
        self.config_file = config_file
        self.gui = gui
        self.controllers: Dict[str, TrafficController] = {}
        self.tls_states: Dict[str, TrafficLightState] = {}
        self.analyzer = TrafficAnalyzer()
        self.metrics_history: List[Dict] = []
        self.performance_log = deque(maxlen=1000)
        
    def setup_sumo(self):
        """Initialize SUMO connection"""
        sumo_binary = "sumo-gui" if self.gui else "sumo"
        sumo_cmd = [sumo_binary, "-c", self.config_file, "--waiting-time-memory", "1000"]
        
        try:
            traci.start(sumo_cmd)
            logger.info("SUMO simulation started successfully")
            self._initialize_traffic_lights()
        except Exception as e:
            logger.error(f"Failed to start SUMO: {e}")
            self.connected = False
            raise
    
    def _initialize_traffic_lights(self):
        """Initialize traffic light controllers and states"""
        tls_ids = traci.trafficlight.getIDList()
        
        for tls_id in tls_ids:
            # Create adaptive controller for each traffic light
            self.controllers[tls_id] = AdaptiveTrafficController()
            
            # Initialize state
            self.tls_states[tls_id] = TrafficLightState(
                id=tls_id,
                current_phase=traci.trafficlight.getPhase(tls_id),
                phase_duration=0,
                last_phase_change=0
            )
            
        logger.info(f"Initialized {len(tls_ids)} traffic lights with adaptive controllers")
    
    def get_vehicle_info(self, lane: str) -> List[VehicleInfo]:
        """Extract detailed vehicle information from a lane"""
        vehicle_ids = traci.lane.getLastStepVehicleIDs(lane)
        vehicles = []
        
        for veh_id in vehicle_ids:
            try:
                veh_type_str = traci.vehicle.getTypeID(veh_id)
                veh_type = VehicleType.EMERGENCY if veh_type_str == "emergency" else \
                          VehicleType.PUBLIC_TRANSPORT if veh_type_str == "bus" else \
                          VehicleType.FREIGHT if veh_type_str == "truck" else \
                          VehicleType.REGULAR
                
                vehicles.append(VehicleInfo(
                    id=veh_id,
                    type=veh_type,
                    speed=traci.vehicle.getSpeed(veh_id),
                    position=traci.vehicle.getLanePosition(veh_id),
                    lane=lane,
                    waiting_time=traci.vehicle.getWaitingTime(veh_id),
                    co2_emission=traci.vehicle.getCO2Emission(veh_id)
                ))
            except traci.TraCIException:
                continue  # Vehicle might have left during data collection
                
        return vehicles
    
    def update_traffic_light(self, tls_id: str, step: int):
        """Update a single traffic light using its controller"""
        state = self.tls_states[tls_id]
        controller = self.controllers[tls_id]
        
        # Get all vehicles in controlled lanes
        controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
        all_vehicles = []
        
        for lane in controlled_lanes:
            all_vehicles.extend(self.get_vehicle_info(lane))
        
        # Update state information
        state.vehicle_count = {lane: len(self.get_vehicle_info(lane)) for lane in controlled_lanes}
        state.average_waiting_time = np.mean([v.waiting_time for v in all_vehicles]) if all_vehicles else 0
        state.emergency_mode = any(v.type == VehicleType.EMERGENCY for v in all_vehicles)
        
        # Get controller decision
        new_phase = controller.decide_phase(state, all_vehicles, step)
        
        # Apply phase change if needed
        if new_phase != state.current_phase:
            traci.trafficlight.setPhase(tls_id, new_phase)
            logger.info(f"Step {step}: Changed {tls_id} from phase {state.current_phase} to {new_phase}")
            state.last_phase_change = step
            state.current_phase = new_phase
            state.phase_duration = 0
        else:
            state.phase_duration += 1
        
        # Update throughput (vehicles that passed)
        state.throughput = len([v for v in all_vehicles if v.speed > 1.0])
    
    def run_simulation(self, max_steps: int = 3600, analysis_interval: int = 100):
        """Run the enhanced simulation with real-time analysis"""
        logger.info(f"Starting simulation for {max_steps} steps")
        
        try:
            for step in range(max_steps):
                traci.simulationStep()
                
                # Update all traffic lights
                for tls_id in self.tls_states.keys():
                    self.update_traffic_light(tls_id, step)
                
                # Periodic analysis
                if step % analysis_interval == 0:
                    analysis = self.analyzer.analyze_traffic_flow(step, self.tls_states)
                    self.metrics_history.append(analysis)
                    
                    logger.info(f"Step {step}: Vehicles: {analysis['total_vehicles']}, "
                              f"Avg Speed: {analysis['average_speed']:.2f}, "
                              f"Congested: {len(analysis['congested_intersections'])}")
                
                # Performance monitoring
                if step % 50 == 0:
                    self.performance_log.append({
                        'step': step,
                        'simulation_time': time.time(),
                        'total_vehicles': len(traci.vehicle.getIDList()),
                        'active_tls': len(self.tls_states)
                    })
                
                time.sleep(0.02)  # Reduced sleep for better performance
                
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        except Exception as e:
            logger.error(f"Simulation error: {e}")
        finally:
            self.cleanup()
    
    def save_results(self, filename: str = "simulation_results.json"):
        """Save simulation results and analysis"""
        results = {
            'metrics_history': self.metrics_history,
            'performance_log': list(self.performance_log),
            'final_states': {tls_id: {
                'current_phase': state.current_phase,
                'average_waiting_time': state.average_waiting_time,
                'throughput': state.throughput,
                'emergency_events': state.emergency_mode
            } for tls_id, state in self.tls_states.items()}
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {filename}")
    
    def cleanup(self):
        """Clean up SUMO connection and save results"""
        if self.connected:
            try:
                traci.close()
                self.save_results()
                logger.info("Simulation cleanup completed")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

def main():
    """Main function with enhanced configuration"""
    # Configuration
    SUMO_CFG = "map.sumocfg"
    MAX_STEPS = 3600  # 1 hour simulation
    ANALYSIS_INTERVAL = 60  # Analyze every minute
    USE_GUI = True
    
    # Setup SUMO environment
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        import sys
        if tools not in sys.path:
            sys.path.append(tools)
    
    # Create and run simulation
    sim_manager = SUMOSimulationManager(SUMO_CFG, gui=USE_GUI)
    
    try:
        sim_manager.setup_sumo()
        sim_manager.run_simulation(max_steps=MAX_STEPS, analysis_interval=ANALYSIS_INTERVAL)
        
        # Print final statistics
        if sim_manager.metrics_history:
            final_metrics = sim_manager.metrics_history[-1]
            print("\n" + "="*50)
            print("SIMULATION SUMMARY")
            print("="*50)
            print(f"Total Steps: {final_metrics['timestamp']}")
            print(f"Final Vehicle Count: {final_metrics['total_vehicles']}")
            print(f"Average Speed: {final_metrics['average_speed']:.2f} m/s")
            print(f"Total CO2 Emissions: {final_metrics['co2_emissions']:.2f} mg")
            print(f"Emergency Events: {final_metrics['emergency_events']}")
            print(f"Congested Intersections: {len(final_metrics['congested_intersections'])}")
            
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())