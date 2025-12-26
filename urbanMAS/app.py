from flask import Flask, jsonify, render_template, send_file, request
from threading import Thread
import time
import logging

app = Flask(__name__)

latest_data = {}
simulation_paused = False
simulation_step = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/data')
def data():
    return jsonify(latest_data)

@app.route('/download_results')
def download_results():
    try:
        return send_file('simulation_results.json', as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/pause', methods=['POST'])
def pause():
    global simulation_paused
    simulation_paused = True
    return '', 204

@app.route('/resume', methods=['POST'])
def resume():
    global simulation_paused
    simulation_paused = False
    return '', 204

@app.route('/step', methods=['POST'])
def step():
    global simulation_step
    simulation_step = True
    return '', 204

@app.route('/map_data')
def map_data():
    # Example: return vehicle positions as lat/lon (replace with real data)
    # You must implement conversion from SUMO coordinates to lat/lon in your backend
    vehicles = latest_data.get('vehicles', [])
    return jsonify({'vehicles': vehicles})

def run_simulation():
    from myel import SUMOSimulationManager
    sim = None
    global simulation_paused, simulation_step
    try:
        sim = SUMOSimulationManager("map.sumocfg", gui=False)
        try:
            sim.setup_sumo()
        except Exception as e:
            logger.error(f"Aborting simulation: SUMO connection failed: {e}")
            return

        for step in range(3600):
            try:
                if simulation_paused:
                    if simulation_step:
                        simulation_step = False
                    else:
                        time.sleep(0.2)
                        continue
                sim.run_simulation(max_steps=1, analysis_interval=1)
                global latest_data
                if sim.metrics_history:
                    latest_data = sim.metrics_history[-1]
                    # Optionally add vehicle positions for map
                    latest_data['vehicles'] = []
                    try:
                        import traci
                        for veh_id in traci.vehicle.getIDList():
                            x, y = traci.vehicle.getPosition(veh_id)
                            # TODO: Convert (x, y) to (lat, lon) if you want true map overlay
                            latest_data['vehicles'].append({'id': veh_id, 'lat': y, 'lon': x})
                    except Exception:
                        pass
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Simulation error at step {step}: {e}")
                break

    finally:
        if sim:
            try:
                sim.cleanup()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

if __name__ == '__main__':
    sim_thread = Thread(target=run_simulation, daemon=True)
    sim_thread.start()
    app.run(debug=False, threaded=True, use_reloader=False)
