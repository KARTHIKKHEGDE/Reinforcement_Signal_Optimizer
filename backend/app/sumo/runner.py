"""
SUMO Process Controller
Manages starting, stopping, and monitoring SUMO simulation
"""
import subprocess
import os
import sys
from typing import Optional
from app.config import settings


class SUMORunner:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        
    def start(self, use_gui: bool = False) -> bool:
        """
        Start SUMO simulation
        
        Args:
            use_gui: Whether to use SUMO GUI or headless mode
            
        Returns:
            bool: True if started successfully
        """
        if self.is_running:
            print("SUMO is already running")
            return False
        
        try:
            # Set SUMO_HOME environment variable
            os.environ['SUMO_HOME'] = settings.SUMO_HOME
            
            # Choose binary
            binary = settings.SUMO_GUI_BINARY if use_gui else settings.SUMO_BINARY
            sumo_binary = os.path.join(settings.SUMO_HOME, 'bin', binary)
            
            # Build command - use list format for traci.start()
            sumo_cmd = [
                sumo_binary,
                "-c", settings.CONFIG_FILE,
                "--step-length", str(settings.STEP_LENGTH),
                "--no-warnings",
                "--duration-log.disable",
                "--no-step-log"
            ]
            
            if not use_gui:
                sumo_cmd.append("--quit-on-end")
            
            print(f"Starting SUMO with command: {' '.join(sumo_cmd)}")
            
            # Import traci here to avoid issues
            import traci
            
            # Check if there's an existing connection and close it
            try:
                if traci.isLoaded():
                    print("Found active TraCI connection, closing it...")
                    traci.close()
            except Exception:
                pass  # Ignore errors if connection is already broken
            
            # Start SUMO with TraCI
            try:
                traci.start(sumo_cmd)
            except traci.exceptions.TraCIException as e:
                if "is already active" in str(e):
                    # If somehow still active, try to use it or force close again
                    print("TraCI connection active, retrying clean start...")
                    try:
                        traci.close()
                        traci.start(sumo_cmd)
                    except Exception as inner_e:
                        print(f"Failed to recover TraCI: {inner_e}")
                        raise e
                else:
                    raise e
            
            self.is_running = True
            self.process = None  # traci manages the process
            print("SUMO started successfully with TraCI")
            return True
            
        except Exception as e:
            print(f"Error starting SUMO: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop(self) -> bool:
        """
        Stop SUMO simulation
        
        Returns:
            bool: True if stopped successfully
        """
        if not self.is_running:
            print("SUMO is not running")
            return False
        
        try:
            import traci
            traci.close()
            self.is_running = False
            print("SUMO stopped successfully")
            return True
            
        except Exception as e:
            print(f"Error stopping SUMO: {e}")
            self.is_running = False
            return True
    
    def get_status(self) -> dict:
        """Get current SUMO status"""
        return {
            "running": self.is_running,
            "pid": self.process.pid if self.process else None
        }


# Global SUMO runner instance
sumo_runner = SUMORunner()
