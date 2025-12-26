"""
Configuration management using pydantic-settings
Loads environment variables from .env file
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # SUMO Configuration
    SUMO_HOME: str = "C:/Program Files (x86)/Eclipse/Sumo"
    SUMO_BINARY: str = "sumo"
    SUMO_GUI_BINARY: str = "sumo-gui"
    
    # Simulation Parameters
    SIMULATION_TIME: int = 3600
    STEP_LENGTH: float = 1.0
    YELLOW_TIME: int = 3
    MIN_GREEN: int = 5
    MAX_GREEN: int = 60
    
    # RL Configuration
    RL_ALGO: str = "PPO"
    MODEL_PATH: str = "models/ppo_model.zip"
    TRAINING_TIMESTEPS: int = 100000
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    # WebSocket Configuration
    WS_UPDATE_INTERVAL: float = 1.0
    
    # Network Files
    NETWORK_FILE: str = "app/sumo/network/network.net.xml"
    ROUTE_FILE: str = "app/sumo/network/routes.rou.xml"
    CONFIG_FILE: str = "app/sumo/network/simulation.sumocfg"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# Global settings instance
settings = Settings()
