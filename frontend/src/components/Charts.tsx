/**
 * Real-time Charts Component
 * Displays queue length and waiting time over time
 */
import React from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';

interface ChartData {
    time: number;
    queue_length: number;
    waiting_time: number;
    vehicle_count: number;
}

interface ChartsProps {
    data: ChartData[];
}

export const Charts: React.FC<ChartsProps> = ({ data }) => {
    return (
        <div className="charts-container">
            <div className="chart-section">
                <h3>Queue Length Over Time</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis
                            dataKey="time"
                            label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }}
                            stroke="#fff"
                        />
                        <YAxis
                            label={{ value: 'Queue Length', angle: -90, position: 'insideLeft' }}
                            stroke="#fff"
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #16213e' }}
                        />
                        <Legend />
                        <Line
                            type="monotone"
                            dataKey="queue_length"
                            stroke="#00d4ff"
                            strokeWidth={2}
                            dot={false}
                            name="Queue Length"
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div className="chart-section">
                <h3>Average Waiting Time</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis
                            dataKey="time"
                            label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }}
                            stroke="#fff"
                        />
                        <YAxis
                            label={{ value: 'Waiting Time (s)', angle: -90, position: 'insideLeft' }}
                            stroke="#fff"
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #16213e' }}
                        />
                        <Legend />
                        <Line
                            type="monotone"
                            dataKey="waiting_time"
                            stroke="#ff6b6b"
                            strokeWidth={2}
                            dot={false}
                            name="Avg Waiting Time"
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div className="chart-section">
                <h3>Vehicle Count</h3>
                <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis
                            dataKey="time"
                            label={{ value: 'Time (s)', position: 'insideBottom', offset: -5 }}
                            stroke="#fff"
                        />
                        <YAxis
                            label={{ value: 'Vehicles', angle: -90, position: 'insideLeft' }}
                            stroke="#fff"
                        />
                        <Tooltip
                            contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #16213e' }}
                        />
                        <Legend />
                        <Line
                            type="monotone"
                            dataKey="vehicle_count"
                            stroke="#4ecdc4"
                            strokeWidth={2}
                            dot={false}
                            name="Vehicle Count"
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
