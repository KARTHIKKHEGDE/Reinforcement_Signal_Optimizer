/**
 * Dashboard Page
 * Main control interface for traffic simulation
 */
import React, { useState, useEffect } from 'react';
import { Charts } from '../components/Charts';
import { SignalState } from '../components/SignalState';
import { TrafficMap } from '../components/TrafficMap';
import { wsService, SimulationMetrics } from '../services/socket';
import { startSimulation, stopSimulation, resetSimulation, getSimulationStatus } from '../services/api';

interface ChartData {
    time: number;
    queue_length: number;
    waiting_time: number;
    vehicle_count: number;
}

export const Dashboard: React.FC = () => {
    const [isRunning, setIsRunning] = useState(false);
    const [currentMode, setCurrentMode] = useState<'fixed' | 'rl'>('fixed');
    const [trafficScenario, setTrafficScenario] = useState<'peak' | 'offpeak'>('peak');
    const [useGui, setUseGui] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [currentMetrics, setCurrentMetrics] = useState<SimulationMetrics | null>(null);
    const [chartData, setChartData] = useState<ChartData[]>([]);
    const [maxDataPoints] = useState(100); // Keep last 100 data points

    // Check initial status
    useEffect(() => {
        checkStatus();
    }, []);

    // Subscribe to WebSocket updates
    useEffect(() => {
        const unsubscribe = wsService.subscribe((metrics: SimulationMetrics) => {
            setCurrentMetrics(metrics);

            // Add to chart data
            setChartData(prev => {
                const newData = [
                    ...prev,
                    {
                        time: Math.round(metrics.time),
                        queue_length: metrics.queue_length,
                        waiting_time: Math.round(metrics.waiting_time * 100) / 100,
                        vehicle_count: metrics.vehicle_count,
                    },
                ];

                // Keep only last N data points
                return newData.slice(-maxDataPoints);
            });
        });

        return () => {
            unsubscribe();
        };
    }, [maxDataPoints]);

    const checkStatus = async () => {
        try {
            const status = await getSimulationStatus();
            setIsRunning(status.running);

            if (status.running) {
                wsService.connect();
            }
        } catch (err) {
            console.error('Error checking status:', err);
        }
    };

    const handleStart = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await startSimulation(currentMode, useGui, trafficScenario);
            console.log('Simulation started:', response);

            setIsRunning(true);
            setChartData([]); // Clear previous data

            // Connect WebSocket
            wsService.connect();

        } catch (err: any) {
            console.error('Error starting simulation:', err);
            setError(err.response?.data?.detail || 'Failed to start simulation');
        } finally {
            setLoading(false);
        }
    };

    const handleStop = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await stopSimulation();
            console.log('Simulation stopped:', response);

            setIsRunning(false);

            // Disconnect WebSocket
            wsService.disconnect();

        } catch (err: any) {
            console.error('Error stopping simulation:', err);
            setError(err.response?.data?.detail || 'Failed to stop simulation');
        } finally {
            setLoading(false);
        }
    };

    const handleReset = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await resetSimulation();
            console.log('Simulation reset:', response);

            setIsRunning(false);
            setChartData([]);
            setCurrentMetrics(null);

            // Disconnect WebSocket
            wsService.disconnect();

        } catch (err: any) {
            console.error('Error resetting simulation:', err);
            setError(err.response?.data?.detail || 'Failed to reset simulation');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <h1>🚦 Smart Traffic Signal Optimizer</h1>
                <p className="subtitle">Real-time Traffic Control using Reinforcement Learning</p>
            </header>

            {/* Control Panel */}
            <div className="control-panel">
                <div className="control-section">
                    <h3>Simulation Control</h3>

                    <div className="control-group">
                        <label>Control Mode:</label>
                        <div className="mode-selector">
                            <button
                                className={`mode-btn ${currentMode === 'fixed' ? 'active' : ''}`}
                                onClick={() => setCurrentMode('fixed')}
                                disabled={isRunning}
                            >
                                Fixed-Time
                            </button>
                            <button
                                className={`mode-btn ${currentMode === 'rl' ? 'active' : ''}`}
                                onClick={() => setCurrentMode('rl')}
                                disabled={isRunning}
                            >
                                RL Agent
                            </button>
                        </div>
                    </div>

                    <div className="control-group">
                        <label>Traffic Scenario:</label>
                        <div className="mode-selector">
                            <button
                                className={`mode-btn ${trafficScenario === 'peak' ? 'active' : ''}`}
                                onClick={() => setTrafficScenario('peak')}
                                disabled={isRunning}
                            >
                                🚗 Peak Hour
                            </button>
                            <button
                                className={`mode-btn ${trafficScenario === 'offpeak' ? 'active' : ''}`}
                                onClick={() => setTrafficScenario('offpeak')}
                                disabled={isRunning}
                            >
                                🌤️ Off-Peak
                            </button>
                        </div>
                        <small style={{ color: '#888', marginTop: '5px', display: 'block' }}>
                            {trafficScenario === 'peak'
                                ? '520 veh/h • Severe Congestion • Avg 11 km/h'
                                : '200 veh/h • Moderate Flow • Avg 28 km/h'
                            }
                        </small>
                    </div>

                    <div className="control-group">
                        <label className="checkbox-label">
                            <input
                                type="checkbox"
                                checked={useGui}
                                onChange={(e) => setUseGui(e.target.checked)}
                                disabled={isRunning}
                            />
                            <span>Show SUMO GUI</span>
                        </label>
                    </div>

                    <div className="action-buttons">
                        {!isRunning ? (
                            <button
                                className="btn btn-start"
                                onClick={handleStart}
                                disabled={loading}
                            >
                                {loading ? 'Starting...' : '▶ Start Simulation'}
                            </button>
                        ) : (
                            <button
                                className="btn btn-stop"
                                onClick={handleStop}
                                disabled={loading}
                            >
                                {loading ? 'Stopping...' : '⏹ Stop Simulation'}
                            </button>
                        )}

                        <button
                            className="btn btn-reset"
                            onClick={handleReset}
                            disabled={loading}
                        >
                            {loading ? 'Resetting...' : '🔄 Reset'}
                        </button>
                    </div>

                    {error && (
                        <div className="error-message">
                            ⚠️ {error}
                        </div>
                    )}
                </div>

                {/* Status Display */}
                <div className="status-section">
                    <h3>Status</h3>
                    <div className="status-grid">
                        <div className="status-item">
                            <span className="status-label">Simulation:</span>
                            <span className={`status-badge ${isRunning ? 'running' : 'stopped'}`}>
                                {isRunning ? '🟢 Running' : '🔴 Stopped'}
                            </span>
                        </div>
                        <div className="status-item">
                            <span className="status-label">Mode:</span>
                            <span className="status-value">{currentMode === 'fixed' ? 'Fixed-Time' : 'RL Agent'}</span>
                        </div>
                        {currentMetrics && (
                            <>
                                <div className="status-item">
                                    <span className="status-label">Sim Time:</span>
                                    <span className="status-value">{Math.round(currentMetrics.time)}s</span>
                                </div>
                                <div className="status-item">
                                    <span className="status-label">Vehicles:</span>
                                    <span className="status-value">{currentMetrics.vehicle_count}</span>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* Metrics Display */}
            {currentMetrics && (
                <div className="metrics-panel">
                    <div className="metric-card">
                        <div className="metric-icon">📊</div>
                        <div className="metric-content">
                            <div className="metric-label">Queue Length</div>
                            <div className="metric-value">{currentMetrics.queue_length}</div>
                        </div>
                    </div>

                    <div className="metric-card">
                        <div className="metric-icon">⏱️</div>
                        <div className="metric-content">
                            <div className="metric-label">Avg Waiting Time</div>
                            <div className="metric-value">{currentMetrics.waiting_time.toFixed(2)}s</div>
                        </div>
                    </div>

                    <div className="metric-card">
                        <div className="metric-icon">🚗</div>
                        <div className="metric-content">
                            <div className="metric-label">Active Vehicles</div>
                            <div className="metric-value">{currentMetrics.vehicle_count}</div>
                        </div>
                    </div>

                    <div className="metric-card">
                        <div className="metric-icon">✅</div>
                        <div className="metric-content">
                            <div className="metric-label">Arrived</div>
                            <div className="metric-value">{currentMetrics.arrived_vehicles}</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Content Grid */}
            <div className="content-grid">
                <div className="grid-item">
                    <TrafficMap
                        queueLength={currentMetrics?.queue_length || 0}
                        vehicleCount={currentMetrics?.vehicle_count || 0}
                    />
                </div>

                <div className="grid-item">
                    <SignalState
                        trafficLights={currentMetrics?.traffic_lights || {}}
                    />
                </div>
            </div>

            {/* Charts */}
            {chartData.length > 0 && (
                <div className="charts-section">
                    <Charts data={chartData} />
                </div>
            )}

            {!isRunning && chartData.length === 0 && (
                <div className="empty-state">
                    <div className="empty-icon">🚦</div>
                    <h2>No Active Simulation</h2>
                    <p>Start a simulation to see real-time traffic metrics and visualizations</p>
                </div>
            )}
        </div>
    );
};
