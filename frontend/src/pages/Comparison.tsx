import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export const Comparison: React.FC = () => {
    const [data, setData] = useState<any[]>([]);

    useEffect(() => {
        // LOAD REAL DATA FROM LOCAL STORAGE
        const history = JSON.parse(localStorage.getItem('simulationHistory') || '[]');

        // Add a "Baseline" reference line for comparison (e.g., standard fixed time delay ~90s)
        const enrichedData = history.map((point: any) => ({
            ...point,
            baseline: 96.5 // Constant baseline reference
        }));

        setData(enrichedData);
    }, []);

    // Helper: Calculate average from history
    const avg = (key: string) => {
        if (data.length === 0) return 0;
        return (data.reduce((sum, item) => sum + (item[key] || 0), 0) / data.length).toFixed(1);
    };

    return (
        <div className="comparison-page" style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#0f172a', color: 'white' }}>
            {/* Header */}
            <header style={{ height: '60px', background: '#1e293b', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', padding: '0 20px', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <Link to="/dashboard" style={{ textDecoration: 'none', fontSize: '1.5em', color: 'white' }}>⬅</Link>
                    <h2 style={{ margin: 0, fontSize: '1.2em', fontWeight: 'bold' }}>LIVE PERFORMANCE ANALYSIS</h2>
                </div>
            </header>

            <div className="content" style={{ padding: '30px', overflowY: 'auto' }}>
                {data.length === 0 ? (
                    <div style={{ textAlign: 'center', marginTop: '50px', color: '#94a3b8' }}>
                        <h2>No Data Yet</h2>
                        <p>Run the simulation to gather performance metrics.</p>
                    </div>
                ) : (
                    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>

                        {/* KPI Cards based on REAL averages */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '20px', marginBottom: '40px' }}>
                            <KpiCard title="Avg Wait Time" value={`${avg('wait')}s`} sub="Live Average" color={Number(avg('wait')) < 60 ? '#22c55e' : '#ef4444'} />
                            <KpiCard title="Avg Queue" value={`${avg('queue')} veh`} sub="Live Average" color={Number(avg('queue')) < 50 ? '#38bdf8' : '#f472b6'} />
                            <KpiCard title="Active Vehicles" value={avg('vehicles')} sub="Traffic Load" color="#fbbf24" />
                        </div>

                        {/* Charts Grid */}
                        <div style={{ background: '#1e293b', padding: '20px', borderRadius: '12px', border: '1px solid #334155', marginBottom: '30px' }}>
                            <h3 style={{ marginTop: 0, color: '#94a3b8' }}>Waiting Time: Live vs Baseline</h3>
                            <div style={{ height: '400px' }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={data}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                                        <XAxis dataKey="time" stroke="#94a3b8" label={{ value: 'Simulation Time (s)', position: 'insideBottom', offset: -5 }} />
                                        <YAxis stroke="#94a3b8" label={{ value: 'Delay (s)', angle: -90, position: 'insideLeft' }} />
                                        <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155' }} />
                                        <Legend />
                                        <Line type="monotone" dataKey="baseline" name="Fixed-Time Baseline" stroke="#ef4444" strokeWidth={2} dot={false} strokeDasharray="5 5" />
                                        <Line type="monotone" dataKey="wait" name="Live System Performance" stroke="#22c55e" strokeWidth={3} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div style={{ textAlign: 'center', color: '#64748b' }}>
                            <p>Data Source: Real-time Simulation Logs (localStorage)</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

const KpiCard = ({ title, value, sub, color }: any) => (
    <div style={{ background: '#1e293b', padding: '25px', borderRadius: '12px', borderLeft: `5px solid ${color}`, boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
        <div style={{ color: '#94a3b8', fontSize: '0.9em', textTransform: 'uppercase', letterSpacing: '1px' }}>{title}</div>
        <div style={{ fontSize: '2.5em', fontWeight: 'bold', color: 'white', margin: '10px 0' }}>{value}</div>
        <div style={{ color: color, fontSize: '0.9em', fontWeight: 'bold' }}>{sub}</div>
    </div>
);
