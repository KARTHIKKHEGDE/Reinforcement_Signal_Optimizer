import traci
import asyncio
from collections import defaultdict, deque
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import numpy as np
from tensorflow import keras
from sklearn.preprocessing import StandardScaler

class TrafficLightAgent(Agent):
    def __init__(self, jid: str, password: str):
        super().__init__(jid=jid, password=password)
        self.tls_id = jid.split("@")[0].replace("tls_", "n_")
        self.controlled_lanes = []
        self.phase_history = deque(maxlen=10)
        self.waiting_times = defaultdict(float)
        self.emergency_mode = False
        self.adaptive_threshold = 5
        self.min_phase_duration = 10
        self.max_phase_duration = 60
        self.current_phase_start = 0
        self.learning_rate = 0.1
        self.queue_weights = {}
        self.phase_count = 4
        
        # Add AI-related attributes
        self.model = None
        self.scaler = StandardScaler()
        self.state_history = []
        self.reward_history = []

    async def setup(self):
        """Setup the agent - SUMO initialization happens later"""
        print(f"Setting up agent {self.jid} for TLS {self.tls_id}")
        self.add_behaviour(self.AdaptiveControlBehaviour())
        
    def initialize_sumo_data(self):
        """Initialize agent with SUMO data after TraCI connection is established"""
        try:
            self.controlled_lanes = traci.trafficlight.getControlledLanes(self.tls_id)
            logic = traci.trafficlight.getAllProgramLogics(self.tls_id)[0]
            self.phase_count = len(logic.phases)
            print(f"Agent {self.tls_id} initialized with {self.phase_count} phases and {len(self.controlled_lanes)} lanes")
        except Exception as e:
            print(f"Warning: Could not fully initialize agent {self.tls_id}: {e}")
            self.phase_count = 4  # Default fallback

    def initialize_ai_model(self):
        """Initialize a simple neural network for traffic control"""
        model = keras.Sequential([
            keras.layers.Dense(24, activation='relu', input_shape=(5,)),
            keras.layers.Dense(12, activation='relu'),
            keras.layers.Dense(self.phase_count, activation='softmax')
        ])
        model.compile(optimizer='adam', loss='categorical_crossentropy')
        self.model = model

    class AdaptiveControlBehaviour(CyclicBehaviour):
        """Main behavior for adaptive traffic control"""
        
        async def run(self):
            try:
                # Check if TraCI is connected and running
                if traci.isLoaded() and traci.simulation.getMinExpectedNumber() > 0:
                    # Run the control logic in a thread pool to avoid blocking
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.agent.control_wrapper
                    )
                await asyncio.sleep(0.1)  # Small delay to prevent overwhelming
            except Exception as e:
                print(f"Behaviour error for {self.agent.tls_id}: {e}")
                await asyncio.sleep(1)  # Longer delay on error

    def control_wrapper(self):
        """Wrapper for the control logic to be called from async context"""
        try:
            if traci.isLoaded():
                current_step = traci.simulation.getTime()
                self.adaptive_control(current_step)
        except traci.exceptions.FatalTraCIError:
            print(f"TraCI connection lost for {self.tls_id}")
        except Exception as e:
            print(f"Control error for {self.tls_id}: {e}")

    def get_lane_metrics(self):
        """Get comprehensive lane metrics"""
        metrics = {}
        for lane in self.controlled_lanes:
            try:
                vehicles = traci.lane.getLastStepVehicleIDs(lane)
                waiting_vehicles = []
                
                for v in vehicles:
                    try:
                        if traci.vehicle.getSpeed(v) < 0.5:
                            waiting_vehicles.append(v)
                    except:
                        continue
                
                metrics[lane] = {
                    'vehicle_count': len(vehicles),
                    'waiting_count': len(waiting_vehicles),
                    'avg_speed': traci.lane.getLastStepMeanSpeed(lane),
                    'queue_length': traci.lane.getLastStepLength(lane),
                    'occupancy': traci.lane.getLastStepOccupancy(lane)
                }
            except Exception as e:
                # Fallback for lanes that might not exist
                metrics[lane] = {
                    'vehicle_count': 0,
                    'waiting_count': 0,
                    'avg_speed': 0,
                    'queue_length': 0,
                    'occupancy': 0
                }
        return metrics
    
    def detect_emergency_vehicles(self):
        """Enhanced emergency vehicle detection"""
        emergency_vehicles = []
        for lane in self.controlled_lanes:
            try:
                vehicles = traci.lane.getLastStepVehicleIDs(lane)
                for veh_id in vehicles:
                    try:
                        veh_type = traci.vehicle.getTypeID(veh_id)
                        if veh_type in ['emergency', 'ambulance', 'fire', 'police']:
                            distance = traci.vehicle.getLanePosition(veh_id)
                            emergency_vehicles.append({
                                'id': veh_id,
                                'type': veh_type,
                                'lane': lane,
                                'distance': distance,
                                'speed': traci.vehicle.getSpeed(veh_id)
                            })
                    except:
                        continue
            except:
                continue
        return emergency_vehicles
    
    def calculate_priority_score(self, phase):
        """Calculate priority score for each phase based on traffic conditions"""
        metrics = self.get_lane_metrics()
        score = 0
        
        try:
            # Get lanes that would be green in this phase
            logic = traci.trafficlight.getAllProgramLogics(self.tls_id)[0]
            if phase >= len(logic.phases):
                return 0
                
            phase_def = logic.phases[phase]
            green_lanes = []
            
            for i, lane in enumerate(self.controlled_lanes):
                if i < len(phase_def.state) and phase_def.state[i] in ['G', 'g']:
                    green_lanes.append(lane)
            
            # Calculate score based on waiting vehicles and queue length
            for lane in green_lanes:
                if lane in metrics:
                    score += metrics[lane]['waiting_count'] * 2
                    score += metrics[lane]['vehicle_count']
                    if metrics[lane]['avg_speed'] > 0:
                        score += (1 - min(metrics[lane]['avg_speed'] / 13.89, 1.0)) * 5
                        
        except Exception as e:
            print(f"Warning: Error calculating priority score for {self.tls_id}: {e}")
            return 0
        
        return score
    
    def get_state_features(self):
        """Get state features for AI input"""
        metrics = self.get_lane_metrics()
        features = np.array([
            np.mean([m['vehicle_count'] for m in metrics.values()]),
            np.mean([m['waiting_count'] for m in metrics.values()]),
            np.mean([m['avg_speed'] for m in metrics.values()]),
            np.mean([m['queue_length'] for m in metrics.values()]),
            np.mean([m['occupancy'] for m in metrics.values()])
        ]).reshape(1, -1)
        return self.scaler.fit_transform(features)

    def calculate_reward(self, prev_metrics, current_metrics):
        """Calculate reward based on traffic improvement"""
        prev_waiting = np.mean([m['waiting_count'] for m in prev_metrics.values()])
        current_waiting = np.mean([m['waiting_count'] for m in current_metrics.values()])
        return prev_waiting - current_waiting
        
    # Modify adaptive_control method to use AI
    def adaptive_control(self, current_step):
        """AI-enhanced adaptive traffic control"""
        try:
            if not self.model:
                self.initialize_ai_model()
            
            # Get current state
            state = self.get_state_features()
            
            # Get AI prediction
            phase_probabilities = self.model.predict(state, verbose=0)[0]
            best_phase = np.argmax(phase_probabilities)
            
            # Execute action and get reward
            prev_metrics = self.get_lane_metrics()
            traci.trafficlight.setPhase(self.tls_id, best_phase)
            self.current_phase_start = current_step
            
            # Store state and reward for training
            current_metrics = self.get_lane_metrics()
            reward = self.calculate_reward(prev_metrics, current_metrics)
            self.state_history.append(state)
            self.reward_history.append(reward)
            
        except Exception as e:
            print(f"AI control error for {self.tls_id}: {e}")
            # Fallback to rule-based control
            super().adaptive_control(current_step)
    
    def handle_emergency(self, emergency_vehicles, current_step):
        """Handle emergency vehicle priority"""
        try:
            print(f"Step {current_step}: Emergency vehicles detected at {self.tls_id}: {[v['id'] for v in emergency_vehicles]}")
            
            # Find the best phase for emergency vehicles
            emergency_lanes = set(v['lane'] for v in emergency_vehicles)
            best_phase = 0
            best_coverage = 0
            
            logic = traci.trafficlight.getAllProgramLogics(self.tls_id)[0]
            
            for phase in range(min(self.phase_count, len(logic.phases))):
                phase_def = logic.phases[phase]
                coverage = 0
                
                for i, lane in enumerate(self.controlled_lanes):
                    if (lane in emergency_lanes and 
                        i < len(phase_def.state) and 
                        phase_def.state[i] in ['G', 'g']):
                        coverage += 1
                
                if coverage > best_coverage:
                    best_coverage = coverage
                    best_phase = phase
            
            traci.trafficlight.setPhase(self.tls_id, best_phase)
            self.current_phase_start = current_step
            self.emergency_mode = True
            
        except Exception as e:
            print(f"Warning: Error handling emergency for {self.tls_id}: {e}")
    
    def switch_to_best_phase(self, current_step):
        """Switch to the phase with highest priority"""
        try:
            best_phase = 0
            best_score = 0
            
            for phase in range(self.phase_count):
                score = self.calculate_priority_score(phase)
                if score > best_score:
                    best_score = score
                    best_phase = phase
            
            current_phase = traci.trafficlight.getPhase(self.tls_id)
            if best_phase != current_phase:
                print(f"Step {current_step}: TLS {self.tls_id} adaptive switch to phase {best_phase}")
                traci.trafficlight.setPhase(self.tls_id, best_phase)
                self.current_phase_start = current_step
                
        except Exception as e:
            print(f"Warning: Error switching phase for {self.tls_id}: {e}")


class EmergencyCoordinator(Agent):
    def __init__(self, jid: str, password: str):
        super().__init__(jid=jid, password=password)
        self.emergency_alerts = []

    async def setup(self):
        """Setup emergency coordinator"""
        print(f"Setting up emergency coordinator {self.jid}")
        self.add_behaviour(self.EmergencyHandlerBehaviour())

    class EmergencyHandlerBehaviour(CyclicBehaviour):
        """Handle emergency vehicle coordination"""
        
        async def run(self):
            try:
                # Check for emergency messages
                msg = await self.receive(timeout=1)
                if msg:
                    print(f"Emergency alert received: {msg.body}")
                    self.agent.emergency_alerts.append(msg.body)
                
                # Detect emergency vehicles in simulation
                if traci.isLoaded():
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.agent.scan_emergency_vehicles
                    )
                    
            except Exception as e:
                print(f"Emergency coordinator error: {e}")
            
            await asyncio.sleep(0.5)  # Check every 0.5 seconds

    def scan_emergency_vehicles(self):
        """Scan for emergency vehicles in the simulation"""
        try:
            all_vehicles = traci.vehicle.getIDList()
            emergency_vehicles = []
            
            for veh_id in all_vehicles:
                try:
                    veh_type = traci.vehicle.getTypeID(veh_id)
                    if veh_type in ['emergency', 'ambulance', 'fire', 'police']:
                        route = traci.vehicle.getRouteID(veh_id)
                        position = traci.vehicle.getPosition(veh_id)
                        emergency_vehicles.append({
                            'id': veh_id,
                            'type': veh_type,
                            'route': route,
                            'position': position
                        })
                except:
                    continue
            
            if emergency_vehicles:
                print(f"Emergency coordinator detected {len(emergency_vehicles)} emergency vehicles")
                
        except Exception as e:
            print(f"Error scanning emergency vehicles: {e}")


# Alternative: Simple traffic controller without SPADE (for testing)
class SimpleTrafficController:
    """Fallback controller that doesn't require SPADE server"""
    
    def __init__(self, tls_id):
        self.tls_id = tls_id
        self.current_phase_start = 0
        self.min_phase_duration = 10
        self.max_phase_duration = 60
        self.phase_count = 4
    
    def adaptive_control(self, current_step):
        """Simple adaptive control without agents"""
        try:
            current_phase = traci.trafficlight.getPhase(self.tls_id)
            phase_duration = current_step - self.current_phase_start
            
            # Force change if maximum duration exceeded
            if phase_duration > self.max_phase_duration:
                next_phase = (current_phase + 1) % self.phase_count
                print(f"Step {current_step}: TLS {self.tls_id} switching to phase {next_phase}")
                traci.trafficlight.setPhase(self.tls_id, next_phase)
                self.current_phase_start = current_step
                
        except Exception as e:
            print(f"Warning: Error in simple control for {self.tls_id}: {e}")