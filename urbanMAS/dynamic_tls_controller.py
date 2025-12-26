import traci
import time
import os

# Path to your SUMO config file
SUMO_CFG = "map.sumocfg"

# Path to SUMO-GUI executable, adjust if needed
SUMO_BINARY = "sumo-gui"

def main():
    # Start SUMO with TraCI
    sumo_cmd = [SUMO_BINARY, "-c", SUMO_CFG]
    traci.start(sumo_cmd)
    print("Simulation started.")

    # Get all traffic light IDs
    tls_ids = traci.trafficlight.getIDList()

    # Main simulation loop
    for step in range(1000):
        traci.simulationStep()
        # For each traffic light
        for tls_id in tls_ids:
            # Get all vehicles controlled by this traffic light
            controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
            vehicles = []
            for lane in controlled_lanes:
                vehicles += traci.lane.getLastStepVehicleIDs(lane)
            # Check for emergency vehicles
            emergency_found = False
            for veh_id in vehicles:
                if traci.vehicle.getTypeID(veh_id) == "emergency":
                    emergency_found = True
                    break
            # If emergency vehicle found, set phase 0 (usually green for main direction)
            if emergency_found:
                print(f"Step {step}: Emergency detected at {tls_id}. Setting phase 0 (green).")
                traci.trafficlight.setPhase(tls_id, 0)
            else:
                # Otherwise, cycle through phases every 30 steps
                phase_count = len(traci.trafficlight.getAllProgramLogics(tls_id)[0].phases)
                current_phase = traci.trafficlight.getPhase(tls_id)
                if step % 30 == 0:
                    next_phase = (current_phase + 1) % phase_count
                    print(f"Step {step}: Cycling {tls_id} to phase {next_phase}.")
                    traci.trafficlight.setPhase(tls_id, next_phase)
        time.sleep(0.05)  # Slow down the sim for visibility

    traci.close()
    print("Simulation finished.")

if __name__ == "__main__":
    # Make sure SUMO_HOME/tools is on your PYTHONPATH if needed
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        import sys
        if tools not in sys.path:
            sys.path.append(tools)
    main()
