import traci
import sumolib
import os
import json
import random
import numpy as np
from collections import defaultdict, deque
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
import asyncio

class TrafficLightAgent(Agent):
    def __init__(self, jid, password):
        super().__init__(jid=jid, password=password)
        self.tls_id = jid.split("@")[0]
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

    async def setup(self):
        print(f"Initializing agent {self.jid}")
        try:
            self.controlled_lanes = traci.trafficlight.getControlledLanes(self.tls_id)
            logic = traci.trafficlight.getAllProgramLogics(self.tls_id)[0]
            self.phase_count = len(logic.phases)
        except Exception as e:
            print(f"Warning: {self.jid} initialization error: {e}")
            self.phase_count = 4
        
        self.add_behaviour(self.AdaptiveControlBehaviour())

    class AdaptiveControlBehaviour(CyclicBehaviour):
        async def run(self):
            current_step = traci.simulation.getTime()
            self.agent.adaptive_control(current_step)
            await asyncio.sleep(0.1)

    # Keep all other methods (get_lane_metrics, adaptive_control, etc.) unchanged

    def initialize(self):
        """Initialize agent with SUMO data"""
        try:
            self.controlled_lanes = traci.trafficlight.getControlledLanes(self.tls_id)
            logic = traci.trafficlight.getAllProgramLogics(self.tls_id)[0]
            self.phase_count = len(logic.phases)
        except Exception as e:
            print(f"Warning: Could not fully initialize agent {self.tls_id}: {e}")
            self.phase_count = 4  # Default fallback
        
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
    
    def adaptive_control(self, current_step):
        """Adaptive traffic light control algorithm"""
        try:
            current_phase = traci.trafficlight.getPhase(self.tls_id)
            phase_duration = current_step - self.current_phase_start
            
            # Check for emergency vehicles first
            emergency_vehicles = self.detect_emergency_vehicles()
            if emergency_vehicles:
                self.handle_emergency(emergency_vehicles, current_step)
                return
            
            # Don't change if minimum duration not met
            if phase_duration < self.min_phase_duration:
                return
                
            # Force change if maximum duration exceeded
            if phase_duration > self.max_phase_duration:
                self.switch_to_best_phase(current_step)
                return
                
            # Adaptive switching based on traffic conditions
            current_score = self.calculate_priority_score(current_phase)
            best_phase = current_phase
            best_score = current_score
            
            for phase in range(self.phase_count):
                if phase != current_phase:
                    score = self.calculate_priority_score(phase)
                    if score > best_score * 1.5:  # 50% improvement threshold
                        best_phase = phase
                        best_score = score
            
            if best_phase != current_phase:
                print(f"Step {current_step}: TLS {self.tls_id} switching from phase {current_phase} to {best_phase} (score: {best_score:.2f})")
                traci.trafficlight.setPhase(self.tls_id, best_phase)
                self.current_phase_start = current_step
                
        except Exception as e:
            print(f"Warning: Error in adaptive control for {self.tls_id}: {e}")
    
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

class NetworkGenerator:
    """Generate SUMO network files"""
    
    @staticmethod
    def create_node_file():
        """Create nodes file for netconvert"""
        nodes_content = """<?xml version="1.0" encoding="UTF-8"?>
<nodes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/nodes_file.xsd">
    <node id="n_0_0" x="0" y="0" type="traffic_light"/>
    <node id="n_0_1" x="0" y="200" type="traffic_light"/>
    <node id="n_0_2" x="0" y="400" type="traffic_light"/>
    <node id="n_1_0" x="200" y="0" type="traffic_light"/>
    <node id="n_1_1" x="200" y="200" type="traffic_light"/>
    <node id="n_1_2" x="200" y="400" type="traffic_light"/>
    <node id="n_2_0" x="400" y="0" type="traffic_light"/>
    <node id="n_2_1" x="400" y="200" type="traffic_light"/>
    <node id="n_2_2" x="400" y="400" type="traffic_light"/>
</nodes>"""
        
        with open('nodes.nod.xml', 'w') as f:
            f.write(nodes_content)
        print("Nodes file 'nodes.nod.xml' created successfully!")
    
    @staticmethod
    def create_edges_file():
        """Create edges file for netconvert"""
        edges_content = """<?xml version="1.0" encoding="UTF-8"?>
<edges xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/edges_file.xsd">
    <!-- Horizontal edges -->
    <edge id="h_0_0_to_1_0" from="n_0_0" to="n_1_0" numLanes="2" speed="13.89"/>
    <edge id="h_1_0_to_0_0" from="n_1_0" to="n_0_0" numLanes="2" speed="13.89"/>
    <edge id="h_1_0_to_2_0" from="n_1_0" to="n_2_0" numLanes="2" speed="13.89"/>
    <edge id="h_2_0_to_1_0" from="n_2_0" to="n_1_0" numLanes="2" speed="13.89"/>
    
    <edge id="h_0_1_to_1_1" from="n_0_1" to="n_1_1" numLanes="2" speed="13.89"/>
    <edge id="h_1_1_to_0_1" from="n_1_1" to="n_0_1" numLanes="2" speed="13.89"/>
    <edge id="h_1_1_to_2_1" from="n_1_1" to="n_2_1" numLanes="2" speed="13.89"/>
    <edge id="h_2_1_to_1_1" from="n_2_1" to="n_1_1" numLanes="2" speed="13.89"/>
    
    <edge id="h_0_2_to_1_2" from="n_0_2" to="n_1_2" numLanes="2" speed="13.89"/>
    <edge id="h_1_2_to_0_2" from="n_1_2" to="n_0_2" numLanes="2" speed="13.89"/>
    <edge id="h_1_2_to_2_2" from="n_1_2" to="n_2_2" numLanes="2" speed="13.89"/>
    <edge id="h_2_2_to_1_2" from="n_2_2" to="n_1_2" numLanes="2" speed="13.89"/>
    
    <!-- Vertical edges -->
    <edge id="v_0_0_to_0_1" from="n_0_0" to="n_0_1" numLanes="2" speed="13.89"/>
    <edge id="v_0_1_to_0_0" from="n_0_1" to="n_0_0" numLanes="2" speed="13.89"/>
    <edge id="v_0_1_to_0_2" from="n_0_1" to="n_0_2" numLanes="2" speed="13.89"/>
    <edge id="v_0_2_to_0_1" from="n_0_2" to="n_0_1" numLanes="2" speed="13.89"/>
    
    <edge id="v_1_0_to_1_1" from="n_1_0" to="n_1_1" numLanes="2" speed="13.89"/>
    <edge id="v_1_1_to_1_0" from="n_1_1" to="n_1_0" numLanes="2" speed="13.89"/>
    <edge id="v_1_1_to_1_2" from="n_1_1" to="n_1_2" numLanes="2" speed="13.89"/>
    <edge id="v_1_2_to_1_1" from="n_1_2" to="n_1_1" numLanes="2" speed="13.89"/>
    
    <edge id="v_2_0_to_2_1" from="n_2_0" to="n_2_1" numLanes="2" speed="13.89"/>
    <edge id="v_2_1_to_2_0" from="n_2_1" to="n_2_0" numLanes="2" speed="13.89"/>
    <edge id="v_2_1_to_2_2" from="n_2_1" to="n_2_2" numLanes="2" speed="13.89"/>
    <edge id="v_2_2_to_2_1" from="n_2_2" to="n_2_1" numLanes="2" speed="13.89"/>
</edges>"""
        
        with open('edges.edg.xml', 'w') as f:
            f.write(edges_content)
        print("Edges file 'edges.edg.xml' created successfully!")
    
    @staticmethod
    def create_network_xml():
        """Create network using netconvert or fallback to simple network"""
        # First create node and edge files
        NetworkGenerator.create_node_file()
        NetworkGenerator.create_edges_file()
        
        # Try to use netconvert to create the network
        try:
            import subprocess
            result = subprocess.run([
                'netconvert',
                '--node-files=nodes.nod.xml',
                '--edge-files=edges.edg.xml',
                '--output-file=network.net.xml',
                '--tls.guess=true',
                '--no-warnings=true'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("Network file 'network.net.xml' created successfully using netconvert!")
                return
            else:
                print(f"netconvert failed: {result.stderr}")
                raise Exception("netconvert failed")
        
        except Exception as e:
            print(f"Could not use netconvert ({e}), creating simple network manually...")
            NetworkGenerator.create_simple_network()
    
    @staticmethod
    def create_simple_network():
        """Create a simple working network file manually"""
        network_content = """<?xml version="1.0" encoding="UTF-8"?>
<net version="1.16" junctionCornerDetail="5" limitTurnSpeed="5.50" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/net_file.xsd">

    <location netOffset="0.00,0.00" convBoundary="-100.00,-100.00,500.00,500.00" origBoundary="-100.00,-100.00,500.00,500.00" projParameter="!"/>

    <edge id="h_0_0_to_1_0" from="n_0_0" to="n_1_0" priority="1">
        <lane id="h_0_0_to_1_0_0" index="0" speed="13.89" length="200.00" shape="0.00,-1.60 200.00,-1.60"/>
        <lane id="h_0_0_to_1_0_1" index="1" speed="13.89" length="200.00" shape="0.00,1.60 200.00,1.60"/>
    </edge>
    <edge id="h_1_0_to_0_0" from="n_1_0" to="n_0_0" priority="1">
        <lane id="h_1_0_to_0_0_0" index="0" speed="13.89" length="200.00" shape="200.00,1.60 0.00,1.60"/>
        <lane id="h_1_0_to_0_0_1" index="1" speed="13.89" length="200.00" shape="200.00,-1.60 0.00,-1.60"/>
    </edge>
    <edge id="h_1_0_to_2_0" from="n_1_0" to="n_2_0" priority="1">
        <lane id="h_1_0_to_2_0_0" index="0" speed="13.89" length="200.00" shape="200.00,-1.60 400.00,-1.60"/>
        <lane id="h_1_0_to_2_0_1" index="1" speed="13.89" length="200.00" shape="200.00,1.60 400.00,1.60"/>
    </edge>
    <edge id="h_2_0_to_1_0" from="n_2_0" to="n_1_0" priority="1">
        <lane id="h_2_0_to_1_0_0" index="0" speed="13.89" length="200.00" shape="400.00,1.60 200.00,1.60"/>
        <lane id="h_2_0_to_1_0_1" index="1" speed="13.89" length="200.00" shape="400.00,-1.60 200.00,-1.60"/>
    </edge>
    
    <edge id="v_0_0_to_0_1" from="n_0_0" to="n_0_1" priority="1">
        <lane id="v_0_0_to_0_1_0" index="0" speed="13.89" length="200.00" shape="-1.60,0.00 -1.60,200.00"/>
        <lane id="v_0_0_to_0_1_1" index="1" speed="13.89" length="200.00" shape="1.60,0.00 1.60,200.00"/>
    </edge>
    <edge id="v_0_1_to_0_0" from="n_0_1" to="n_0_0" priority="1">
        <lane id="v_0_1_to_0_0_0" index="0" speed="13.89" length="200.00" shape="1.60,200.00 1.60,0.00"/>
        <lane id="v_0_1_to_0_0_1" index="1" speed="13.89" length="200.00" shape="-1.60,200.00 -1.60,0.00"/>
    </edge>
    <edge id="v_1_0_to_1_1" from="n_1_0" to="n_1_1" priority="1">
        <lane id="v_1_0_to_1_1_0" index="0" speed="13.89" length="200.00" shape="198.40,0.00 198.40,200.00"/>
        <lane id="v_1_0_to_1_1_1" index="1" speed="13.89" length="200.00" shape="201.60,0.00 201.60,200.00"/>
    </edge>
    <edge id="v_1_1_to_1_0" from="n_1_1" to="n_1_0" priority="1">
        <lane id="v_1_1_to_1_0_0" index="0" speed="13.89" length="200.00" shape="201.60,200.00 201.60,0.00"/>
        <lane id="v_1_1_to_1_0_1" index="1" speed="13.89" length="200.00" shape="198.40,200.00 198.40,0.00"/>
    </edge>

    <junction id="n_0_0" type="traffic_light" x="0.00" y="0.00" incLanes="h_1_0_to_0_0_0 h_1_0_to_0_0_1 v_0_1_to_0_0_0 v_0_1_to_0_0_1" intLanes=":n_0_0_0_0 :n_0_0_1_0 :n_0_0_2_0 :n_0_0_3_0" shape="-3.20,0.00 3.20,0.00 0.00,-3.20 0.00,3.20">
        <request index="0" response="0000" foes="1000" cont="0"/>
        <request index="1" response="0000" foes="0100" cont="0"/>
        <request index="2" response="0000" foes="0010" cont="0"/>
        <request index="3" response="0000" foes="0001" cont="0"/>
    </junction>
    <junction id="n_0_1" type="traffic_light" x="0.00" y="200.00" incLanes="v_0_0_to_0_1_0 v_0_0_to_0_1_1" intLanes=":n_0_1_0_0 :n_0_1_1_0" shape="-3.20,200.00 3.20,200.00">
        <request index="0" response="00" foes="00" cont="0"/>
        <request index="1" response="00" foes="00" cont="0"/>
    </junction>
    <junction id="n_1_0" type="traffic_light" x="200.00" y="0.00" incLanes="h_0_0_to_1_0_0 h_0_0_to_1_0_1 h_2_0_to_1_0_0 h_2_0_to_1_0_1 v_1_1_to_1_0_0 v_1_1_to_1_0_1" intLanes=":n_1_0_0_0 :n_1_0_1_0 :n_1_0_2_0 :n_1_0_3_0 :n_1_0_4_0 :n_1_0_5_0" shape="196.80,0.00 203.20,0.00 200.00,-3.20 200.00,3.20">
        <request index="0" response="000000" foes="100000" cont="0"/>
        <request index="1" response="000000" foes="010000" cont="0"/>
        <request index="2" response="000000" foes="001000" cont="0"/>
        <request index="3" response="000000" foes="000100" cont="0"/>
        <request index="4" response="000000" foes="000010" cont="0"/>
        <request index="5" response="000000" foes="000001" cont="0"/>
    </junction>
    <junction id="n_1_1" type="traffic_light" x="200.00" y="200.00" incLanes="v_1_0_to_1_1_0 v_1_0_to_1_1_1" intLanes=":n_1_1_0_0 :n_1_1_1_0" shape="196.80,200.00 203.20,200.00">
        <request index="0" response="00" foes="00" cont="0"/>
        <request index="1" response="00" foes="00" cont="0"/>
    </junction>
    <junction id="n_2_0" type="traffic_light" x="400.00" y="0.00" incLanes="h_1_0_to_2_0_0 h_1_0_to_2_0_1" intLanes=":n_2_0_0_0 :n_2_0_1_0" shape="400.00,-3.20 400.00,3.20">
        <request index="0" response="00" foes="00" cont="0"/>
        <request index="1" response="00" foes="00" cont="0"/>
    </junction>

    <connection from="h_0_0_to_1_0" to="h_1_0_to_2_0" fromLane="0" toLane="0" via=":n_1_0_0_0" tl="n_1_0" linkIndex="0" dir="s" state="G"/>
    <connection from="h_0_0_to_1_0" to="h_1_0_to_2_0" fromLane="1" toLane="1" via=":n_1_0_1_0" tl="n_1_0" linkIndex="1" dir="s" state="G"/>
    <connection from="h_0_0_to_1_0" to="v_1_0_to_1_1" fromLane="0" toLane="0" via=":n_1_0_2_0" tl="n_1_0" linkIndex="2" dir="l" state="r"/>
    <connection from="h_1_0_to_0_0" to="v_0_0_to_0_1" fromLane="0" toLane="0" via=":n_0_0_0_0" tl="n_0_0" linkIndex="0" dir="r" state="G"/>
    <connection from="h_2_0_to_1_0" to="h_1_0_to_0_0" fromLane="0" toLane="0" via=":n_1_0_3_0" tl="n_1_0" linkIndex="3" dir="s" state="r"/>
    <connection from="h_2_0_to_1_0" to="h_1_0_to_0_0" fromLane="1" toLane="1" via=":n_1_0_4_0" tl="n_1_0" linkIndex="4" dir="s" state="r"/>
    <connection from="v_0_0_to_0_1" to="v_0_1_to_0_0" fromLane="0" toLane="0" via=":n_0_1_0_0" tl="n_0_1" linkIndex="0" dir="t" state="G"/>
    <connection from="v_0_1_to_0_0" to="h_0_0_to_1_0" fromLane="0" toLane="0" via=":n_0_0_1_0" tl="n_0_0" linkIndex="1" dir="r" state="r"/>
    <connection from="v_1_0_to_1_1" to="v_1_1_to_1_0" fromLane="0" toLane="0" via=":n_1_1_0_0" tl="n_1_1" linkIndex="0" dir="t" state="G"/>
    <connection from="v_1_1_to_1_0" to="v_1_0_to_1_1" fromLane="0" toLane="0" via=":n_1_0_5_0" tl="n_1_0" linkIndex="5" dir="r" state="G"/>

    <tlLogic id="n_0_0" type="static" programID="0" offset="0">
        <phase duration="31" state="GGrr"/>
        <phase duration="4" state="yyrr"/>
        <phase duration="31" state="rrGG"/>
        <phase duration="4" state="rryy"/>
    </tlLogic>
    <tlLogic id="n_0_1" type="static" programID="0" offset="0">
        <phase duration="35" state="GG"/>
        <phase duration="35" state="GG"/>
    </tlLogic>
    <tlLogic id="n_1_0" type="static" programID="0" offset="0">
        <phase duration="31" state="GGGrrr"/>
        <phase duration="4" state="yyyrrr"/>
        <phase duration="31" state="rrrGGG"/>
        <phase duration="4" state="rrryyy"/>
    </tlLogic>
    <tlLogic id="n_1_1" type="static" programID="0" offset="0">
        <phase duration="35" state="GG"/>
        <phase duration="35" state="GG"/>
    </tlLogic>
    <tlLogic id="n_2_0" type="static" programID="0" offset="0">
        <phase duration="35" state="GG"/>
        <phase duration="35" state="GG"/>
    </tlLogic>

</net>"""
        
        with open('network.net.xml', 'w') as f:
            f.write(network_content)
        print("Simple network file 'network.net.xml' created successfully!")
    
    @staticmethod
    def create_routes_xml():
        """Create simple but working traffic routes"""
        routes_content = """<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    
    <!-- Vehicle Types -->
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5.0" maxSpeed="55.56"/>
    <vType id="emergency" accel="3.0" decel="5.0" sigma="0.2" length="7.0" maxSpeed="69.44" color="1,0,0"/>
    <vType id="bus" accel="1.5" decel="3.5" sigma="0.3" length="12.0" maxSpeed="44.44"/>
    
    <!-- Routes -->
    <route id="horizontal_1" edges="h_0_0_to_1_0 h_1_0_to_2_0"/>
    <route id="horizontal_2" edges="h_2_0_to_1_0 h_1_0_to_0_0"/>
    <route id="vertical_1" edges="v_0_0_to_0_1"/>
    <route id="vertical_2" edges="v_0_1_to_0_0"/>
    <route id="through_1" edges="v_1_0_to_1_1 v_1_1_to_1_0"/>
    <route id="through_2" edges="v_1_1_to_1_0 v_1_0_to_1_1"/>
    
    <!-- Traffic flows -->
    <flow id="flow_h1" route="horizontal_1" begin="0" end="3600" vehsPerHour="400" type="car"/>
    <flow id="flow_h2" route="horizontal_2" begin="0" end="3600" vehsPerHour="350" type="car"/>
    <flow id="flow_v1" route="vertical_1" begin="0" end="3600" vehsPerHour="200" type="car"/>
    <flow id="flow_v2" route="vertical_2" begin="0" end="3600" vehsPerHour="250" type="car"/>
    <flow id="flow_t1" route="through_1" begin="0" end="3600" vehsPerHour="300" type="car"/>
    <flow id="flow_t2" route="through_2" begin="0" end="3600" vehsPerHour="280" type="car"/>
    
    <!-- Emergency vehicles (occasional) -->
    <flow id="emergency_flow" route="horizontal_1" begin="300" end="3600" period="600" type="emergency"/>
    
    <!-- Bus routes -->
    <flow id="bus_flow" route="horizontal_1" begin="120" end="3600" period="300" type="bus"/>
    
</routes>"""
        
        with open('routes.rou.xml', 'w') as f:
            f.write(routes_content)
        print("Routes file 'routes.rou.xml' created successfully!")
    
    @staticmethod
    def create_config_file():
        """Create SUMO configuration file"""
        config_content = """<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="network.net.xml"/>
        <route-files value="routes.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
        <step-length value="1"/>
    </time>
    <processing>
        <time-to-teleport value="300"/>
    </processing>
    <report>
        <verbose value="false"/>
        <no-step-log value="true"/>
    </report>
    <gui_only>
        <gui-settings-file value="gui-settings.xml"/>
    </gui_only>
</configuration>"""
        
        with open('simulation.sumocfg', 'w') as f:
            f.write(config_content)
        print("Configuration file 'simulation.sumocfg' created successfully!")
    
    @staticmethod
    def create_gui_settings():
        """Create GUI settings for better visualization"""
        gui_content = """<?xml version="1.0" encoding="UTF-8"?>
<viewsettings>
    <viewport zoom="200" x="200" y="200"/>
    <delay value="100"/>
    <scheme name="standard">
        <edges>
            <edge_attr color="black" width="1.0"/>
        </edges>
        <vehicles>
            <vehicle_attr size="1.0" color="yellow"/>
        </vehicles>
        <junctions>
            <junction_attr color="black" size="2.0"/>
        </junctions>
    </scheme>
</viewsettings>"""
        
        with open('gui-settings.xml', 'w') as f:
            f.write(gui_content)
        print("GUI settings file 'gui-settings.xml' created successfully!")

class TrafficMetrics:
    """Collect and analyze traffic performance metrics"""
    
    def __init__(self):
        self.step_data = []
        self.vehicle_data = defaultdict(list)
        self.tls_data = defaultdict(list)
        
    def collect_step_data(self, step):
        """Collect data for current simulation step"""
        try:
            # Get all vehicle IDs
            vehicle_ids = traci.vehicle.getIDList()
            
            total_waiting = 0
            total_travel_time = 0
            total_fuel = 0
            total_co2 = 0
            
            for veh_id in vehicle_ids:
                try:
                    waiting_time = traci.vehicle.getWaitingTime(veh_id)
                    total_waiting += waiting_time
                    
                    # Get fuel consumption and emissions if available
                    try:
                        fuel = traci.vehicle.getFuelConsumption(veh_id)
                        co2 = traci.vehicle.getCO2Emission(veh_id)
                        total_fuel += fuel
                        total_co2 += co2
                    except:
                        pass  # Some SUMO versions don't support these
                        
                except traci.TraCIException:
                    continue
            
            step_metrics = {
                'step': step,
                'vehicle_count': len(vehicle_ids),
                'total_waiting_time': total_waiting,
                'avg_waiting_time': total_waiting / max(len(vehicle_ids), 1),
                'total_fuel': total_fuel,
                'total_co2': total_co2,
                'throughput': len(vehicle_ids)
            }
            
            self.step_data.append(step_metrics)
            
        except Exception as e:
            print(f"Warning: Could not collect metrics for step {step}: {e}")
    
    def get_summary_statistics(self):
        """Calculate summary statistics"""
        if not self.step_data:
            return {}
        
        total_vehicles = sum(d['vehicle_count'] for d in self.step_data)
        avg_waiting = sum(d['avg_waiting_time'] for d in self.step_data) / len(self.step_data)
        total_fuel = sum(d['total_fuel'] for d in self.step_data)
        total_co2 = sum(d['total_co2'] for d in self.step_data)
        
        return {
            'total_simulation_steps': len(self.step_data),
            'total_vehicles_processed': total_vehicles,
            'average_waiting_time': avg_waiting,
            'total_fuel_consumption': total_fuel,
            'total_co2_emissions': total_co2,
            'average_throughput': total_vehicles / len(self.step_data)
        }
    
    def save_results(self, filename="traffic_results.txt"):
        """Save results to file"""
        stats = self.get_summary_statistics()
        
        with open(filename, 'w') as f:
            f.write("Traffic Simulation Results\n")
            f.write("=" * 30 + "\n\n")
            
            for key, value in stats.items():
                f.write(f"{key}: {value:.2f}\n")
            
            f.write("\nStep-by-step data:\n")
            f.write("-" * 20 + "\n")
            
            for data in self.step_data[-10:]:  # Last 10 steps
                f.write(f"Step {data['step']}: {data['vehicle_count']} vehicles, "
                       f"avg wait: {data['avg_waiting_time']:.2f}s\n")
        
        print(f"Results saved to {filename}")

class AdaptiveTrafficController:
    """Main controller for the adaptive traffic light system"""
    
    def __init__(self):
        self.agents = {}
        self.metrics = TrafficMetrics()
        self.simulation_running = False
        
    def setup_simulation(self):
        """Setup the complete simulation environment"""
        print("Setting up simulation environment...")
        
        # Generate all necessary files
        NetworkGenerator.create_network_xml()
        NetworkGenerator.create_routes_xml()
        NetworkGenerator.create_config_file()
        NetworkGenerator.create_gui_settings()
        
        print("All simulation files created successfully!")
        
    def initialize_agents(self):
        """Initialize traffic light agents"""
        try:
            tls_ids = traci.trafficlight.getIDList()
            print(f"Found {len(tls_ids)} traffic light systems: {tls_ids}")
            
            for tls_id in tls_ids:
                agent = TrafficLightAgent(tls_id)
                agent.initialize()
                self.agents[tls_id] = agent
                print(f"Initialized agent for TLS {tls_id}")
                
        except Exception as e:
            print(f"Error initializing agents: {e}")
            
    def run_simulation(self, gui=True, duration=3600):
        """Run the complete simulation"""
        try:
            # Start SUMO
            if gui:
                sumoBinary = "sumo-gui"
            else:
                sumoBinary = "sumo"
            
            sumoCmd = [sumoBinary, "-c", "simulation.sumocfg"]
            
            print(f"Starting SUMO with command: {' '.join(sumoCmd)}")
            traci.start(sumoCmd)
            
            self.simulation_running = True
            self.initialize_agents()
            
            step = 0
            print(f"Running simulation for {duration} steps...")
            
            while step < duration and traci.simulation.getMinExpectedNumber() > 0:
                traci.simulationStep()
                
                # Update all traffic light agents
                for agent in self.agents.values():
                    agent.adaptive_control(step)
                
                # Collect metrics every 10 steps
                if step % 10 == 0:
                    self.metrics.collect_step_data(step)
                
                # Progress update every 300 steps (5 minutes)
                if step % 300 == 0:
                    vehicle_count = len(traci.vehicle.getIDList())
                    print(f"Step {step}: {vehicle_count} vehicles in simulation")
                
                step += 1
            
            print(f"Simulation completed after {step} steps")
            
        except Exception as e:
            print(f"Error during simulation: {e}")
            
        finally:
            if self.simulation_running:
                traci.close()
                self.simulation_running = False
            
            # Save results
            self.metrics.save_results()
            print("Simulation ended and results saved")
    
    def run_comparison_study(self):
        """Run comparison between adaptive and fixed-time control"""
        print("Running comparison study...")
        
        # First run with adaptive control
        print("\n--- Running with Adaptive Control ---")
        self.run_simulation(gui=False, duration=1800)  # 30 minutes
        self.metrics.save_results("adaptive_results.txt")
        
        # Reset for second run
        adaptive_stats = self.metrics.get_summary_statistics()
        self.metrics = TrafficMetrics()
        
        # Run with fixed-time control (disable adaptive control)
        print("\n--- Running with Fixed-Time Control ---")
        # TODO: Implement fixed-time comparison
        # For now, just show the adaptive results
        
        print("\n--- Comparison Results ---")
        print("Adaptive Control Performance:")
        for key, value in adaptive_stats.items():
            print(f"  {key}: {value:.2f}")

def main():
    """Main function to run the traffic control system"""
    print("Advanced Adaptive Traffic Light Control System")
    print("=" * 50)
    
    controller = AdaptiveTrafficController()
    
    try:
        # Setup simulation files
        controller.setup_simulation()
        
        # Ask user for simulation type
        print("\nSimulation Options:")
        print("1. Run with GUI (interactive)")
        print("2. Run without GUI (faster)")
        print("3. Run comparison study")
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            controller.run_simulation(gui=True)
        elif choice == "2":
            controller.run_simulation(gui=False)
        elif choice == "3":
            controller.run_comparison_study()
        else:
            print("Invalid choice, running with GUI...")
            controller.run_simulation(gui=True)
            
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Program ended")

if __name__ == "__main__":
    main() 