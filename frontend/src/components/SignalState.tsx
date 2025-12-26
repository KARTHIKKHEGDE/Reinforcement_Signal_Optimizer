import React from 'react';

interface TrafficLight {
    phase: number;
    state: string;
}

interface SignalStateProps {
    trafficLights: Record<string, TrafficLight>;
}

export const SignalState: React.FC<SignalStateProps> = ({ trafficLights }) => {

    const formatId = (id: string, index: number) => {
        if (id.includes('joinedS')) return 'Primary Signal Controller';
        if (id.includes('cluster')) return 'Secondary Signal';
        return `Signal #${index + 1}`;
    };

    const getPhaseDesc = (state: string) => {
        const greens = (state.match(/G|g/g) || []).length;
        const reds = (state.match(/r/g) || []).length;
        if (state.includes('y')) return "⚠️ CLEARANCE";
        if (greens > reds) return "🟢 GO PHASE";
        return "🔴 STOP PHASE";
    };

    const sortedIds = Object.keys(trafficLights).sort((a, b) => b.length - a.length); // Assuming longest ID is main joined signal

    return (
        <div className="signal-container" style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '300px', overflowY: 'auto' }}>
            {sortedIds.map((id, index) => {
                const light = trafficLights[id];
                const cleanId = formatId(id, index);

                return (
                    <div key={id} style={{
                        background: 'rgba(30, 41, 59, 0.9)',
                        backdropFilter: 'blur(4px)',
                        padding: '12px',
                        borderRadius: '8px',
                        border: '1px solid #475569',
                        boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
                        borderLeft: `4px solid ${light.state.includes('y') ? '#eab308' : (light.state.includes('G') ? '#22c55e' : '#ef4444')}`
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <h4 style={{ margin: 0, fontSize: '0.9em', color: '#e2e8f0' }}>{cleanId}</h4>
                            <span style={{ fontSize: '0.7em', fontWeight: 'bold', color: '#94a3b8', background: '#0f172a', padding: '2px 6px', borderRadius: '4px' }}>
                                Phase {light.phase}
                            </span>
                        </div>

                        {/* Dynamic Lights Visualization */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginBottom: '4px' }}>
                            {light.state.split('').map((char, i) => {
                                let color = '#334155';
                                if (char === 'G' || char === 'g') color = '#22c55e';
                                if (char === 'r') color = '#ef4444';
                                if (char === 'y' || char === 'Y') color = '#eab308';

                                return (
                                    <div key={i} style={{
                                        width: '10px',
                                        height: '10px',
                                        borderRadius: '50%',
                                        background: color,
                                        boxShadow: color !== '#334155' ? `0 0 5px ${color}` : 'none',
                                        transition: 'background 0.3s'
                                    }} title={`Signal Index ${i}: ${char}`} />
                                );
                            })}
                        </div>

                        <div style={{ fontSize: '0.75em', color: '#64748b', display: 'flex', justifyContent: 'space-between' }}>
                            <span>{getPhaseDesc(light.state)}</span>
                            <span style={{ opacity: 0.5 }}>{light.state.length} lanes</span>
                        </div>
                    </div>
                );
            })}
            {Object.keys(trafficLights).length === 0 && (
                <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '0.9em' }}>
                    Waiting for signal data...
                </div>
            )}
        </div>
    );
};
