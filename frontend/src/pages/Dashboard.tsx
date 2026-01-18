import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { NavHeader } from "../components/NavHeader";
import { StatusBar } from "../components/StatusBar";
import { DigitalTwin } from "../components/DigitalTwin";
import { wsService, SimulationMetrics } from "../services/socket";
import {
  stopSimulation,
  resetSimulation,
  getSimulationStatus,
} from "../services/api";

interface DashboardProps {}

export const Dashboard: React.FC<DashboardProps> = () => {
  const navigate = useNavigate();
  const [isRunning, setIsRunning] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [currentMode, setCurrentMode] = useState<"fixed" | "rl">(
    (localStorage.getItem("selectedMode") as "fixed" | "rl") || "fixed",
  );
  const [currentMetrics, setCurrentMetrics] =
    useState<SimulationMetrics | null>(null);
  const [loading, setLoading] = useState(false);

  const [stats, setStats] = useState({
    maxQueue: 0,
    totalWaitTime: 0,
    dataPoints: 0,
    startTime: 0,
  });

  useEffect(() => {
    const init = async () => {
      try {
        const status = await getSimulationStatus();
        setIsRunning(status.running);

        // Always try to connect WebSocket when Dashboard loads
        wsService.connect();

        // Poll connection status every 2 seconds
        const connectionCheckInterval = setInterval(() => {
          setIsConnected(wsService.isConnected());
        }, 2000);

        return () => clearInterval(connectionCheckInterval);
      } catch (e) {
        console.error(e);
      }
    };
    init();

    const unsubscribe = wsService.subscribe((metrics: SimulationMetrics) => {
      setIsConnected(true); // Mark as connected when we receive data
      setCurrentMetrics(metrics);
      setStats((prev) => ({
        maxQueue: Math.max(prev.maxQueue, metrics.queue_length || 0),
        totalWaitTime: prev.totalWaitTime + (metrics.waiting_time || 0),
        dataPoints: prev.dataPoints + 1,
        startTime: prev.startTime || metrics.time,
      }));

      const history = JSON.parse(
        localStorage.getItem("simulationHistory") || "[]",
      );
      history.push({
        time: metrics.time,
        queue: metrics.queue_length,
        wait: metrics.waiting_time,
        vehicles: metrics.vehicle_count,
      });
      if (history.length > 100) history.shift();
      localStorage.setItem("simulationHistory", JSON.stringify(history));
      localStorage.setItem("lastRunMetrics", JSON.stringify(metrics));
    });

    return () => unsubscribe();
  }, []);

  const handleStop = async () => {
    setLoading(true);
    if (currentMetrics && stats.dataPoints > 0) {
      const finalStats = {
        ...currentMetrics,
        queue_length: stats.maxQueue,
        waiting_time: stats.totalWaitTime / stats.dataPoints,
        total_simulation_time: currentMetrics.time - stats.startTime,
      };
      localStorage.setItem("lastRunMetrics", JSON.stringify(finalStats));
    }
    await stopSimulation();
    setIsRunning(false);
    // Don't disconnect WebSocket - keep it alive for reconnection
    setLoading(false);
  };

  const handleReset = async () => {
    setLoading(true);
    await resetSimulation();
    setIsRunning(false);
    setCurrentMetrics(null);
    setStats({ maxQueue: 0, totalWaitTime: 0, dataPoints: 0, startTime: 0 });
    // Keep WebSocket connected for when user starts new simulation
    localStorage.removeItem("simulationHistory");
    localStorage.removeItem("lastRunMetrics");
    setLoading(false);
    navigate("/junctions");
  };

  const handleSwitchMode = async () => {
    const newMode = currentMode === "fixed" ? "rl" : "fixed";

    if (isRunning) {
      const confirmMsg = `This will stop the current simulation and take you back to junction selection.\n\nYou can then start a new simulation with ${newMode.toUpperCase()} mode.`;
      if (!confirm(confirmMsg)) {
        return;
      }

      setLoading(true);
      await handleStop();
      setCurrentMode(newMode);
      localStorage.setItem("selectedMode", newMode);
      setLoading(false);
      alert(`Ready to start with ${newMode.toUpperCase()} mode!`);
      navigate("/junctions");
    } else {
      setCurrentMode(newMode);
      localStorage.setItem("selectedMode", newMode);
      alert(
        `Mode changed to ${newMode.toUpperCase()}. Start a simulation to use this mode.`,
      );
    }
  };

  return (
    <div className="dashboard-container">
      <NavHeader onNewDeployment={() => navigate("/junctions")} />

      <div className="dashboard-content">
        {/* Main Panel - Digital Twin View */}
        <div className="main-panel">
          <div className="section-card" style={{ height: "100%" }}>
            <div className="section-header">
              <div>
                <div className="section-label">LIVE VISUALIZATION</div>
                <div className="section-title">DIGITAL TWIN INTERFACE</div>
              </div>
              <div
                className="system-badge"
                style={{
                  background: isConnected
                    ? "rgba(0, 255, 136, 0.1)"
                    : "rgba(255, 71, 87, 0.1)",
                  borderColor: isConnected
                    ? "var(--accent-green)"
                    : "var(--status-critical)",
                  color: isConnected
                    ? "var(--accent-green)"
                    : "var(--status-critical)",
                }}
              >
                <span
                  className="status-dot"
                  style={{
                    background: isConnected
                      ? "var(--accent-green)"
                      : "var(--status-critical)",
                  }}
                ></span>
                {isConnected ? "SYSTEM ONLINE" : "SYSTEM OFFLINE"}
              </div>
            </div>
            <div
              className="section-content"
              style={{ height: "calc(100% - 60px)", padding: 0 }}
            >
              <DigitalTwin
                queueLength={currentMetrics?.queue_length || 0}
                vehicleCount={currentMetrics?.vehicle_count || 0}
                trafficLights={currentMetrics?.traffic_lights || {}}
                locationId={
                  localStorage.getItem("lastLocation") || "silk_board"
                }
              />
            </div>
          </div>
        </div>

        {/* Side Panel - Metrics & Controls */}
        <div className="side-panel">
          {/* Real-time Metrics */}
          <div className="section-card">
            <div className="section-header">
              <div className="section-label">
                REAL-TIME METRICS
                {isConnected && (
                  <span
                    style={{
                      marginLeft: "8px",
                      color: "var(--accent-green)",
                      fontSize: "0.6rem",
                      animation: "pulse 2s infinite",
                    }}
                  >
                    ● LIVE
                  </span>
                )}
              </div>
            </div>
            <div className="section-content">
              {!isConnected && (
                <div
                  style={{
                    padding: "20px",
                    textAlign: "center",
                    color: "var(--text-muted)",
                    fontSize: "0.8rem",
                    background: "rgba(255, 71, 87, 0.05)",
                    borderRadius: "8px",
                    border: "1px solid rgba(255, 71, 87, 0.2)",
                    marginBottom: "12px",
                  }}
                >
                  <div style={{ fontSize: "1.5rem", marginBottom: "8px" }}>
                    🔌
                  </div>
                  <div>Waiting for connection...</div>
                  <div
                    style={{
                      fontSize: "0.7rem",
                      marginTop: "4px",
                      opacity: 0.6,
                    }}
                  >
                    {isRunning
                      ? "Reconnecting to simulation..."
                      : "Start a simulation to begin"}
                  </div>
                </div>
              )}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                  opacity: isConnected ? 1 : 0.5,
                }}
              >
                <MetricCard
                  label="ACTIVE VEHICLES"
                  value={currentMetrics?.vehicle_count || 0}
                  icon="🚗"
                  color="var(--accent-cyan)"
                />
                <MetricCard
                  label="AVG WAIT TIME"
                  value={`${(currentMetrics?.waiting_time || 0).toFixed(1)}s`}
                  icon="⏱️"
                  color={
                    (currentMetrics?.waiting_time || 0) > 60
                      ? "var(--status-critical)"
                      : "var(--accent-green)"
                  }
                />
                <MetricCard
                  label="QUEUE LENGTH"
                  value={currentMetrics?.queue_length || 0}
                  icon="📏"
                  color="var(--accent-pink)"
                />
                <MetricCard
                  label="THROUGHPUT"
                  value={currentMetrics?.arrived_vehicles || 0}
                  icon="✅"
                  color="var(--accent-yellow)"
                  suffix="veh"
                />
              </div>
            </div>
          </div>

          {/* Congestion Level */}
          <div className="section-card">
            <div className="section-header">
              <div className="section-label">CONGESTION LEVEL</div>
            </div>
            <div className="section-content">
              <div
                style={{
                  marginBottom: "8px",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.75rem",
                    color: "var(--text-secondary)",
                  }}
                >
                  Current Load
                </span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.75rem",
                    color: "var(--accent-cyan)",
                  }}
                >
                  {(currentMetrics?.vehicle_count || 0) > 400
                    ? "HEAVY"
                    : "MODERATE"}
                </span>
              </div>
              <div
                style={{
                  height: "8px",
                  background: "var(--bg-tertiary)",
                  borderRadius: "4px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${Math.min(((currentMetrics?.vehicle_count || 0) / 1000) * 100, 100)}%`,
                    background:
                      "linear-gradient(90deg, var(--accent-cyan), var(--accent-purple))",
                    transition: "width 0.5s",
                  }}
                ></div>
              </div>
            </div>
          </div>

          {/* Agent Status */}
          <div className="section-card">
            <div className="section-header">
              <div className="section-label">AGENT STATUS</div>
            </div>
            <div className="section-content">
              <div
                style={{ display: "flex", alignItems: "center", gap: "10px" }}
              >
                <div
                  style={{
                    width: "10px",
                    height: "10px",
                    borderRadius: "50%",
                    background:
                      currentMode === "rl"
                        ? "var(--accent-green)"
                        : "var(--text-muted)",
                    boxShadow:
                      currentMode === "rl" ? "var(--glow-green)" : "none",
                  }}
                ></div>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.85rem",
                    color:
                      currentMode === "rl"
                        ? "var(--accent-green)"
                        : "var(--text-muted)",
                  }}
                >
                  {currentMode === "rl"
                    ? "RL Agent Optimizing..."
                    : "Fixed Timer Active"}
                </span>
              </div>
              <div
                style={{
                  marginTop: "12px",
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.75rem",
                  color: "var(--text-muted)",
                }}
              >
                MODE:{" "}
                <span style={{ color: "var(--accent-cyan)" }}>
                  {currentMode === "fixed" ? "FIXED-TIME" : "RL-AGENT (AI)"}
                </span>
              </div>
              {currentMetrics && (
                <div
                  style={{
                    marginTop: "8px",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.75rem",
                    color: "var(--text-muted)",
                  }}
                >
                  SIM TIME:{" "}
                  <span style={{ color: "var(--text-primary)" }}>
                    {Math.round(currentMetrics.time)}s
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Control Buttons */}
          <div className="control-buttons" style={{ marginTop: "auto" }}>
            {!isRunning ? (
              <button
                className="control-btn start"
                onClick={() => navigate("/junctions")}
                disabled={loading}
              >
                ▶ START
              </button>
            ) : (
              <button
                className="control-btn stop"
                onClick={handleStop}
                disabled={loading}
              >
                ⏹ STOP
              </button>
            )}
            <button
              className="control-btn reset"
              onClick={handleReset}
              disabled={loading}
            >
              🔄 RESET
            </button>
          </div>
          <button
            className="control-btn switch"
            onClick={handleSwitchMode}
            style={{ width: "100%" }}
            title={
              isRunning
                ? "Stop current simulation and restart with different mode"
                : "Change mode for next simulation"
            }
          >
            {isRunning ? "🔄 RESTART WITH" : "⚡ SWITCH TO"}{" "}
            {currentMode === "fixed" ? "RL" : "FIXED"}
          </button>
        </div>
      </div>

      <StatusBar
        isConnected={isConnected}
        engineStatus={
          isConnected ? (isRunning ? "RUNNING" : "READY") : "OFFLINE"
        }
        load={isRunning ? "ACTIVE" : "STANDBY"}
      />
    </div>
  );
};

// Metric Card Component
const MetricCard = ({ label, value, icon, color, suffix }: any) => (
  <div
    style={{
      background: "var(--bg-tertiary)",
      padding: "16px",
      borderRadius: "8px",
      border: "1px solid var(--border-color)",
      position: "relative",
      overflow: "hidden",
    }}
  >
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "3px",
        height: "100%",
        background: color,
      }}
    ></div>
    <div style={{ fontSize: "1.2rem", marginBottom: "8px" }}>{icon}</div>
    <div
      style={{
        fontFamily: "var(--font-display)",
        fontSize: "1.5rem",
        fontWeight: 700,
        color: "var(--text-primary)",
        marginBottom: "4px",
      }}
    >
      {value}
      {suffix && (
        <span
          style={{
            fontSize: "0.7rem",
            color: "var(--text-muted)",
            marginLeft: "4px",
          }}
        >
          {suffix}
        </span>
      )}
    </div>
    <div
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "0.65rem",
        color: "var(--text-muted)",
        letterSpacing: "0.1em",
        textTransform: "uppercase",
      }}
    >
      {label}
    </div>
  </div>
);
