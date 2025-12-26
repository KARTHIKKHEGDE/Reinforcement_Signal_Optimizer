/**
 * Traffic Map Component
 * Visual representation of the intersection
 */
import React from 'react';

interface TrafficMapProps {
    queueLength: number;
    vehicleCount: number;
}

export const TrafficMap: React.FC<TrafficMapProps> = ({ queueLength, vehicleCount }) => {
    return (
        <div className="traffic-map-container">
            <h3>Intersection Overview</h3>

            <div className="map-wrapper">
                <svg viewBox="0 0 400 400" className="intersection-svg">
                    {/* Background */}
                    <rect width="400" height="400" fill="#0f0f1e" />

                    {/* Roads */}
                    {/* Vertical road */}
                    <rect x="150" y="0" width="100" height="400" fill="#2a2a3e" />
                    {/* Horizontal road */}
                    <rect x="0" y="150" width="400" height="100" fill="#2a2a3e" />

                    {/* Lane markings */}
                    {/* Vertical center line */}
                    <line x1="200" y1="0" x2="200" y2="150" stroke="#ffff00" strokeWidth="2" strokeDasharray="10,10" />
                    <line x1="200" y1="250" x2="200" y2="400" stroke="#ffff00" strokeWidth="2" strokeDasharray="10,10" />
                    {/* Horizontal center line */}
                    <line x1="0" y1="200" x2="150" y2="200" stroke="#ffff00" strokeWidth="2" strokeDasharray="10,10" />
                    <line x1="250" y1="200" x2="400" y2="200" stroke="#ffff00" strokeWidth="2" strokeDasharray="10,10" />

                    {/* Junction box */}
                    <rect x="150" y="150" width="100" height="100" fill="#1a1a2e" stroke="#ffff00" strokeWidth="2" />

                    {/* Traffic lights */}
                    {/* North */}
                    <circle cx="180" cy="140" r="8" fill="#ff0000" className="traffic-light" />
                    <circle cx="220" cy="140" r="8" fill="#ff0000" className="traffic-light" />

                    {/* South */}
                    <circle cx="180" cy="260" r="8" fill="#ff0000" className="traffic-light" />
                    <circle cx="220" cy="260" r="8" fill="#ff0000" className="traffic-light" />

                    {/* East */}
                    <circle cx="260" cy="180" r="8" fill="#ff0000" className="traffic-light" />
                    <circle cx="260" cy="220" r="8" fill="#ff0000" className="traffic-light" />

                    {/* West */}
                    <circle cx="140" cy="180" r="8" fill="#ff0000" className="traffic-light" />
                    <circle cx="140" cy="220" r="8" fill="#ff0000" className="traffic-light" />

                    {/* Direction arrows */}
                    {/* North arrow */}
                    <text x="200" y="80" textAnchor="middle" fill="#fff" fontSize="20">↑</text>
                    <text x="200" y="100" textAnchor="middle" fill="#aaa" fontSize="12">N</text>

                    {/* South arrow */}
                    <text x="200" y="320" textAnchor="middle" fill="#fff" fontSize="20">↓</text>
                    <text x="200" y="340" textAnchor="middle" fill="#aaa" fontSize="12">S</text>

                    {/* East arrow */}
                    <text x="320" y="205" textAnchor="middle" fill="#fff" fontSize="20">→</text>
                    <text x="340" y="205" textAnchor="middle" fill="#aaa" fontSize="12">E</text>

                    {/* West arrow */}
                    <text x="80" y="205" textAnchor="middle" fill="#fff" fontSize="20">←</text>
                    <text x="60" y="205" textAnchor="middle" fill="#aaa" fontSize="12">W</text>
                </svg>
            </div>

            <div className="map-stats">
                <div className="stat-item">
                    <span className="stat-label">Queue Length:</span>
                    <span className="stat-value">{queueLength}</span>
                </div>
                <div className="stat-item">
                    <span className="stat-label">Active Vehicles:</span>
                    <span className="stat-value">{vehicleCount}</span>
                </div>
            </div>
        </div>
    );
};
