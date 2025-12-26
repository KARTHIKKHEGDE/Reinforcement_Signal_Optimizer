/**
 * Traffic Signal State Component
 * Displays current traffic light phases and states
 */
import React from 'react';

interface TrafficLight {
    phase: number;
    state: string;
}

interface SignalStateProps {
    trafficLights: Record<string, TrafficLight>;
}

export const SignalState: React.FC<SignalStateProps> = ({ trafficLights }) => {
    const getPhaseColor = (state: string, index: number): string => {
        if (!state || index >= state.length) return '#333';

        const char = state[index].toLowerCase();
        switch (char) {
            case 'g':
            case 'G':
                return '#00ff00'; // Green
            case 'y':
                return '#ffff00'; // Yellow
            case 'r':
                return '#ff0000'; // Red
            default:
                return '#333'; // Off
        }
    };

    const getPhaseDescription = (phase: number): string => {
        switch (phase) {
            case 0:
                return 'North-South Green';
            case 1:
                return 'North-South Yellow';
            case 2:
                return 'East-West Green';
            case 3:
                return 'East-West Yellow';
            default:
                return `Phase ${phase}`;
        }
    };

    return (
        <div className="signal-state-container">
            <h3>Traffic Signal States</h3>
            {Object.entries(trafficLights).map(([junctionId, light]) => (
                <div key={junctionId} className="signal-card">
                    <div className="signal-header">
                        <h4>{junctionId}</h4>
                        <span className="phase-badge">
                            Phase {light.phase}: {getPhaseDescription(light.phase)}
                        </span>
                    </div>

                    <div className="signal-lights">
                        <div className="direction-group">
                            <span className="direction-label">North-South</span>
                            <div className="lights">
                                <div
                                    className="light"
                                    style={{ backgroundColor: getPhaseColor(light.state, 0) }}
                                    title={light.state[0]}
                                />
                                <div
                                    className="light"
                                    style={{ backgroundColor: getPhaseColor(light.state, 1) }}
                                    title={light.state[1]}
                                />
                            </div>
                        </div>

                        <div className="direction-group">
                            <span className="direction-label">East-West</span>
                            <div className="lights">
                                <div
                                    className="light"
                                    style={{ backgroundColor: getPhaseColor(light.state, 4) }}
                                    title={light.state[4]}
                                />
                                <div
                                    className="light"
                                    style={{ backgroundColor: getPhaseColor(light.state, 5) }}
                                    title={light.state[5]}
                                />
                            </div>
                        </div>
                    </div>

                    <div className="state-string">
                        <span className="label">State:</span>
                        <code>{light.state}</code>
                    </div>
                </div>
            ))}

            {Object.keys(trafficLights).length === 0 && (
                <div className="no-data">
                    <p>No traffic light data available</p>
                    <p className="hint">Start a simulation to see live signal states</p>
                </div>
            )}
        </div>
    );
};
