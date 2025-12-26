import asyncio
import traci
import time
from agents import TrafficLightAgent, EmergencyCoordinator
from traci.exceptions import FatalTraCIError

# Configuration for SPADE agents
AGENT_CREDENTIALS = {
    "n_0_0": ("tls_0_0@jabber.org", "password123"),
    "n_0_1": ("tls_0_1@jabber.org", "password123"),
    "n_1_0": ("tls_1_0@jabber.org", "password123"),
    "n_1_1": ("tls_1_1@jabber.org", "password123"),
    "n_2_0": ("tls_2_0@jabber.org", "password123"),
    "emergency": ("emergency@jabber.org", "password123")
}

class SimulationController:
    def __init__(self):
        self.agents = []
        self.sumo_process = None
        self.simulation_running = False

    async def wait_for_traci_connection(self, timeout=10):
        """Wait until a simple TraCI query succeeds or timeout."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                # Simple lightweight call to verify connection
                _ = traci.simulation.getMinExpectedNumber()
                return True
            except FatalTraCIError:
                await asyncio.sleep(0.5)
            except Exception:
                # other transient errors — retry
                await asyncio.sleep(0.5)
        return False

    async def start_simulation(self, use_gui=True, duration=3600):
        """Main simulation entry point"""
        try:
            print("Starting SUMO simulation...")
            
            # Start SUMO with appropriate binary
            sumo_binary = "sumo-gui" if use_gui else "sumo"
            sumo_cmd = [
                sumo_binary,
                "-c", "simulation.sumocfg",
                "--remote-port", "8813",
                "--num-clients", "1",
                "--start"  # Auto-start simulation
            ]
            
            print(f"SUMO command: {' '.join(sumo_cmd)}")
            traci.start(sumo_cmd)
            self.simulation_running = True
            
            # Wait for TraCI to be responsive
            connected = await self.wait_for_traci_connection(timeout=10)
            if not connected:
                print("Failed to establish TraCI connection within timeout")
                # ensure a safe close if partially connected
                try:
                    if traci.isLoaded():
                        traci.close()
                except Exception:
                    pass
                return

            print("SUMO started successfully!")
            
            # Wait a moment for SUMO to fully initialize
            await asyncio.sleep(1)
            
            # Initialize and start agents
            await self.start_agents()
            
            # Run main simulation loop
            await self.run_simulation_loop(duration)
            
        except Exception as e:
            print(f"Simulation error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            await self.cleanup()

    async def start_agents(self):
        """Initialize and start SPADE agents with fallback"""
        try:
            print("Starting SPADE agents...")
            
            # Get traffic light IDs from SUMO — guard against TraCI disconnect
            try:
                tls_ids = traci.trafficlight.getIDList()
            except FatalTraCIError as e:
                print(f"TraCI not connected when starting agents: {e}")
                return
            print(f"Found traffic lights: {tls_ids}")
            
            # Try to create and start traffic light agents
            for tls_id in tls_ids:
                try:
                    if tls_id in AGENT_CREDENTIALS:
                        jid, password = AGENT_CREDENTIALS[tls_id]
                        print(f"Creating agent for {tls_id} with JID {jid}")
                        
                        # Create agent with explicit keyword arguments
                        agent = TrafficLightAgent(jid=jid, password=password)
                        
                        # Try to start the agent (this might fail if no SPADE server)
                        await agent.start(auto_register=False)  # Don't auto-register to avoid server issues
                        
                        # Initialize SUMO data after agent is started
                        agent.initialize_sumo_data()
                        
                        self.agents.append(agent)
                        print(f"Started agent for {tls_id}")
                        
                        # Small delay between agent starts
                        await asyncio.sleep(0.1)
                    else:
                        # Fallback: Use simple controller
                        print(f"No credentials for {tls_id}, using simple controller")
                        from agents import SimpleTrafficController
                        controller = SimpleTrafficController(tls_id)
                        self.agents.append(controller)
                        
                except Exception as agent_error:
                    print(f"Failed to start SPADE agent for {tls_id}: {agent_error}")
                    print("Using simple traffic controller as fallback...")
                    from agents import SimpleTrafficController
                    controller = SimpleTrafficController(tls_id)
                    self.agents.append(controller)

            # Try to create emergency coordinator
            try:
                if "emergency" in AGENT_CREDENTIALS:
                    e_jid, e_password = AGENT_CREDENTIALS["emergency"]
                    emergency_agent = EmergencyCoordinator(jid=e_jid, password=e_password)
                    await emergency_agent.start(auto_register=False)
                    self.agents.append(emergency_agent)
                    print("Emergency coordinator started")
            except Exception as e:
                print(f"Emergency coordinator failed to start: {e}")

            print(f"Successfully started {len(self.agents)} controllers/agents")
            
        except Exception as e:
            print(f"Error starting agents: {str(e)}")
            import traceback
            traceback.print_exc()

    async def run_simulation_loop(self, duration):
        """Main simulation loop with proper timing"""
        try:
            print(f"Running simulation for {duration} seconds...")
            step = 0
            start_time = time.time()
            
            while step < duration and self.simulation_running:
                # Check TraCI connectivity and whether vehicles are expected
                try:
                    min_expected = traci.simulation.getMinExpectedNumber()
                except FatalTraCIError:
                    print("TraCI disconnected during simulation loop")
                    break
                except Exception as e:
                    # transient error, try next iteration
                    print(f"Transient TraCI error checking min expected vehicles: {e}")
                    await asyncio.sleep(0.1)
                    continue

                if min_expected <= 0:
                    print("No more expected vehicles, ending simulation")
                    break
                
                # Advance SUMO simulation by one step
                try:
                    traci.simulationStep()
                except FatalTraCIError:
                    print("TraCI disconnected on simulation step")
                    break

                step += 1
                
                # Run agent/controller logic
                for agent in self.agents:
                    try:
                        if hasattr(agent, 'adaptive_control'):  # Simple controller
                            agent.adaptive_control(step)
                        # SPADE agents run their own behaviors automatically
                    except Exception as e:
                        print(f"Error running controller: {e}")
                
                # Print progress every 300 steps (5 minutes simulation time)
                if step % 300 == 0:
                    try:
                        vehicle_count = len(traci.vehicle.getIDList())
                    except Exception:
                        vehicle_count = -1
                    elapsed_time = time.time() - start_time
                    print(f"Step {step}: {vehicle_count} vehicles, Real time: {elapsed_time:.1f}s")
                
                # Small delay to allow agent processing
                await asyncio.sleep(0.01)
                
            print(f"Simulation completed after {step} steps")
            
        except KeyboardInterrupt:
            print("\nSimulation interrupted by user")
        except Exception as e:
            print(f"Error in simulation loop: {str(e)}")
            import traceback
            traceback.print_exc()

    async def cleanup(self):
        """Clean up resources"""
        print("Cleaning up resources...")
        
        # Stop all agents first
        await self.stop_agents()
        
        # Close TraCI connection
        if traci.isLoaded():
            try:
                traci.close()
                print("TraCI connection closed")
            except Exception as e:
                print(f"Error closing TraCI: {e}")
        
        self.simulation_running = False

    async def stop_agents(self):
        """Stop all SPADE agents properly"""
        print("Stopping agents...")
        for agent in self.agents:
            try:
                if hasattr(agent, 'stop'):  # SPADE agent
                    await agent.stop()
                    print(f"Stopped agent: {agent.jid}")
                else:  # Simple controller
                    print(f"Stopped simple controller: {getattr(agent, 'tls_id', 'unknown')}")
            except Exception as e:
                print(f"Error stopping agent: {str(e)}")
        
        self.agents.clear()

    async def run_comparison_study(self):
        """Run comparison between adaptive and fixed-time control"""
        print("Running comparison study...")
        
        # Run with adaptive control
        print("\n--- Running with Adaptive Control ---")
        await self.start_simulation(use_gui=False, duration=1800)  # 30 minutes
        
        # Here you could implement a second run with fixed timing
        # For now, just the adaptive run
        print("Comparison study completed")

async def main():
    """Main function"""
    print("Advanced Adaptive Traffic Light Control System")
    print("=" * 50)
    
    controller = SimulationController()
    
    try:
        # Check if simulation files exist
        import os
        required_files = ['simulation.sumocfg', 'network.net.xml', 'routes.rou.xml']
        missing_files = [f for f in required_files if not os.path.exists(f)]
        
        if missing_files:
            print("Missing simulation files. Creating them...")
            # Import and use the NetworkGenerator from myels.py
            from myels import NetworkGenerator
            NetworkGenerator.create_network_xml()
            NetworkGenerator.create_routes_xml()
            NetworkGenerator.create_config_file()
            NetworkGenerator.create_gui_settings()
            print("Simulation files created successfully!")
        
        # Ask user for simulation type
        print("\nSimulation Options:")
        print("1. Run with GUI (interactive)")
        print("2. Run without GUI (faster)")
        print("3. Run comparison study")
        print("4. Use myels.py directly (recommended for testing)")
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == "1":
            await controller.start_simulation(use_gui=True)
        elif choice == "2":
            await controller.start_simulation(use_gui=False)
        elif choice == "3":
            await controller.run_comparison_study()
        elif choice == "4":
            print("Running myels.py directly...")
            from myels import main as myels_main
            myels_main()
        else:
            print("Invalid choice, running with GUI...")
            await controller.start_simulation(use_gui=True)
            
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Program ended")

if __name__ == "__main__":
    # Use asyncio to run the main function
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted")
    except Exception as e:
        print(f"Fatal error: {e}")