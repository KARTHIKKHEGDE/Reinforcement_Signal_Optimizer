"""
TraCI Handler - Interface with running SUMO simulation
Collects real-time metrics and controls traffic signals
"""
import traci
from typing import Dict, List, Optional
import os
from app.config import settings


class TraCIHandler:
    def __init__(self):
        self.connected = False
        self.junction_ids: List[str] = []
        self.lane_ids: List[str] = []
        
    def connect(self, port: int = 8813) -> bool:
        """
        Connect to SUMO via TraCI
        
        Args:
            port: TraCI port number
            
        Returns:
            bool: True if connected successfully
        """
        try:
            if self.connected:
                return True
            
            traci.init(port)
            self.connected = True
            
            # Get junction and lane IDs
            self.junction_ids = traci.trafficlight.getIDList()
            self.lane_ids = traci.lane.getIDList()
            
            print(f"TraCI connected. Found {len(self.junction_ids)} junctions")
            return True
            
        except Exception as e:
            print(f"Error connecting to TraCI: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from TraCI"""
        try:
            if self.connected:
                traci.close()
                self.connected = False
                print("TraCI disconnected")
        except Exception as e:
            print(f"Error disconnecting TraCI: {e}")
    
    def get_metrics(self) -> Dict:
        """
        Get real-time simulation metrics
        
        Returns:
            dict: Current simulation metrics
        """
        if not self.connected:
            return self._get_empty_metrics()
        
        try:
            # Get current simulation time
            current_time = traci.simulation.getTime()
            
            # Calculate queue lengths
            total_queue = sum(
                traci.lane.getLastStepHaltingNumber(lane_id)
                for lane_id in self.lane_ids
            )
            
            # Calculate waiting times
            vehicle_ids = traci.vehicle.getIDList()
            total_waiting_time = sum(
                traci.vehicle.getWaitingTime(veh_id)
                for veh_id in vehicle_ids
            )
            avg_waiting_time = total_waiting_time / len(vehicle_ids) if vehicle_ids else 0
            
            # Get traffic light states
            traffic_lights = {}
            for junction_id in self.junction_ids:
                phase = traci.trafficlight.getPhase(junction_id)
                state = traci.trafficlight.getRedYellowGreenState(junction_id)
                traffic_lights[junction_id] = {
                    "phase": phase,
                    "state": state
                }
            
            # Calculate throughput
            departed = traci.simulation.getDepartedNumber()
            arrived = traci.simulation.getArrivedNumber()
            
            return {
                "time": current_time,
                "queue_length": total_queue,
                "waiting_time": avg_waiting_time,
                "total_waiting_time": total_waiting_time,
                "vehicle_count": len(vehicle_ids),
                "departed_vehicles": departed,
                "arrived_vehicles": arrived,
                "traffic_lights": traffic_lights,
                "timestamp": current_time
            }
            
        except Exception as e:
            print(f"Error getting metrics: {e}")
            return self._get_empty_metrics()
    
    def set_traffic_light_phase(self, junction_id: str, phase: int) -> bool:
        """
        Set traffic light phase (used by RL agent)
        
        Args:
            junction_id: Traffic light junction ID
            phase: Phase index to set
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.connected:
                return False
            
            traci.trafficlight.setPhase(junction_id, phase)
            return True
            
        except Exception as e:
            print(f"Error setting traffic light phase: {e}")
            return False
    
    def simulation_step(self) -> bool:
        """
        Advance simulation by one step
        
        Returns:
            bool: True if successful
        """
        try:
            if not self.connected:
                return False
            
            traci.simulationStep()
            return True
            
        except Exception as e:
            print(f"Error in simulation step: {e}")
            return False
    
    def _get_empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        return {
            "time": 0,
            "queue_length": 0,
            "waiting_time": 0,
            "total_waiting_time": 0,
            "vehicle_count": 0,
            "departed_vehicles": 0,
            "arrived_vehicles": 0,
            "traffic_lights": {},
            "timestamp": 0
        }


# Global TraCI handler instance
traci_handler = TraCIHandler()
