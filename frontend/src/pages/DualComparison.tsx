import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { NavHeader } from "../components/NavHeader";
import { dualWsService, DualSimulationMetrics } from "../services/dualSocket";
import { stopDualSimulation, getDualSimulationStatus } from "../services/api";
import "../App.css";

export const DualComparison: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isConnected, setIsConnected] = useState(false);
  const [currentMetrics, setCurrentMetrics] =
    useState<DualSimulationMetrics | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        const status = await getDualSimulationStatus();

        // Connect to dual WebSocket
        dualWsService.connect();

        // Poll connection status
        const connectionCheckInterval = setInterval(() => {
          setIsConnected(dualWsService.isConnected());
        }, 2000);

        return () => clearInterval(connectionCheckInterval);
      } catch (e) {
        console.error("Failed to initialize dual comparison:", e);
      }
    };
    init();

    const unsubscribe = dualWsService.subscribe(
      (metrics: DualSimulationMetrics) => {
        setIsConnected(true);
        setCurrentMetrics(metrics);
      },
    );

    return () => {
      unsubscribe();
      dualWsService.disconnect();
    };
  }, []);

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopDualSimulation();
      navigate("/junctions");
    } catch (error) {
      console.error("Failed to stop dual simulation:", error);
      alert("Failed to stop simulation");
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="dashboard-container">
      <NavHeader onNewDeployment={() => navigate("/junctions")} />

      <div style={{ padding: "20px", color: "white" }}>
        {/* Header */}
        <div
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            padding: "20px",
            borderRadius: "12px",
            marginBottom: "20px",
            border: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <h1 style={{ margin: 0, fontSize: "2rem", marginBottom: "8px" }}>
            ⚔️ Dual Simulation Comparison
          </h1>
          <p
            style={{
              margin: 0,
              color: "var(--text-muted)",
              fontSize: "0.9rem",
            }}
          >
            Fixed Time Control vs. RL Agent - Real-time Side-by-Side Comparison
          </p>
          <div
            style={{
              marginTop: "12px",
              display: "flex",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <div
              style={{
                background: isConnected
                  ? "rgba(0, 255, 136, 0.1)"
                  : "rgba(255, 71, 87, 0.1)",
                padding: "6px 12px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 600,
                color: isConnected
                  ? "var(--accent-green)"
                  : "var(--status-critical)",
                border: `1px solid ${isConnected ? "var(--accent-green)" : "var(--status-critical)"}`,
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <span
                style={{
                  width: "8px",
                  height: "8px",
                  borderRadius: "50%",
                  background: isConnected
                    ? "var(--accent-green)"
                    : "var(--status-critical)",
                  animation: isConnected ? "pulse 2s infinite" : "none",
                }}
              ></span>
              {isConnected ? "SYSTEM ONLINE" : "CONNECTING..."}
            </div>

            <button
              onClick={handleStop}
              disabled={loading}
              style={{
                padding: "8px 16px",
                background: "rgba(255, 71, 87, 0.2)",
                border: "1px solid var(--status-critical)",
                borderRadius: "6px",
                color: "var(--status-critical)",
                cursor: "pointer",
                fontSize: "0.75rem",
                fontWeight: 600,
                opacity: loading ? 0.5 : 1,
              }}
            >
              {loading ? "STOPPING..." : "STOP SIMULATION"}
            </button>
          </div>
        </div>

        {!isConnected && (
          <div
            style={{
              padding: "60px 20px",
              textAlign: "center",
              background: "rgba(255, 255, 255, 0.02)",
              borderRadius: "12px",
              border: "1px dashed rgba(255, 255, 255, 0.1)",
            }}
          >
            <div style={{ fontSize: "3rem", marginBottom: "16px" }}>🔄</div>
            <div style={{ fontSize: "1.2rem", marginBottom: "8px" }}>
              Connecting to dual simulation...
            </div>
            <div style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
              Please wait while we establish connection to both simulations
            </div>
          </div>
        )}

        {isConnected && currentMetrics && (
          <>
            {/* Comparison Summary */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "16px",
                marginBottom: "24px",
              }}
            >
              <ComparisonCard
                title="Wait Time Difference"
                value={currentMetrics.comparison.wait_time_diff.toFixed(1)}
                unit="seconds"
                improvement={currentMetrics.comparison.wait_time_diff < 0}
              />
              <ComparisonCard
                title="Queue Length Difference"
                value={currentMetrics.comparison.queue_diff.toString()}
                unit="vehicles"
                improvement={currentMetrics.comparison.queue_diff < 0}
              />
              <ComparisonCard
                title="Throughput Difference"
                value={currentMetrics.comparison.throughput_diff.toString()}
                unit="vehicles"
                improvement={currentMetrics.comparison.throughput_diff > 0}
              />
            </div>

            {/* Side by Side Comparison */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "20px",
              }}
            >
              {/* Fixed Controller */}
              <SimulationPanel
                title="FIXED TIME CONTROL"
                color="#ff6b6b"
                metrics={currentMetrics.fixed}
              />

              {/* RL Agent */}
              <SimulationPanel
                title="RL AGENT"
                color="#00e676"
                metrics={currentMetrics.rl}
              />
            </div>

            {/* Step Counter */}
            <div
              style={{
                marginTop: "20px",
                padding: "12px",
                background: "rgba(255, 255, 255, 0.02)",
                borderRadius: "8px",
                textAlign: "center",
                border: "1px solid rgba(255, 255, 255, 0.05)",
              }}
            >
              <div
                style={{
                  fontSize: "0.7rem",
                  color: "var(--text-muted)",
                  marginBottom: "4px",
                }}
              >
                SIMULATION STEP
              </div>
              <div style={{ fontSize: "1.5rem", fontWeight: 600 }}>
                {currentMetrics.step}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

interface ComparisonCardProps {
  title: string;
  value: string;
  unit: string;
  improvement: boolean;
}

const ComparisonCard: React.FC<ComparisonCardProps> = ({
  title,
  value,
  unit,
  improvement,
}) => {
  const color = improvement ? "#00e676" : "#ff6b6b";
  const icon = improvement ? "↓" : "↑";

  return (
    <div
      style={{
        background: `rgba(${improvement ? "0, 230, 118" : "255, 107, 107"}, 0.05)`,
        padding: "20px",
        borderRadius: "12px",
        border: `1px solid ${color}33`,
      }}
    >
      <div
        style={{
          fontSize: "0.7rem",
          color: "var(--text-muted)",
          marginBottom: "8px",
        }}
      >
        {title}
      </div>
      <div
        style={{
          fontSize: "2rem",
          fontWeight: 600,
          color,
          marginBottom: "4px",
        }}
      >
        {icon} {value}
      </div>
      <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
        {unit}
      </div>
    </div>
  );
};

interface SimulationPanelProps {
  title: string;
  color: string;
  metrics: {
    time: number;
    queue_length: number;
    waiting_time: number;
    vehicle_count: number;
    departed_vehicles: number;
    arrived_vehicles: number;
  };
}

const SimulationPanel: React.FC<SimulationPanelProps> = ({
  title,
  color,
  metrics,
}) => {
  return (
    <div
      style={{
        background: "rgba(255, 255, 255, 0.02)",
        borderRadius: "12px",
        overflow: "hidden",
        border: `2px solid ${color}`,
      }}
    >
      {/* Header */}
      <div
        style={{
          background: `${color}20`,
          padding: "16px",
          borderBottom: `1px solid ${color}40`,
        }}
      >
        <div
          style={{
            fontSize: "1rem",
            fontWeight: 600,
            color: color,
          }}
        >
          {title}
        </div>
      </div>

      {/* Metrics Grid */}
      <div style={{ padding: "20px" }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
          }}
        >
          <MetricBox
            label="Queue Length"
            value={metrics.queue_length.toString()}
            unit="vehicles"
          />
          <MetricBox
            label="Wait Time"
            value={metrics.waiting_time.toFixed(1)}
            unit="seconds"
          />
          <MetricBox
            label="Active Vehicles"
            value={metrics.vehicle_count.toString()}
            unit="on road"
          />
          <MetricBox
            label="Completed"
            value={metrics.departed_vehicles.toString()}
            unit="departed"
          />
        </div>

        {/* Time Display */}
        <div
          style={{
            marginTop: "16px",
            padding: "12px",
            background: "rgba(255, 255, 255, 0.02)",
            borderRadius: "8px",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: "0.7rem",
              color: "var(--text-muted)",
              marginBottom: "4px",
            }}
          >
            SIMULATION TIME
          </div>
          <div style={{ fontSize: "1.2rem", fontWeight: 600 }}>
            {Math.floor(metrics.time / 60)}:
            {(metrics.time % 60).toString().padStart(2, "0")}
          </div>
        </div>
      </div>
    </div>
  );
};

interface MetricBoxProps {
  label: string;
  value: string;
  unit: string;
}

const MetricBox: React.FC<MetricBoxProps> = ({ label, value, unit }) => {
  return (
    <div>
      <div
        style={{
          fontSize: "0.7rem",
          color: "var(--text-muted)",
          marginBottom: "4px",
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "1.5rem",
          fontWeight: 600,
          marginBottom: "2px",
        }}
      >
        {value}
      </div>
      <div
        style={{
          fontSize: "0.65rem",
          color: "var(--text-muted)",
        }}
      >
        {unit}
      </div>
    </div>
  );
};
