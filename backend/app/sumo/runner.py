"""
SUMO Process Controller
Manages starting, stopping, and monitoring SUMO simulation
"""
import subprocess
import os
import sys
import time
from typing import Optional
from app.config import settings
from app.sumo.traci_handler import traci_handler


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
            
            # Verify critical files exist before starting
            if not os.path.exists(settings.CONFIG_FILE):
                raise Exception(f"Config file not found: {settings.CONFIG_FILE}")
            
            print(f"✓ Config file exists: {settings.CONFIG_FILE}")
            
            # Parse config to verify network and route files exist
            import xml.etree.ElementTree as ET
            try:
                tree = ET.parse(settings.CONFIG_FILE)
                root = tree.getroot()
                
                # Find input section
                input_node = root.find("input")
                if input_node is not None:
                    net_node = input_node.find("net-file")
                    routes_node = input_node.find("route-files")
                    
                    if net_node is not None:
                        net_file = net_node.get("value")
                        net_path = os.path.join(os.path.dirname(settings.CONFIG_FILE), net_file)
                        if not os.path.exists(net_path):
                            raise Exception(f"Network file not found: {net_path}")
                        print(f"✓ Network file exists: {net_file}")
                    
                    if routes_node is not None:
                        route_file = routes_node.get("value")
                        route_path = os.path.join(os.path.dirname(settings.CONFIG_FILE), route_file)
                        if not os.path.exists(route_path):
                            raise Exception(f"Route file not found: {route_path}")
                        print(f"✓ Route file exists: {route_file}")
            except Exception as e:
                print(f"⚠️ Warning: Could not verify config files: {e}")
            
            # Import traci here to avoid issues
            import traci
            
            # CRITICAL: Force complete cleanup before starting
            print("🔍 Checking for stale connections...")
            
            # Force handler disconnect if still marked as connected
            if traci_handler.connected:
                print("⚠️ Handler still connected, forcing disconnect...")
                traci_handler.disconnect()
                time.sleep(0.5)
            
            # Check if there's an existing TraCI connection and close it
            try:
                if traci.isLoaded():
                    print("⚠️ Found active TraCI connection, closing it...")
                    traci.close()
                    time.sleep(1.0)  # Longer wait for clean shutdown
            except Exception as e:
                print(f"Note: TraCI cleanup attempt: {e}")
            
            # Final check - ensure really closed
            try:
                if traci.isLoaded():
                    print("❌ TraCI still loaded! Force closing...")
                    # Kill any stuck SUMO processes
                    os.system('taskkill /F /IM sumo.exe 2>nul')
                    os.system('taskkill /F /IM sumo-gui.exe 2>nul')
                    time.sleep(1.0)
            except Exception:
                pass
            
            # Start SUMO with TraCI
            try:
                print(f"🚀 Starting SUMO with TraCI...")
                print(f"   Command: {' '.join(sumo_cmd)}")
                
                traci.start(sumo_cmd)
                print("   TraCI.start() command executed")
                
                # Give SUMO time to start up
                time.sleep(2.0)
                
                # Verify connection
                if not traci.isLoaded():
                    raise Exception("TraCI.start() succeeded but connection not loaded!")
                
                print("   ✓ TraCI connection verified")
                
                # Check if SUMO loaded successfully
                print(f"✅ SUMO connected! Checking initial state...")
                loaded = traci.simulation.getLoadedNumber()
                departed = traci.simulation.getDepartedNumber()
                sim_time = traci.simulation.getTime()
                
                print(f"   - Loaded vehicles waiting: {loaded}")
                print(f"   - Departed vehicles: {departed}")
                print(f"   - Simulation time: {sim_time}")
                
            except traci.exceptions.TraCIException as e:
                error_msg = str(e)
                print(f"❌ TraCI Exception: {error_msg}")
                
                # Check if it's a connection refused error
                if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                    print("💡 SUMO started but TraCI server didn't initialize properly")
                    print("   This usually means SUMO crashed due to a config error")
                    print("   Check if route file has vehicles and network file is valid")
                    
                    # Try to read SUMO output
                    try:
                        # Kill any stuck SUMO processes
                        os.system('taskkill /F /IM sumo.exe 2>nul')
                        os.system('taskkill /F /IM sumo-gui.exe 2>nul')
                    except Exception:
                        pass
                    
                    raise Exception(f"SUMO crashed on startup - likely config/route error: {error_msg}")
                
                if "already active" in error_msg or "already connected" in error_msg:
                    print("🔄 Attempting recovery from stuck connection...")
                    try:
                        # Force close
                        traci.close()
                        time.sleep(1.0)
                        
                        # Kill processes
                        os.system('taskkill /F /IM sumo.exe 2>nul')
                        os.system('taskkill /F /IM sumo-gui.exe 2>nul')
                        time.sleep(1.0)
                        
                        # Retry start
                        print("🔄 Retrying SUMO start...")
                        traci.start(sumo_cmd)
                        time.sleep(2.0)
                        print("✅ Recovery successful!")
                    except Exception as inner_e:
                        print(f"❌ Recovery failed: {inner_e}")
                        raise Exception(f"Failed to start SUMO after recovery attempt: {inner_e}")
                else:
                    raise Exception(f"Failed to start SUMO: {error_msg}")
            
            # ⚡ Initialize TraCI handler with fresh state
            print("🔧 Initializing TraCI handler...")
            traci_handler.connected = True
            traci_handler.junction_ids = list(traci.trafficlight.getIDList())
            traci_handler.lane_ids = list(traci.lane.getIDList())
            traci_handler.total_departed = 0
            traci_handler.total_arrived = 0
            
            print(f"   ✓ Traffic lights: {len(traci_handler.junction_ids)}")
            print(f"   ✓ Lanes: {len(traci_handler.lane_ids)}")
            print(f"   ✓ Handler connected: {traci_handler.connected}")
            
            self.is_running = True
            self.process = None  # traci manages the process
            print("✅ SUMO started successfully with TraCI")
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
            return True  # Return True since it's already stopped
        
        try:
            import traci
            print("🛑 Stopping SUMO...")
            
            # Try to close TraCI gracefully
            if traci.isLoaded():
                print("   Closing TraCI connection...")
                traci.close()
                time.sleep(0.5)  # Give SUMO time to shutdown
            
            # Force kill any remaining SUMO processes
            print("   Cleaning up SUMO processes...")
            os.system('taskkill /F /IM sumo.exe 2>nul')
            os.system('taskkill /F /IM sumo-gui.exe 2>nul')
            time.sleep(0.3)
            
            # Reset state
            self.is_running = False
            self.process = None
            
            # Ensure TraCI handler is also disconnected
            print("   Resetting TraCI handler state...")
            traci_handler.connected = False
            traci_handler.junction_ids = []
            traci_handler.lane_ids = []
            
            print("✅ SUMO stopped successfully - Ready for new simulation")
            return True
            
        except Exception as e:
            print(f"⚠️ Error stopping SUMO: {e}")
            import traceback
            traceback.print_exc()
            
            # Force mark as stopped even if error
            self.is_running = False
            self.process = None
            traci_handler.connected = False
            return True
    
    def get_status(self) -> dict:
        """Get current SUMO status"""
        return {
            "running": self.is_running,
            "pid": self.process.pid if self.process else None
        }


# Global SUMO runner instance
sumo_runner = SUMORunner()
