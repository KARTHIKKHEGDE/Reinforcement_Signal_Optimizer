import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Landing } from './pages/Landing';
import { JunctionSelection } from './pages/JunctionSelection';
import { Dashboard } from './pages/Dashboard';
import { Comparison } from './pages/Comparison';
import { AgentInsights } from './pages/AgentInsights';
import { Results } from './pages/Results';
import './App.css';

function App() {
    return (
        <Router>
            <div className="App">
                <Routes>
                    <Route path="/" element={<Landing />} />
                    <Route path="/junctions" element={<JunctionSelection />} />
                    <Route path="/dashboard" element={<Dashboard />} />
                    <Route path="/comparison" element={<Comparison />} />
                    <Route path="/agent" element={<AgentInsights />} />
                    <Route path="/results" element={<Results />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </div>
        </Router>
    );
}

export default App;
