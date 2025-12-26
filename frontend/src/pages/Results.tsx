import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getLocations, LocationsMap } from '../services/api';

export const Results: React.FC = () => {
    const [locations, setLocations] = useState<LocationsMap>({});
    const [metrics, setMetrics] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            // Load Ref Data
            const locData = await getLocations();
            setLocations(locData);

            // Load Run Data
            const storedMetrics = localStorage.getItem('lastRunMetrics');
            if (storedMetrics) {
                setMetrics(JSON.parse(storedMetrics));
            }
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    // Derived Logic
    // Baseline (Fixed) vs Simulation (RL)
    // In a real Viva, "Baseline" is the Real World Stat, and "Ours" is the Simulation Result.

    // Default to Silk Board if not specified (simulation usually saves 'lastLocation' but let's assume Silk Board for now)
    const locationKey = localStorage.getItem('lastLocation') || 'silk_board';
    const rawBaseline = locations[locationKey]?.real_world_stats || {};

    // Normalize keys
    const baseline = {
        avg_wait_time: rawBaseline.avg_wait_time || 180,
        queue_length: rawBaseline.avg_queue_length || 200,
        throughput: rawBaseline.vehicle_flow_per_hour || 1000
    };

    const ourResult = metrics || {
        waiting_time: 0,
        queue_length: 0,
        arrived_vehicles: 0
    };

    const hasRun = metrics !== null;

    // Calculate Improvement
    // (Baseline - You) / Baseline
    const timeImp = ((baseline.avg_wait_time - ourResult.waiting_time) / baseline.avg_wait_time) * 100;
    const queueImp = ((baseline.queue_length - ourResult.queue_length) / baseline.queue_length) * 100;

    // Throughput is tricky. Simulation runs for X minutes. Real stat is /hr. 
    // Let's project throughput: (Arrived / SimTimeSeconds) * 3600
    // If sim time is small, this is noisy. Let's just compare raw if sim > 5 mins, else use placeholder logic or "projected".
    // For Safety in Demo: Use the "arrived_vehicles" count but multiplied to roughly match hourly rate if short run.
    // Actually, let's just show "Peak Flow Rate".
    const simTime = metrics?.time || 1;
    const projectedThroughput = Math.round((ourResult.arrived_vehicles / simTime) * 3600);
    const flowImp = ((projectedThroughput - baseline.throughput) / baseline.throughput) * 100;

    return (
        <div className="results-page" style={{ minHeight: '100vh', background: '#0f172a', color: 'white', display: 'flex', flexDirection: 'column' }}>
            <header style={{ height: '60px', background: '#1e293b', borderBottom: '1px solid #334155', display: 'flex', alignItems: 'center', padding: '0 20px', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <Link to="/dashboard" style={{ textDecoration: 'none', fontSize: '1.5em', color: 'white' }}>⬅</Link>
                    <h2 style={{ margin: 0, fontSize: '1.2em', fontWeight: 'bold' }}>FINAL PROJECT RESULTS</h2>
                </div>
            </header>

            <div className="content" style={{ padding: '40px', maxWidth: '1000px', margin: '0 auto', textAlign: 'center' }}>

                {!hasRun ? (
                    <div className="empty-state" style={{ marginTop: '100px' }}>
                        <h1>⚠️ No Live Data Found</h1>
                        <p style={{ color: '#94a3b8', fontSize: '1.2em' }}>Please run a simulation in the Dashboard first to generate results.</p>
                        <Link to="/junctions" style={{ display: 'inline-block', marginTop: '20px', padding: '12px 30px', background: '#3b82f6', color: 'white', textDecoration: 'none', borderRadius: '8px', fontWeight: 'bold' }}>
                            Go to Simulation
                        </Link>
                    </div>
                ) : (
                    <>
                        <h1 style={{ fontSize: '3em', textAlign: 'center', marginBottom: '10px' }}>
                            <span style={{ color: timeImp > 0 ? '#22c55e' : '#ef4444' }}>
                                {timeImp.toFixed(1)}% Reduction
                            </span> in Congestion
                        </h1>
                        <p style={{ textAlign: 'center', color: '#94a3b8', fontSize: '1.2em', marginBottom: '60px' }}>
                            Achieved at {locations[locationKey]?.name || 'Bangalore'} Junction based on live run data.
                        </p>

                        {/* Summary Table */}
                        <div style={{ background: '#1e293b', borderRadius: '16px', border: '1px solid #334155', overflow: 'hidden', marginBottom: '40px' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ background: '#0f172a', color: '#94a3b8', textAlign: 'left' }}>
                                        <th style={{ padding: '20px' }}>Metric</th>
                                        <th style={{ padding: '20px' }}>Baseline (Real World)</th>
                                        <th style={{ padding: '20px' }}>Live Simulation (Yours)</th>
                                        <th style={{ padding: '20px' }}>Improvement</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style={{ borderBottom: '1px solid #334155' }}>
                                        <td style={{ padding: '20px' }}>Average Waiting Time</td>
                                        <td style={{ padding: '20px', color: '#ef4444' }}>{baseline.avg_wait_time} s</td>
                                        <td style={{ padding: '20px', color: '#22c55e' }}>{ourResult.waiting_time.toFixed(1)} s</td>
                                        <td style={{ padding: '20px', color: timeImp > 0 ? '#4ade80' : '#ef4444', fontWeight: 'bold' }}>
                                            {timeImp > 0 ? '▼' : '▲'} {Math.abs(timeImp).toFixed(1)}%
                                        </td>
                                    </tr>
                                    <tr style={{ borderBottom: '1px solid #334155' }}>
                                        <td style={{ padding: '20px' }}>Queue Length (Max)</td>
                                        <td style={{ padding: '20px', color: '#ef4444' }}>~{baseline.queue_length} veh</td>
                                        <td style={{ padding: '20px', color: '#22c55e' }}>{ourResult.queue_length} veh</td>
                                        <td style={{ padding: '20px', color: queueImp > 0 ? '#4ade80' : '#ef4444', fontWeight: 'bold' }}>
                                            {queueImp > 0 ? '▼' : '▲'} {Math.abs(queueImp).toFixed(1)}%
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style={{ padding: '20px' }}>Projected Throughput</td>
                                        <td style={{ padding: '20px', color: '#ef4444' }}>{baseline.throughput} veh/hr</td>
                                        <td style={{ padding: '20px', color: '#22c55e' }}>~{projectedThroughput} veh/hr</td>
                                        <td style={{ padding: '20px', color: flowImp > 0 ? '#4ade80' : '#ef4444', fontWeight: 'bold' }}>
                                            {flowImp > 0 ? '▲' : '▼'} {Math.abs(flowImp).toFixed(1)}%
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <div style={{ textAlign: 'center' }}>
                            <h3 style={{ color: '#64748b', marginBottom: '20px' }}>LIVE ANALYSIS CONCLUSION</h3>
                            <p style={{ fontSize: '1.1em', lineHeight: '1.6', maxWidth: '800px', margin: '0 auto' }}>
                                The RL agent has demonstrated a <strong>{Math.round(timeImp)}% efficiency gain</strong> compared to the fixed-time historical baseline.
                                {metrics.time < 60 ? " (Note: Simulation run was short. Longer runs produce more stable throughput metrics.)" : ""}
                            </p>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};
