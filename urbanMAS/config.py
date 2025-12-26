import os

# Adjust this path to your SUMO installation
SUMO_HOME = os.getenv('SUMO_HOME', 'C:\\Program Files (x86)\\Eclipse\\Sumo')

XMPP_SERVER = "localhost"
XMPP_PORT = 5222
AGENT_CREDENTIALS = {
    # Traffic Light Agents
    "n_0_0": ("tls7@xmpp.jp", "keerthi@2504"),
    "n_0_1": ("tls8@xmpp.jp", "keerthi@2504"),
    "n_0_2": ("tls9@xmpp.jp", "keerthi@2504"),
    "n_1_0": ("tls10@xmpp.jp", "keerthi@2504"),
    "n_1_1": ("tls11@xmpp.jp", "keerthi@2504"),
    "n_1_2": ("tls12@xmpp.jp", "keerthi@2504"),
    "n_2_0": ("tls13@xmpp.jp", "keerthi@2504"),
    "n_2_1": ("tls14@xmpp.jp", "keerthi@2504"),
    "n_2_2": ("tls15@xmpp.jp", "keerthi@2504"),
    
    # Emergency Coordinator (fixed comma)
    "emergency": ("emergencyresponse@xmpp.jp", "keerthimanne999000@")
}

SIMULATION_CONFIG = {
    'gui': True,
    'config_file': 'simulation.sumocfg',
    'simulation_time': 3600,
    'port': 8813
}
