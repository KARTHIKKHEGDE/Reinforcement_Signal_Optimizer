"""
Reward Functions for Traffic Signal Optimization
Optimized for Silk Board Junction, Bangalore based on govt congestion data
"""
import traci


def calculate_reward_simple(junction_id: str) -> float:
    """
    Simple reward function based on total waiting time
    Suitable for Bangalore's severe congestion patterns
    
    Args:
        junction_id: SUMO junction ID
        
    Returns:
        float: Negative reward (minimize waiting time)
    """
    total_waiting_time = 0.0
    
    for vehicle_id in traci.vehicle.getIDList():
        total_waiting_time += traci.vehicle.getWaitingTime(vehicle_id)
    
    # Negative reward: we want to minimize waiting time
    return -total_waiting_time


def calculate_reward_balanced(junction_id: str) -> float:
    """
    Balanced reward function for Silk Board Junction
    Based on Karnataka govt congestion study metrics
    
    Penalizes:
    - Total waiting time (primary metric)
    - Queue length (prevents gridlock)
    
    Args:
        junction_id: SUMO junction ID
        
    Returns:
        float: Combined negative reward
    """
    total_waiting_time = 0.0
    total_queue_length = 0
    
    # Get all lanes at the junction
    try:
        lanes = traci.trafficlight.getControlledLanes(junction_id)
        
        # Calculate queue lengths
        for lane_id in set(lanes):  # Use set to avoid duplicates
            total_queue_length += traci.lane.getLastStepHaltingNumber(lane_id)
    except:
        # Fallback if junction_id is invalid
        pass
    
    # Calculate total waiting time
    for vehicle_id in traci.vehicle.getIDList():
        total_waiting_time += traci.vehicle.getWaitingTime(vehicle_id)
    
    # Balanced reward formula (calibrated for Bangalore traffic)
    # Higher weight on waiting time due to severe congestion at Silk Board
    reward = -(total_waiting_time + 0.5 * total_queue_length)
    
    return reward


def calculate_reward_advanced(junction_id: str, prev_phase: int, current_phase: int) -> float:
    """
    Advanced reward function with phase switch penalty
    Prevents excessive switching in congested conditions
    
    Args:
        junction_id: SUMO junction ID
        prev_phase: Previous traffic light phase
        current_phase: Current traffic light phase
        
    Returns:
        float: Advanced reward with stability bonus
    """
    # Get base reward
    base_reward = calculate_reward_balanced(junction_id)
    
    # Penalize phase switches (encourages stability)
    phase_switch_penalty = -10.0 if prev_phase != current_phase else 0.0
    
    return base_reward + phase_switch_penalty


# Legacy compatibility functions (for existing env.py)
def waiting_time_reward(traffic_signal) -> float:
    """Legacy function - delegates to calculate_reward_simple"""
    # Assuming traffic_signal has junction_id attribute
    if hasattr(traffic_signal, 'id'):
        return calculate_reward_simple(traffic_signal.id)
    return calculate_reward_simple('junction_1')


def combined_reward(traffic_signal, queue_weight: float = 0.5) -> float:
    """Legacy function - delegates to calculate_reward_balanced"""
    if hasattr(traffic_signal, 'id'):
        return calculate_reward_balanced(traffic_signal.id)
    return calculate_reward_balanced('junction_1')
