import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getLocations, startSimulation, LocationsMap } from '../services/api';

export const JunctionSelection: React.FC = () => {
    const navigate = useNavigate();
    const [locations, setLocations] = useState<LocationsMap>({});
    const [selectedLocation, setSelectedLocation] = useState<string>('silk_board');
    const [intensity, setIntensity] = useState<'peak' | 'offpeak'>('peak');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        loadLocations();
    }, []);

    const loadLocations = async () => {
        try {
            const data = await getLocations();
            setLocations(data);
            if (Object.keys(data).length > 0) {
                setSelectedLocation(Object.keys(data)[0]);
            }
        } catch (err) {
            console.error("Failed to load locations", err);
        }
    };

    const handleStart = async () => {
        setLoading(true);
        try {
            // Start simulation with selected params
            // Defaulting to 'fixed' mode initially, user can switch in dashboard
            await startSimulation('fixed', true, intensity, selectedLocation);

            // Navigate to dashboard
            navigate('/dashboard');
        } catch (err) {
            console.error("Failed to start", err);
            alert("Failed to start simulation. Check console.");
        } finally {
            setLoading(false);
        }
    };

    const currentLocation = locations[selectedLocation];

    return (
        <div className="junction-page" style={{ height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#0f172a', color: 'white' }}>
            <div className="card" style={{ background: '#1e293b', padding: '40px', borderRadius: '16px', border: '1px solid #334155', width: '100%', maxWidth: '500px', boxShadow: '0 10px 30px rgba(0,0,0,0.5)' }}>
                <h2 style={{ marginTop: 0, marginBottom: '30px', textAlign: 'center', borderBottom: '1px solid #334155', paddingBottom: '20px' }}>
                    Select Simulation Scenario
                </h2>

                <div className="form-group" style={{ marginBottom: '25px' }}>
                    <label style={{ display: 'block', marginBottom: '10px', color: '#94a3b8', fontSize: '0.9em' }}>TARGET JUNCTION</label>
                    <select
                        value={selectedLocation}
                        onChange={(e) => setSelectedLocation(e.target.value)}
                        style={{ width: '100%', padding: '12px', background: '#0f172a', border: '1px solid #475569', borderRadius: '8px', color: 'white', fontSize: '1.1em' }}
                    >
                        {Object.entries(locations).map(([key, loc]) => (
                            <option key={key} value={key}>{loc.name}</option>
                        ))}
                    </select>
                    {currentLocation && (
                        <p style={{ fontSize: '0.9em', color: '#64748b', marginTop: '8px' }}>
                            {currentLocation.description}
                        </p>
                    )}
                </div>

                <div className="form-group" style={{ marginBottom: '35px' }}>
                    <label style={{ display: 'block', marginBottom: '10px', color: '#94a3b8', fontSize: '0.9em' }}>TRAFFIC INTENSITY</label>
                    <div className="intensity-selector" style={{ display: 'flex', gap: '10px' }}>
                        <button
                            onClick={() => setIntensity('peak')}
                            style={{
                                flex: 1,
                                padding: '12px',
                                background: intensity === 'peak' ? 'rgba(239, 68, 68, 0.2)' : '#0f172a',
                                border: intensity === 'peak' ? '1px solid #ef4444' : '1px solid #475569',
                                color: intensity === 'peak' ? '#ef4444' : '#94a3b8',
                                borderRadius: '8px',
                                cursor: 'pointer'
                            }}
                        >
                            🔥 Peak Hour
                        </button>
                        <button
                            onClick={() => setIntensity('offpeak')}
                            style={{
                                flex: 1,
                                padding: '12px',
                                background: intensity === 'offpeak' ? 'rgba(34, 197, 94, 0.2)' : '#0f172a',
                                border: intensity === 'offpeak' ? '1px solid #22c55e' : '1px solid #475569',
                                color: intensity === 'offpeak' ? '#22c55e' : '#94a3b8',
                                borderRadius: '8px',
                                cursor: 'pointer'
                            }}
                        >
                            🌤️ Normal Flow
                        </button>
                    </div>
                </div>

                <button
                    onClick={handleStart}
                    disabled={loading}
                    style={{
                        width: '100%',
                        padding: '16px',
                        fontSize: '1.2em',
                        fontWeight: 'bold',
                        color: 'white',
                        background: 'linear-gradient(90deg, #10b981, #059669)',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        opacity: loading ? 0.7 : 1,
                        boxShadow: '0 4px 15px rgba(16, 185, 129, 0.4)'
                    }}
                >
                    {loading ? 'Initializing SUMO...' : '▶ Start Live Simulation'}
                </button>
            </div>
        </div>
    );
};
