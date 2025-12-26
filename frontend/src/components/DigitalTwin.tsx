import React, { useEffect } from 'react';
import { SignalState } from './SignalState';

interface DigitalTwinProps {
    queueLength: number;
    vehicleCount: number;
    trafficLights: any;
    locationId?: string;
}

const LOCATION_COORDS: Record<string, [number, number]> = {
    'silk_board': [12.9175, 77.6234],
    'tin_factory': [12.9976, 77.6601],
    'hebbal': [13.0334, 77.5891]
};

export const DigitalTwin: React.FC<DigitalTwinProps> = ({ queueLength, vehicleCount, trafficLights, locationId = 'silk_board' }) => {
    // Determine congestion color
    const getCongestionColor = () => {
        if (queueLength > 80) return '#ef4444'; // Red
        if (queueLength > 40) return '#eab308'; // Yellow
        return '#22c55e'; // Green
    };

    const color = getCongestionColor();
    const pulseSpeed = Math.max(0.5, 2 - (vehicleCount / 100)); // Faster pulse if more cars

    const center = LOCATION_COORDS[locationId] || LOCATION_COORDS['silk_board'];

    // Calculate BBox for OSM Embed
    const offset = 0.003; // Radius
    const bbox = `${center[1] - offset},${center[0] - offset},${center[1] + offset},${center[0] + offset}`;
    const embedUrl = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${center[0]},${center[1]}`;

    return (
        <div className="digital-twin-container" style={{
            width: '100%',
            height: '100%',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            background: '#0f172a'
        }}>

            {/* 🌍 REAL MAP BACKGROUND (Using Iframe for Stability) */}
            <div style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', zIndex: 0, filter: 'invert(100%) hue-rotate(180deg) brightness(0.8) contrast(1.2)' }}>
                <iframe
                    width="100%"
                    height="100%"
                    frameBorder="0"
                    scrolling="no"
                    marginHeight={0}
                    marginWidth={0}
                    src={embedUrl}
                    style={{ pointerEvents: 'none' }} // Disable map interaction to keep focus on scanner
                ></iframe>
            </div>

            {/* 🕸️ SCANNER OVERLAY (The "Digital Twin" Effect) */}
            <div className="scanner-overlay" style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: 'radial-gradient(circle at center, transparent 30%, #0f172a 90%)',
                zIndex: 1,
                pointerEvents: 'none'
            }}></div>

            {/* Radar Scan Effect */}
            <div className="radar-sweep" style={{
                position: 'absolute',
                width: '100%',
                height: '100%',
                background: 'conic-gradient(from 0deg, transparent 0deg, rgba(56, 189, 248, 0.1) 60deg, transparent 60deg)',
                borderRadius: '50%',
                animation: 'spin 4s linear infinite',
                zIndex: 2,
                pointerEvents: 'none'
            }}></div>

            {/* Central Node (The Junction Status) */}
            <div style={{
                width: '140px',
                height: '140px',
                borderRadius: '50%',
                background: `rgba(15, 23, 42, 0.8)`,
                boxShadow: `0 0 30px ${color}60`,
                zIndex: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: `2px solid ${color}`,
                backdropFilter: 'blur(4px)',
                animation: `pulse ${pulseSpeed}s infinite`
            }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '2em', fontWeight: 'bold', color: 'white' }}>{vehicleCount}</div>
                    <div style={{ fontSize: '0.6em', textTransform: 'uppercase', letterSpacing: '2px', color: '#cbd5e1' }}>VEHICLES</div>
                </div>
            </div>

            {/* HUD Overlay for Signal State (Floating Top Left) */}
            <div style={{ position: 'absolute', top: '20px', left: '20px', zIndex: 20, width: '300px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '0.9em', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(0,0,0,0.6)', padding: '5px', borderRadius: '4px', width: 'fit-content' }}>
                    <span style={{ width: '8px', height: '8px', background: '#22c55e', borderRadius: '50%', boxShadow: '0 0 5px #22c55e' }}></span>
                    LIVE SIGNAL TELEMETRY
                </h3>
                <SignalState trafficLights={trafficLights} />
            </div>

            {/* Simulation Status (Bottom Right) */}
            <div style={{ position: 'absolute', bottom: '20px', right: '20px', zIndex: 20, textAlign: 'right' }}>
                <div style={{ fontSize: '0.8em', color: '#64748b', background: 'rgba(0,0,0,0.6)', padding: '2px 8px', borderRadius: '4px' }}>CONGESTION INDEX</div>
                <div style={{ fontSize: '1.5em', fontWeight: 'bold', color: color, textShadow: '0 2px 4px rgba(0,0,0,0.5)' }}>
                    {queueLength > 80 ? 'CRITICAL' : (queueLength > 40 ? 'HEAVY' : 'STABLE')}
                </div>
                <div style={{ fontSize: '0.8em', color: '#94a3b8', marginTop: '5px' }}>
                    📍 {locationId.replace('_', ' ').toUpperCase()}
                </div>
            </div>

            {/* CSS Animations */}
            <style>{`
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
                @keyframes pulse { 0% { transform: scale(1); border-color: ${color}; } 50% { transform: scale(1.05); border-color: white; } 100% { transform: scale(1); border-color: ${color}; } }
            `}</style>
        </div>
    );
};
