"""
Reward function definitions
Different reward strategies for RL training
"""


def waiting_time_reward(traffic_signal) -> float:
    """
    Reward based on waiting time minimization
    
    Args:
        traffic_signal: Traffic signal object
        
    Returns:
        Negative waiting time (to minimize)
    """
    waiting_time = sum(traffic_signal.get_lanes_waiting_time())
    return -waiting_time


def queue_length_reward(traffic_signal) -> float:
    """
    Reward based on queue length minimization
    
    Args:
        traffic_signal: Traffic signal object
        
    Returns:
        Negative queue length (to minimize)
    """
    queue_length = sum(traffic_signal.get_lanes_queue())
    return -queue_length


def combined_reward(traffic_signal, queue_weight: float = 10.0) -> float:
    """
    Combined reward function
    Balances waiting time and queue length
    
    Args:
        traffic_signal: Traffic signal object
        queue_weight: Weight for queue length penalty
        
    Returns:
        Combined reward value
    """
    waiting_time = sum(traffic_signal.get_lanes_waiting_time())
    queue_length = sum(traffic_signal.get_lanes_queue())
    
    # Weighted combination
    reward = -(waiting_time + queue_weight * queue_length)
    
    return reward


def throughput_reward(traffic_signal) -> float:
    """
    Reward based on vehicle throughput
    Maximizes number of vehicles passing through
    
    Args:
        traffic_signal: Traffic signal object
        
    Returns:
        Positive reward for throughput
    """
    # This would need access to arrived vehicles count
    # Placeholder implementation
    queue_length = sum(traffic_signal.get_lanes_queue())
    return -queue_length  # Inverse of queue as proxy for throughput
