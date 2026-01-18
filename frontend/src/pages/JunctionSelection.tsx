import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  getLocations,
  startSimulation,
  startDualSimulation,
  getAvailableHours,
  LocationsMap,
  HourData,
  previewDemand,
} from "../services/api";
import { wsService } from "../services/socket";

interface JunctionData {
  id: string;
  code: string;
  name: string;
  lanes: number;
  conflictPts: number;
  flowRate: string;
  load: "critical" | "high" | "moderate";
  description: string;
}

const junctionDefaults: Record<string, Partial<JunctionData>> = {
  silk_board: {
    code: "BLR-SB-01",
    lanes: 48,
    conflictPts: 12,
    flowRate: "12k v/h",
    load: "critical",
    description: "Primary arterial intersection. High latency expected.",
  },
  tin_factory: {
    code: "BLR-TF-02",
    lanes: 36,
    conflictPts: 8,
    flowRate: "10.5k v/h",
    load: "high",
    description: "Complex multi-modal convergence zone.",
  },
  hebbal: {
    code: "BLR-HF-03",
    lanes: 42,
    conflictPts: 6,
    flowRate: "11k v/h",
    load: "high",
    description: "Major flyover junction with high-speed lanes.",
  },
  kr_puram: {
    code: "BLR-KP-04",
    lanes: 32,
    conflictPts: 14,
    flowRate: "9.5k v/h",
    load: "moderate",
    description: "Eastern corridor hub with railway crossing.",
  },
};

export const JunctionSelection: React.FC = () => {
  const navigate = useNavigate();
  const [locations, setLocations] = useState<LocationsMap>({});
  const [selectedLocation, setSelectedLocation] =
    useState<string>("silk_board");
  const [loading, setLoading] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [simulationMode, setSimulationMode] = useState<"single" | "dual">(
    "dual",
  );
  const [controllerMode, setControllerMode] = useState<"fixed" | "rl">(
    (localStorage.getItem("selectedMode") as "fixed" | "rl") || "fixed",
  );
  const [availableHours, setAvailableHours] = useState<HourData[]>([]);

  // Time window state (REQUIRED for dual simulation)
  const [startHour, setStartHour] = useState<number>(8);
  const [startMinute, setStartMinute] = useState<number>(0);
  const [endHour, setHourEnd] = useState<number>(9);
  const [endMinute, setMinuteEnd] = useState<number>(0);

  // Demand preview (shows exact vehicle count from CSV)
  const [demandPreview, setDemandPreview] = useState<{
    total_vehicles: number;
    duration_minutes: number;
    by_direction: { north: number; south: number; east: number; west: number };
  } | null>(null);

  useEffect(() => {
    loadLocations();
  }, []);

  // Load hours when location changes
  useEffect(() => {
    if (selectedLocation && simulationMode === "dual") {
      loadHoursForLocation(selectedLocation);
    }
  }, [selectedLocation, simulationMode]);

  // Update demand preview when parameters change
  useEffect(() => {
    if (simulationMode === "dual" && selectedLocation) {
      updateDemandPreviewUI();
    }
  }, [
    selectedLocation,
    startHour,
    startMinute,
    endHour,
    endMinute,
    simulationMode,
  ]);

  const loadLocations = async () => {
    try {
      const data = await getLocations();
      setLocations(data);
      setIsConnected(true);
      if (Object.keys(data).length > 0) {
        // Keep current selection if valid, otherwise first one
        if (!Object.keys(data).includes(selectedLocation)) {
          setSelectedLocation(Object.keys(data)[0]);
        }
      }
    } catch (err) {
      console.error("Failed to load locations", err);
      setIsConnected(false);
    }
  };

  const loadHoursForLocation = async (location: string) => {
    try {
      const data = await getAvailableHours(location);
      setAvailableHours(data.hours || []);
      // Default to first Peak hour found
      const peakHour = data.hours?.find(
        (h) => h.intensity === "critical" || h.intensity === "high",
      );
      if (peakHour) {
        setStartHour(peakHour.hour);
        setHourEnd(peakHour.hour + 1);
      }
    } catch (err) {
      console.error("Failed to load hours", err);
      setAvailableHours([]);
    }
  };

  const updateDemandPreviewUI = async () => {
    try {
      const result = await previewDemand(selectedLocation, {
        start_hour: startHour,
        start_minute: startMinute,
        end_hour: endHour,
        end_minute: endMinute,
      });
      setDemandPreview(result.demand);
    } catch (err) {
      console.error("Failed to preview demand", err);
      setDemandPreview(null);
    }
  };

  const handleStart = async () => {
    setLoading(true);
    try {
      localStorage.setItem("lastLocation", selectedLocation);
      localStorage.setItem("selectedMode", controllerMode);

      if (simulationMode === "dual") {
        const timeWindow = {
          start_hour: startHour,
          start_minute: startMinute,
          end_hour: endHour,
          end_minute: endMinute,
        };
        await startDualSimulation(selectedLocation, timeWindow, true, 42);

        // Navigate to dual comparison page
        navigate("/dual");
      } else {
        // Use the selected controller mode (fixed or rl)
        await startSimulation(controllerMode, true, "peak", selectedLocation);

        // Ensure WebSocket is connected before navigating
        wsService.connect();
        navigate("/dashboard");
      }
    } catch (err) {
      console.error("Failed to start", err);
      alert("Failed to start simulation. Check backend logs.");
    } finally {
      setLoading(false);
    }
  };

  const handleJunctionClick = (key: string) => {
    setSelectedLocation(key);
  };

  const getJunctionData = (key: string, loc: any): JunctionData => {
    const defaults = junctionDefaults[key] || junctionDefaults.silk_board;
    return {
      id: key,
      code: defaults.code || "BLR-XX-00",
      name:
        loc?.name?.toUpperCase().replace(/ /g, "_") ||
        key.toUpperCase().replace(/ /g, "_"),
      lanes: defaults.lanes || 24,
      conflictPts: defaults.conflictPts || 8,
      flowRate: defaults.flowRate || "8k v/h",
      load: defaults.load || "moderate",
      description:
        loc?.description || defaults.description || "Traffic intersection.",
    };
  };

  return (
    <div
      className="junction-page"
      style={{
        padding: "40px",
        color: "white",
        minHeight: "100vh",
        position: "relative",
      }}
    >
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: "40px" }}>
        <div
          className="page-breadcrumb"
          onClick={() => navigate("/")}
          style={{
            cursor: "pointer",
            opacity: 0.6,
            fontSize: "0.8rem",
            marginBottom: "8px",
          }}
        >
          ← EXIT_SELECTION
        </div>
        <div
          className="page-label"
          style={{
            color: "var(--accent-cyan)",
            fontSize: "0.7rem",
            fontWeight: 600,
            letterSpacing: "2px",
          }}
        >
          SYSTEM CONFIGURATION
        </div>
        <h1
          className="page-title"
          style={{ fontSize: "2rem", margin: "10px 0", fontFamily: "Orbitron" }}
        >
          SELECT NETWORK TOPOLOGY
        </h1>
      </div>

      {/* Junction Grid */}
      <div
        className="junction-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(350px, 1fr))",
          gap: "24px",
          marginBottom: "100px",
        }}
      >
        {Object.entries(locations).map(([key, loc]) => {
          const junction = getJunctionData(key, loc);
          const isSelected = selectedLocation === key;

          return (
            <div
              key={key}
              className={`junction-card ${isSelected ? "selected" : ""}`}
              onClick={() => handleJunctionClick(key)}
              style={{
                background: isSelected
                  ? "rgba(0, 229, 255, 0.05)"
                  : "var(--bg-card)",
                border: isSelected
                  ? "1px solid var(--accent-cyan)"
                  : "1px solid var(--border-color)",
                padding: "24px",
                borderRadius: "12px",
                cursor: "pointer",
                transition: "all 0.3s ease",
                position: "relative",
                boxShadow: isSelected
                  ? "0 0 20px rgba(0, 229, 255, 0.1)"
                  : "none",
              }}
            >
              <div
                className="junction-header"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: "20px",
                }}
              >
                <div>
                  <div
                    className="junction-id"
                    style={{
                      fontSize: "0.7rem",
                      color: "var(--text-muted)",
                      marginBottom: "4px",
                    }}
                  >
                    {junction.code}
                  </div>
                  <div
                    className="junction-name"
                    style={{
                      fontSize: "1.2rem",
                      fontWeight: "bold",
                      fontFamily: "Orbitron",
                    }}
                  >
                    {junction.name}
                  </div>
                </div>
                <div
                  className={`load-badge ${junction.load}`}
                  style={{
                    padding: "4px 10px",
                    borderRadius: "4px",
                    fontSize: "0.65rem",
                    fontWeight: "bold",
                    background:
                      junction.load === "critical"
                        ? "rgba(255, 61, 0, 0.1)"
                        : "rgba(0, 255, 157, 0.1)",
                    color: junction.load === "critical" ? "#ff3d00" : "#00ff9d",
                    border: `1px solid ${junction.load === "critical" ? "#ff3d0044" : "#00ff9d44"}`,
                  }}
                >
                  LOAD: {junction.load.toUpperCase()}
                </div>
              </div>

              <div
                className="junction-stats"
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: "12px",
                  marginBottom: "20px",
                }}
              >
                <div className="stat-item">
                  <div
                    className="stat-label"
                    style={{ fontSize: "0.6rem", color: "var(--text-muted)" }}
                  >
                    LANES
                  </div>
                  <div
                    className="stat-value"
                    style={{ fontSize: "1rem", fontWeight: 600 }}
                  >
                    {junction.lanes}
                  </div>
                </div>
                <div className="stat-item">
                  <div
                    className="stat-label"
                    style={{ fontSize: "0.6rem", color: "var(--text-muted)" }}
                  >
                    CONFLICT PTS
                  </div>
                  <div
                    className="stat-value"
                    style={{ fontSize: "1rem", fontWeight: 600 }}
                  >
                    {junction.conflictPts}
                  </div>
                </div>
                <div className="stat-item">
                  <div
                    className="stat-label"
                    style={{ fontSize: "0.6rem", color: "var(--text-muted)" }}
                  >
                    FLOW RATE
                  </div>
                  <div
                    className="stat-value flow"
                    style={{
                      fontSize: "1rem",
                      fontWeight: 600,
                      color: "var(--accent-cyan)",
                    }}
                  >
                    {junction.flowRate}
                  </div>
                </div>
              </div>

              <div
                className="junction-description"
                style={{
                  fontSize: "0.85rem",
                  color: "var(--text-secondary)",
                  lineHeight: 1.5,
                }}
              >
                {junction.description}
              </div>
            </div>
          );
        })}
      </div>

      {/* Float Controls */}
      {selectedLocation && (
        <div
          style={{
            position: "fixed",
            bottom: "40px",
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 100,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "20px",
            width: "100%",
            maxWidth: "500px",
          }}
        >
          {/* Control Panel */}
          <div
            style={{
              background: "rgba(10, 15, 20, 0.95)",
              backdropFilter: "blur(10px)",
              padding: "20px",
              borderRadius: "16px",
              border: "1px solid var(--border-color)",
              width: "100%",
              boxShadow: "0 20px 40px rgba(0,0,0,0.5)",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            {/* Mode Selector */}
            <div
              style={{
                display: "flex",
                gap: "8px",
                padding: "4px",
                background: "rgba(255,255,255,0.05)",
                borderRadius: "10px",
              }}
            >
              <button
                onClick={() => setSimulationMode("dual")}
                style={{
                  flex: 1,
                  padding: "10px",
                  border: "none",
                  borderRadius: "8px",
                  background:
                    simulationMode === "dual"
                      ? "var(--accent-cyan)"
                      : "transparent",
                  color: simulationMode === "dual" ? "black" : "white",
                  cursor: "pointer",
                  fontWeight: "bold",
                  fontSize: "0.75rem",
                  transition: "all 0.2s",
                }}
              >
                ⚔️ DUAL COMPARISON
              </button>
              <button
                onClick={() => setSimulationMode("single")}
                style={{
                  flex: 1,
                  padding: "10px",
                  border: "none",
                  borderRadius: "8px",
                  background:
                    simulationMode === "single"
                      ? "var(--accent-cyan)"
                      : "transparent",
                  color: simulationMode === "single" ? "black" : "white",
                  cursor: "pointer",
                  fontWeight: "bold",
                  fontSize: "0.75rem",
                  transition: "all 0.2s",
                }}
              >
                🚦 SINGLE MODE
              </button>
            </div>

            {/* Single Mode Controller Selector */}
            {simulationMode === "single" && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  padding: "12px",
                  background: "rgba(255,255,255,0.03)",
                  borderRadius: "12px",
                  border: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--accent-cyan)",
                    fontWeight: "bold",
                  }}
                >
                  🤖 SELECT CONTROLLER
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={() => setControllerMode("fixed")}
                    style={{
                      flex: 1,
                      padding: "12px",
                      border: `2px solid ${controllerMode === "fixed" ? "var(--accent-yellow)" : "rgba(255,255,255,0.1)"}`,
                      borderRadius: "8px",
                      background:
                        controllerMode === "fixed"
                          ? "rgba(255, 193, 7, 0.1)"
                          : "transparent",
                      color:
                        controllerMode === "fixed"
                          ? "var(--accent-yellow)"
                          : "rgba(255,255,255,0.5)",
                      cursor: "pointer",
                      fontWeight: "bold",
                      fontSize: "0.7rem",
                      transition: "all 0.2s",
                      textAlign: "center",
                    }}
                  >
                    ⏱️ FIXED-TIME
                  </button>
                  <button
                    onClick={() => setControllerMode("rl")}
                    style={{
                      flex: 1,
                      padding: "12px",
                      border: `2px solid ${controllerMode === "rl" ? "var(--accent-green)" : "rgba(255,255,255,0.1)"}`,
                      borderRadius: "8px",
                      background:
                        controllerMode === "rl"
                          ? "rgba(0, 255, 136, 0.1)"
                          : "transparent",
                      color:
                        controllerMode === "rl"
                          ? "var(--accent-green)"
                          : "rgba(255,255,255,0.5)",
                      cursor: "pointer",
                      fontWeight: "bold",
                      fontSize: "0.7rem",
                      transition: "all 0.2s",
                      textAlign: "center",
                    }}
                  >
                    🤖 RL AGENT
                  </button>
                </div>
                <div
                  style={{
                    fontSize: "0.65rem",
                    color: "var(--text-muted)",
                    textAlign: "center",
                    padding: "8px",
                    background: "rgba(0,0,0,0.3)",
                    borderRadius: "6px",
                  }}
                >
                  {controllerMode === "fixed"
                    ? "⚙️ Traditional timer-based control"
                    : "🧠 AI-powered adaptive control"}
                </div>
              </div>
            )}

            {/* Dual Mode Specific Controls */}
            {simulationMode === "dual" && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  padding: "12px",
                  background: "rgba(255,255,255,0.03)",
                  borderRadius: "12px",
                  border: "1px solid rgba(255,255,255,0.05)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.7rem",
                    color: "var(--accent-cyan)",
                    fontWeight: "bold",
                  }}
                >
                  ⏱️ SIMULATION TIME WINDOW (CSV DATA)
                </div>

                <div
                  style={{ display: "flex", gap: "10px", alignItems: "center" }}
                >
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontSize: "0.6rem",
                        color: "var(--text-muted)",
                        marginBottom: "4px",
                      }}
                    >
                      START
                    </div>
                    <div style={{ display: "flex", gap: "4px" }}>
                      <input
                        type="number"
                        value={startHour}
                        min={0}
                        max={23}
                        onChange={(e) => setStartHour(parseInt(e.target.value))}
                        style={{
                          width: "45px",
                          background: "#000",
                          border: "1px solid #333",
                          color: "#fff",
                          textAlign: "center",
                          borderRadius: "4px",
                        }}
                      />
                      <span style={{ color: "#444" }}>:</span>
                      <input
                        type="number"
                        value={startMinute}
                        min={0}
                        max={59}
                        onChange={(e) =>
                          setStartMinute(parseInt(e.target.value))
                        }
                        style={{
                          width: "45px",
                          background: "#000",
                          border: "1px solid #333",
                          color: "#fff",
                          textAlign: "center",
                          borderRadius: "4px",
                        }}
                      />
                    </div>
                  </div>
                  <div style={{ color: "#444" }}>→</div>
                  <div style={{ flex: 1 }}>
                    <div
                      style={{
                        fontSize: "0.6rem",
                        color: "var(--text-muted)",
                        marginBottom: "4px",
                      }}
                    >
                      END
                    </div>
                    <div style={{ display: "flex", gap: "4px" }}>
                      <input
                        type="number"
                        value={endHour}
                        min={0}
                        max={23}
                        onChange={(e) => setHourEnd(parseInt(e.target.value))}
                        style={{
                          width: "45px",
                          background: "#000",
                          border: "1px solid #333",
                          color: "#fff",
                          textAlign: "center",
                          borderRadius: "4px",
                        }}
                      />
                      <span style={{ color: "#444" }}>:</span>
                      <input
                        type="number"
                        value={endMinute}
                        min={0}
                        max={59}
                        onChange={(e) => setMinuteEnd(parseInt(e.target.value))}
                        style={{
                          width: "45px",
                          background: "#000",
                          border: "1px solid #333",
                          color: "#fff",
                          textAlign: "center",
                          borderRadius: "4px",
                        }}
                      />
                    </div>
                  </div>
                </div>

                {demandPreview && (
                  <div
                    style={{
                      padding: "8px",
                      background: "rgba(0, 255, 157, 0.05)",
                      borderRadius: "8px",
                      fontSize: "0.7rem",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                      }}
                    >
                      <span style={{ color: "var(--text-muted)" }}>
                        Expected Vehicles:
                      </span>
                      <span
                        style={{
                          color: "var(--accent-green)",
                          fontWeight: "bold",
                        }}
                      >
                        {demandPreview.total_vehicles}
                      </span>
                    </div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginTop: "2px",
                      }}
                    >
                      <span style={{ color: "var(--text-muted)" }}>
                        Duration:
                      </span>
                      <span>{demandPreview.duration_minutes} min</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Action Button */}
            <button
              onClick={handleStart}
              disabled={loading}
              style={{
                width: "100%",
                padding: "14px",
                background: loading
                  ? "rgba(0, 229, 255, 0.3)"
                  : "var(--accent-cyan)",
                color: "black",
                border: "none",
                borderRadius: "10px",
                fontWeight: "bold",
                fontFamily: "Orbitron",
                cursor: loading ? "not-allowed" : "pointer",
                transition: "all 0.3s",
              }}
            >
              {loading ? "INITIALIZING ENGINE..." : "LAUNCH SIMULATION →"}
            </button>
          </div>

          {/* Status Info */}
          <div
            style={{
              display: "flex",
              gap: "20px",
              fontSize: "0.65rem",
              color: "var(--text-muted)",
            }}
          >
            <div>
              CONNECTION:{" "}
              <span
                style={{ color: isConnected ? "var(--accent-green)" : "red" }}
              >
                {isConnected ? "STABLE" : "OFFLINE"}
              </span>
            </div>
            <div>
              SIGNAL SYNC: <span style={{ color: "white" }}>ACTIVE</span>
            </div>
            <div>
              DATA SOURCE: <span style={{ color: "white" }}>CSV_REALTIME</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
