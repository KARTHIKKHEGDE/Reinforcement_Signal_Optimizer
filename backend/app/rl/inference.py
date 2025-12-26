"""
RL Model Inference
Load trained model and use for live simulation control
"""
from stable_baselines3 import PPO, DQN
import os
from app.config import settings
from app.sumo.traci_handler import traci_handler


class RLAgent:
    """RL Agent for traffic signal control"""
    
    def __init__(self, model_path: str = None, algorithm: str = "PPO"):
        self.model_path = model_path or settings.MODEL_PATH
        self.algorithm = algorithm.upper()
        self.model = None
        self.loaded = False
        
    def load_model(self) -> bool:
        """
        Load trained RL model
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            if not os.path.exists(self.model_path):
                print(f"Model not found at {self.model_path}")
                return False
            
            print(f"Loading {self.algorithm} model from {self.model_path}")
            
            if self.algorithm == "PPO":
                self.model = PPO.load(self.model_path)
            elif self.algorithm == "DQN":
                self.model = DQN.load(self.model_path)
            else:
                print(f"Unknown algorithm: {self.algorithm}")
                return False
            
            self.loaded = True
            print("Model loaded successfully")
            return True
            
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def predict_action(self, observation):
        """
        Predict action for given observation
        
        Args:
            observation: Current state observation
            
        Returns:
            Predicted action
        """
        if not self.loaded or self.model is None:
            print("Model not loaded")
            return None
        
        try:
            action, _states = self.model.predict(observation, deterministic=True)
            return action
            
        except Exception as e:
            print(f"Error predicting action: {e}")
            return None
    
    def get_observation_from_traci(self):
        """
        Get observation from current SUMO state via TraCI
        
        Returns:
            Observation array for RL model
        """
        if not traci_handler.connected:
            return None
        
        try:
            metrics = traci_handler.get_metrics()
            
            # Build observation (customize based on your state space)
            observation = [
                metrics["queue_length"],
                metrics["waiting_time"],
                metrics["vehicle_count"],
                # Add more state features as needed
            ]
            
            return observation
            
        except Exception as e:
            print(f"Error getting observation: {e}")
            return None
    
    def control_traffic_light(self, junction_id: str):
        """
        Control traffic light using RL agent
        
        Args:
            junction_id: Traffic light junction ID
            
        Returns:
            bool: True if action applied successfully
        """
        if not self.loaded:
            print("Model not loaded")
            return False
        
        try:
            # Get current observation
            observation = self.get_observation_from_traci()
            if observation is None:
                return False
            
            # Predict action
            action = self.predict_action(observation)
            if action is None:
                return False
            
            # Apply action to traffic light
            success = traci_handler.set_traffic_light_phase(junction_id, int(action))
            
            return success
            
        except Exception as e:
            print(f"Error controlling traffic light: {e}")
            return False


# Global RL agent instance
rl_agent = RLAgent()
