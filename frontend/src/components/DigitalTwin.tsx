import React from 'react';
import { SignalState } from './SignalState';

interface DigitalTwinProps {
    queueLength: number;
    vehicleCount: number;
    trafficLights: any; // Raw signals
}

export const DigitalTwin: React.FC<DigitalTwinProps> = ({ queueLength, vehicleCount, trafficLights }) => {
    // Determine congestion color
    const getCongestionColor = () => {
        if (queueLength > 80) return '#ef4444'; // Red
        if (queueLength > 40) return '#eab308'; // Yellow
        return '#22c55e'; // Green
    };

    const color = getCongestionColor();
    const pulseSpeed = Math.max(0.5, 2 - (vehicleCount / 100)); // Faster pulse if more cars

    return (
        <div className="digital-twin-container" style={{
            width: '100%',
            height: '100%',
            background: 'radial-gradient(circle at center, #1e293b 0%, #0f172a 70%)',
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
            borderRight: '1px solid #334155'
        }}>
            {/* Grid Background */}
            <div style={{
                position: 'absolute',
                width: '200%',
                height: '200%',
                backgroundSize: '40px 40px',
                backgroundImage: 'linear-gradient(rgba(51, 65, 85, 0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(51, 65, 85, 0.3) 1px, transparent 1px)',
                transform: 'perspective(500px) rotateX(60deg) translateY(-100px)',
                opacity: 0.5,
                zIndex: 1
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

            {/* Central Node (The Junction) */}
            <div style={{
                width: '150px',
                height: '150px',
                borderRadius: '50%',
                background: `radial-gradient(circle, ${color} 0%, transparent 70%)`,
                boxShadow: `0 0 50px ${color}40`,
                zIndex: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: `2px solid ${color}40`,
                animation: `pulse ${pulseSpeed}s infinite`
            }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '2em', fontWeight: 'bold', color: 'white' }}>{vehicleCount}</div>
                    <div style={{ fontSize: '0.6em', textTransform: 'uppercase', letterSpacing: '2px', color: '#cbd5e1' }}>VEHICLES</div>
                </div>
            </div>

            {/* Incoming Lanes (Visual Decoration) */}
            {[0, 90, 180, 270].map((deg, i) => (
                <div key={i} style={{
                    position: 'absolute',
                    width: '40%',
                    height: '2px',
                    background: `linear-gradient(90deg, transparent, ${color})`,
                    transform: `rotate(${deg}deg) translateX(60%)`,
                    zIndex: 5
                }}>
                    {/* Moving Particles */}
                    <div style={{
                        position: 'absolute',
                        width: '8px',
                        height: '2px',
                        background: 'white',
                        boxShadow: '0 0 10px white',
                        animation: `flow 1.5s linear infinite`,
                        animationDelay: `${i * 0.2}s`
                    }}></div>
                </div>
            ))}

            {/* HUD Overlay for Signal State (Floating Top Left) */}
            <div style={{ position: 'absolute', top: '20px', left: '20px', zIndex: 20, width: '300px' }}>
                <h3 style={{ margin: '0 0 10px 0', fontSize: '0.9em', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ width: '8px', height: '8px', background: '#22c55e', borderRadius: '50%', boxShadow: '0 0 5px #22c55e' }}></span>
                    LIVE SIGNAL TELEMETRY
                </h3>
                {/* Re-use the polished SignalState component */}
                <SignalState trafficLights={trafficLights} />
            </div>

            {/* Simulation Status (Bottom Right) */}
            <div style={{ position: 'absolute', bottom: '20px', right: '20px', zIndex: 20, textAlign: 'right' }}>
                <div style={{ fontSize: '0.8em', color: '#64748b' }}>CONGESTION INDEX</div>
                <div style={{ fontSize: '1.5em', fontWeight: 'bold', color: color }}>
                    {queueLength > 80 ? 'CRITICAL' : (queueLength > 40 ? 'HEAVY' : 'STABLE')}
                </div>
            </div>

            {/* CSS Animations */}
            <style>{`
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
                @keyframes pulse { 0% { transform: scale(1); opacity: 0.8; } 50% { transform: scale(1.05); opacity: 1; } 100% { transform: scale(1); opacity: 0.8; } }
                @keyframes flow { 0% { left: 0; opacity: 0; } 50% { opacity: 1; } 100% { left: 100%; opacity: 0; } }
            `}</style>
        </div>
    );
};
