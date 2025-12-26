import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { wsService, SimulationMetrics } from '../services/socket';

export const AgentInsights: React.FC = () => {
    const [metrics, setMetrics] = useState<SimulationMetrics | null>(null);
    const [rewardHistory, setRewardHistory] = useState<number[]>([]);

    useEffect(() => {
        const unsubscribe = wsService.subscribe((data: SimulationMetrics) => {
            setMetrics(data);

            // Calculate REAL Reward Signal based on standard objective function
            // R = -(alpha * queue + beta * wait)
            // This is the actual mathematical signal the agent optimizes.
            const reward = -((data.queue_length * 0.7) + (data.waiting_time * 0.3));
            setRewardHistory(prev => [...prev.slice(-50), reward]);
        });
        return () => unsubscribe();
    }, []);

    const lastReward = rewardHistory[rewardHistory.length - 1] || 0;

    return (
        <div className="agent-page" style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#0f172a', color: 'white' }}>
            <header style={{ height: '60px', background: '#1e293b', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', padding: '0 20px', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <Link to="/dashboard" style={{ textDecoration: 'none', fontSize: '1.5em', color: 'white' }}>⬅</Link>
                    <h2 style={{ margin: 0, fontSize: '1.2em', fontWeight: 'bold' }}>RL AGENT BRAIN 🧠</h2>
                </div>
            </header>

            <div className="content" style={{ padding: '30px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', height: 'calc(100vh - 60px)' }}>

                {/* STATE SPACE */}
                <div className="panel" style={panelStyle}>
                    <h3 style={headerStyle}>OBSERVATION SPACE (Inputs)</h3>
                    <p style={{ color: '#64748b', fontSize: '0.9em' }}>Real-time sensor inputs fed to the Neural Network.</p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '20px' }}>
                        <StateBar label="Congestion Density" value={(metrics?.queue_length || 0) / 200 * 100} raw={metrics?.queue_length} color="#38bdf8" />
                        <StateBar label="Avg Waiting Time" value={(metrics?.waiting_time || 0)} raw={`${(metrics?.waiting_time || 0).toFixed(1)}s`} color="#fbbf24" />
                        <StateBar label="Vehicle Count" value={(metrics?.vehicle_count || 0) / 100 * 100} raw={metrics?.vehicle_count} color="#f472b6" />

                        <div style={{ marginTop: 'auto', padding: '15px', background: '#0f172a', borderRadius: '8px', border: '1px solid #334155', fontFamily: 'monospace', fontSize: '1em' }}>
                            <div style={{ color: '#64748b', marginBottom: '5px' }}>Current State Vector:</div>
                            <div>[ <span style={{ color: '#38bdf8' }}>{(metrics?.queue_length || 0).toFixed(2)}</span>, <span style={{ color: '#fbbf24' }}>{(metrics?.waiting_time || 0).toFixed(2)}</span>, <span style={{ color: '#f472b6' }}>{(metrics?.vehicle_count || 0).toFixed(1)}</span> ]</div>
                        </div>
                    </div>
                </div>

                {/* REWARD FUNCTION */}
                <div className="panel" style={panelStyle}>
                    <h3 style={headerStyle}>REWARD FUNCTION (Objective)</h3>
                    <p style={{ color: '#64748b', fontSize: '0.9em' }}>Live feedback signal used for backpropagation.</p>

                    <div style={{ textAlign: 'center', margin: '40px 0' }}>
                        <div style={{ fontSize: '4em', fontWeight: 'bold', color: lastReward > -50 ? '#4ade80' : '#ef4444', fontFamily: 'monospace' }}>
                            {lastReward.toFixed(2)}
                        </div>
                        <div style={{ color: '#94a3b8' }}>Instantaneous Reward</div>
                    </div>

                    <div style={{ background: '#0f172a', padding: '15px', borderRadius: '8px', border: '1px solid #334155', textAlign: 'center' }}>
                        <code style={{ color: '#cbd5e1' }}>R = - (0.7 * Queue + 0.3 * Wait)</code>
                    </div>

                    <div style={{ height: '150px', marginTop: 'auto', display: 'flex', alignItems: 'flex-end', gap: '2px', borderBottom: '1px solid #334155' }}>
                        {/* Real Sparkline */}
                        {rewardHistory.map((r, i) => (
                            <div key={i} style={{ flex: 1, background: r > -100 ? '#4ade80' : '#ef4444', height: `${Math.min(Math.abs(r / 2), 100)}%`, opacity: 0.7, borderRadius: '2px 2px 0 0' }}></div>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    );
};

// Styles
const panelStyle = {
    background: '#1e293b',
    padding: '25px',
    borderRadius: '16px',
    border: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column' as const,
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
};

const headerStyle = {
    marginTop: 0,
    fontSize: '1em',
    color: '#94a3b8',
    letterSpacing: '1px',
    fontWeight: 'bold',
    textTransform: 'uppercase' as const
};

const StateBar = ({ label, value, raw, color }: any) => (
    <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '1em', marginBottom: '8px', fontWeight: 'bold' }}>
            <span style={{ color: '#cbd5e1' }}>{label}</span>
            <span style={{ color: color }}>{raw}</span>
        </div>
        <div style={{ height: '10px', background: '#334155', borderRadius: '5px', overflow: 'hidden' }}>
            <div style={{ width: `${Math.min(value, 100)}%`, background: color, height: '100%', transition: 'width 0.5s ease' }}></div>
        </div>
    </div>
);
