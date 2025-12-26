import traci
import os

# Replace with your SUMO network file path
NETWORK_FILE = "network.net.xml"

# SUMO configuration
sumoBinary = "sumo-gui"  # or "sumo" for command-line
sumoCmd = [
    sumoBinary,
    "-n", NETWORK_FILE,  # Network file
    "--no-step-log",     # Disable step logging
    "--no-warnings",     # Disable warnings
]

# Connect to SUMO
traci.start(sumoCmd)
tls_ids = traci.trafficlight.getIDList()
print("Traffic Light IDs:", tls_ids)
print("Total Traffic Lights:", len(tls_ids))
traci.close()
