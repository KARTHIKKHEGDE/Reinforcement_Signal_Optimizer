import React from 'react';
import { useNavigate } from 'react-router-dom';

export const Landing: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="landing-page" style={{ height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', color: 'white', textAlign: 'center', padding: '20px' }}>

            <div className="hero-content" style={{ maxWidth: '800px', animation: 'fadeIn 1s ease-in' }}>
                <div className="badge" style={{ display: 'inline-block', padding: '4px 12px', borderRadius: '20px', background: 'rgba(56, 189, 248, 0.1)', color: '#38bdf8', border: '1px solid #38bdf8', marginBottom: '20px', fontSize: '0.9em', fontWeight: 'bold' }}>
                    TRAFFIC INTELLIGENCE SYSTEM
                </div>

                <h1 style={{ fontSize: '3.5em', fontWeight: '800', lineHeight: '1.2', marginBottom: '15px' }}>
                    AI-Based Adaptive <br />
                    <span style={{ background: 'linear-gradient(to right, #4ade80, #38bdf8)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                        Traffic Signal Control
                    </span> <br />
                    for Bangalore Junctions
                </h1>

                <p style={{ fontSize: '1.25em', color: '#94a3b8', marginBottom: '40px', maxWidth: '600px', margin: '0 auto 40px' }}>
                    Live SUMO Simulation • Reinforcement Learning • Real-World Calibration
                </p>

                <div className="action-area">
                    <button
                        onClick={() => navigate('/junctions')}
                        style={{
                            padding: '16px 40px',
                            fontSize: '1.2em',
                            fontWeight: 'bold',
                            color: 'white',
                            background: 'linear-gradient(90deg, #2563eb, #3b82f6)',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            boxShadow: '0 4px 15px rgba(37, 99, 235, 0.4)',
                            transition: 'transform 0.2s, box-shadow 0.2s'
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(37, 99, 235, 0.6)'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = '0 4px 15px rgba(37, 99, 235, 0.4)'; }}
                    >
                        🚀 Launch Simulation
                    </button>

                    <p style={{ marginTop: '20px', fontSize: '0.9em', color: '#64748b' }}>
                        Simulating: Silk Board • Tin Factory • Hebbal
                    </p>
                </div>
            </div>

            <footer style={{ position: 'absolute', bottom: '20px', fontSize: '0.8em', color: '#475569' }}>
                Advanced Agentic Coding • Google DeepMind Project
            </footer>
        </div>
    );
};
