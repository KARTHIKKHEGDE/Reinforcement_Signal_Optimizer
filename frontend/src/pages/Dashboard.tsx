import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { DigitalTwin } from '../components/DigitalTwin';
import { wsService, SimulationMetrics } from '../services/socket';
import { stopSimulation, resetSimulation, getSimulationStatus } from '../services/api';

interface DashboardProps { }

export const Dashboard: React.FC<DashboardProps> = () => {
    const navigate = useNavigate();
    const [isRunning, setIsRunning] = useState(false);
    const [currentMode, setCurrentMode] = useState<'fixed' | 'rl'>('fixed');
    const [currentMetrics, setCurrentMetrics] = useState<SimulationMetrics | null>(null);
    const [loading, setLoading] = useState(false);

    // Initial check
    useEffect(() => {
        const init = async () => {
            try {
                const status = await getSimulationStatus();
                setIsRunning(status.running);
                if (status.running) {
                    wsService.connect();
                    // We assume mode is whatever was started. 
                    // Ideally API returns current mode, but for now we default to ui state or generic.
                }
            } catch (e) { console.error(e); }
        };
        init();

        const unsubscribe = wsService.subscribe((metrics: SimulationMetrics) => {
            setCurrentMetrics(metrics);

            // SAVE HISTORY FOR REAL CHARTS (Comparison Page)
            const history = JSON.parse(localStorage.getItem('simulationHistory') || '[]');
            history.push({
                time: metrics.time,
                queue: metrics.queue_length,
                wait: metrics.waiting_time,
                vehicles: metrics.vehicle_count
            });
            // Keep last 100 points to avoid storage overflow
            if (history.length > 100) history.shift();
            localStorage.setItem('simulationHistory', JSON.stringify(history));

            // Save Snapshot for Results
            localStorage.setItem('lastRunMetrics', JSON.stringify(metrics));
        });
        return () => unsubscribe();
    }, []);

    const handleStop = async () => {
        setLoading(true);
        await stopSimulation();
        setIsRunning(false);
        wsService.disconnect();
        setLoading(false);
        // Clear history on stop or keep? Let's keep for analysis until reset.
    };

    const handleReset = async () => {
        setLoading(true);
        await resetSimulation();
        setIsRunning(false);
        setCurrentMetrics(null);
        wsService.disconnect();
        localStorage.removeItem('simulationHistory'); // Clear history on reset
        localStorage.removeItem('lastRunMetrics');
        setLoading(false);
        navigate('/junctions');
    };

    const handleSwitchMode = async () => {
        const newMode = currentMode === 'fixed' ? 'rl' : 'fixed';
        setCurrentMode(newMode);

        // If running, we stop and ask user to restart for cleanliness
        if (isRunning) {
            await handleStop();
            alert(`Mode switched to ${newMode.toUpperCase()}. Please restart simulation to apply logic change.`);
            navigate('/junctions');
        }
    };

    return (
        <div className="dashboard-container" style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#0f172a', color: 'white', overflow: 'hidden' }}>

            {/* 🔴 Top Status Bar */}
            <header style={{ height: '60px', background: '#1e293b', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', padding: '0 20px', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <h2 style={{ margin: 0, fontSize: '1.2em', fontWeight: 'bold', letterSpacing: '1px' }}>
                        🚦 TRAFFIC CONTROL CENTER
                    </h2>
                    <div className="status-badge" style={{ padding: '4px 12px', borderRadius: '12px', background: isRunning ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)', color: isRunning ? '#22c55e' : '#ef4444', border: isRunning ? '1px solid #22c55e' : '1px solid #ef4444', fontSize: '0.85em', fontWeight: 'bold' }}>
                        {isRunning ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '20px', fontSize: '0.9em' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ color: '#64748b' }}>MODE:</span>
                        <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>{currentMode === 'fixed' ? 'FIXED-TIME' : 'RL-AGENT (AI)'}</span>
                    </div>
                    {currentMetrics && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: '#64748b' }}>SIM TIME:</span>
                            <span style={{ color: 'white', fontWeight: 'bold', fontFamily: 'monospace' }}>{Math.round(currentMetrics.time)}s</span>
                        </div>
                    )}
                </div>

                <nav style={{ display: 'flex', gap: '15px' }}>
                    <Link to="/comparison" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.9em', padding: '5px 10px', borderRadius: '4px', background: 'rgba(255,255,255,0.05)' }}>Analysis</Link>
                    <Link to="/agent" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.9em', padding: '5px 10px', borderRadius: '4px', background: 'rgba(255,255,255,0.05)' }}>Agent View</Link>
                    <Link to="/results" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.9em', padding: '5px 10px', borderRadius: '4px', background: 'rgba(255,255,255,0.05)' }}>Results</Link>
                </nav>
            </header>

            {/* 🧩 Split Screen Layout */}
            <div className="main-content" style={{ flex: 1, display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1px', background: '#334155', overflow: 'hidden' }}>

                {/* LEFT SIDE: Visuals */}
                <div className="visual-panel" style={{ background: '#0f172a', position: 'relative', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ position: 'absolute', top: '20px', left: '20px', right: '20px', zIndex: 10, display: 'flex', justifyContent: 'space-between', pointerEvents: 'none' }}>
                        <div style={{ background: 'rgba(0,0,0,0.7)', padding: '5px 10px', borderRadius: '6px', pointerEvents: 'auto' }}>
                            <h3 style={{ margin: 0, fontSize: '0.8em', color: '#94a3b8' }}>LIVE FEED</h3>
                        </div>
                    </div>

                    {/* Digital Twin Container */}
                    <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
                        <DigitalTwin
                            queueLength={currentMetrics?.queue_length || 0}
                            vehicleCount={currentMetrics?.vehicle_count || 0}
                            trafficLights={currentMetrics?.traffic_lights || {}}
                            locationId={localStorage.getItem('lastLocation') || 'silk_board'}
                        />
                    </div>
                </div>

                {/* RIGHT SIDE: Metrics & Controls */}
                <div className="metrics-panel" style={{ background: '#1e293b', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px', borderLeft: '1px solid #334155', overflowY: 'auto' }}>

                    {/* Metric Cards */}
                    <div className="metric-group">
                        <h3 style={{ fontSize: '0.8em', color: '#64748b', marginBottom: '10px', textTransform: 'uppercase' }}>Real-time Metrics</h3>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                            <MetricCard
                                label="Active Vehicles"
                                value={currentMetrics?.vehicle_count || 0}
                                icon="🚗"
                                color="#38bdf8"
                            />
                            <MetricCard
                                label="Avg Wait Time"
                                value={`${(currentMetrics?.waiting_time || 0).toFixed(1)}s`}
                                icon="⏱️"
                                color={(currentMetrics?.waiting_time || 0) > 60 ? '#ef4444' : '#4ade80'}
                            />
                            <MetricCard
                                label="Queue Length"
                                value={currentMetrics?.queue_length || 0}
                                icon="📏"
                                color="#f472b6"
                            />
                            <MetricCard
                                label="Throughput"
                                value={`${currentMetrics?.arrived_vehicles || 0}`}
                                icon="✅"
                                suffix="veh"
                                color="#fbbf24"
                            />
                        </div>
                    </div>

                    {/* Performance Bar */}
                    <div style={{ background: '#0f172a', borderRadius: '12px', padding: '15px', border: '1px solid #334155' }}>
                        <h3 style={{ fontSize: '0.8em', color: '#64748b', marginBottom: '15px', textTransform: 'uppercase' }}>Congestion Level</h3>
                        {/* Simple congestion bar */}
                        <div style={{ marginBottom: '5px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8em', marginBottom: '8px', color: '#cbd5e1' }}>
                                <span>Current Load</span>
                                <span>{(currentMetrics?.vehicle_count || 0) > 400 ? 'HEAVY' : 'MODERATE'}</span>
                            </div>
                            <div style={{ height: '8px', background: '#334155', borderRadius: '4px', overflow: 'hidden' }}>
                                <div style={{
                                    height: '100%',
                                    width: `${Math.min(((currentMetrics?.vehicle_count || 0) / 1000) * 100, 100)}%`,
                                    background: 'linear-gradient(90deg, #38bdf8, #818cf8)',
                                    transition: 'width 0.5s'
                                }}></div>
                            </div>
                        </div>
                    </div>

                    {/* Agent Status (Mini) */}
                    <div style={{ background: '#0f172a', borderRadius: '12px', padding: '15px', border: '1px solid #334155' }}>
                        <h3 style={{ fontSize: '0.8em', color: '#64748b', marginBottom: '10px', textTransform: 'uppercase' }}>Agent Status</h3>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9em' }}>
                            <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: currentMode === 'rl' ? '#22c55e' : '#64748b' }}></div>
                            <span style={{ color: currentMode === 'rl' ? '#22c55e' : '#64748b' }}>
                                {currentMode === 'rl' ? 'Optimizing Signal Phases...' : 'Fixed Timer Active'}
                            </span>
                        </div>
                    </div>

                    {/* 🟢 Controls */}
                    <div className="controls-area" style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                            {!isRunning ? (
                                <button onClick={() => navigate('/junctions')} style={btnStyle('#22c55e')}>▶ START</button>
                            ) : (
                                <button onClick={handleStop} style={btnStyle('#ef4444')}>⏹ STOP</button>
                            )}
                            <button onClick={handleReset} style={btnStyle('#475569')}>🔄 RESET</button>
                        </div>
                        <button
                            onClick={handleSwitchMode}
                            style={btnStyle('#6366f1')}
                        >
                            ⚡ SWITCH CONTROLLER ({currentMode === 'fixed' ? 'TO RL' : 'TO FIXED'})
                        </button>
                    </div>

                </div>
            </div>
        </div>
    );
};

// Helper Components & Styles
const MetricCard = ({ label, value, icon, color, suffix }: any) => (
    <div style={{ background: '#0f172a', padding: '15px', borderRadius: '12px', border: '1px solid #334155', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', background: color }}></div>
        <div style={{ fontSize: '1.5em', marginBottom: '5px' }}>{icon}</div>
        <div style={{ fontSize: '1.4em', fontWeight: 'bold', color: 'white' }}>{value} <span style={{ fontSize: '0.6em', color: '#64748b' }}>{suffix}</span></div>
        <div style={{ fontSize: '0.75em', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</div>
    </div>
);

const btnStyle = (color: string) => ({
    padding: '14px',
    background: color,
    border: 'none',
    borderRadius: '8px',
    color: 'white',
    fontWeight: 'bold',
    fontSize: '0.9em',
    cursor: 'pointer',
    opacity: 1,
    transition: 'opacity 0.2s',
    boxShadow: '0 4px 6px rgba(0,0,0,0.2)'
} as React.CSSProperties);
