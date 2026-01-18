/**
 * Dual WebSocket Service
 * Real-time data streaming from BOTH simulations (Fixed + RL)
 */

const DUAL_WS_URL =
  import.meta.env.VITE_WS_URL?.replace("/ws", "/ws/dual") ||
  "ws://localhost:8000/ws/dual";

export interface DualSimulationMetrics {
  fixed: {
    time: number;
    queue_length: number;
    waiting_time: number;
    total_waiting_time: number;
    vehicle_count: number;
    departed_vehicles: number;
    arrived_vehicles: number;
    traffic_lights: Record<string, { phase: number; state: string }>;
  };
  rl: {
    time: number;
    queue_length: number;
    waiting_time: number;
    total_waiting_time: number;
    vehicle_count: number;
    departed_vehicles: number;
    arrived_vehicles: number;
    traffic_lights: Record<string, { phase: number; state: string }>;
  };
  step: number;
  comparison: {
    wait_time_diff: number; // Negative means RL is faster
    queue_diff: number; // Negative means RL has fewer vehicles queued
    throughput_diff: number; // Positive means RL processed more
  };
}

type DualMessageHandler = (data: DualSimulationMetrics) => void;

class DualWebSocketService {
  private ws: WebSocket | null = null;
  private messageHandlers: Set<DualMessageHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 2000;
  private isConnecting = false;
  private shouldStayConnected = false;
  private heartbeatInterval: number | null = null;

  /**
   * Connect to Dual WebSocket server
   */
  connect(): void {
    this.shouldStayConnected = true;
    this.reconnectAttempts = 0;

    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log("Dual WebSocket already connected");
      return;
    }

    if (this.isConnecting) {
      console.log("Dual WebSocket connection already in progress");
      return;
    }

    this.isConnecting = true;
    console.log("Connecting to Dual WebSocket:", DUAL_WS_URL);

    try {
      this.ws = new WebSocket(DUAL_WS_URL);

      this.ws.onopen = () => {
        console.log("✅ Dual WebSocket connected");
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const data: DualSimulationMetrics = JSON.parse(event.data);

          // Notify all registered handlers
          this.messageHandlers.forEach((handler) => {
            handler(data);
          });
        } catch (error) {
          console.error("Error parsing Dual WebSocket message:", error);
        }
      };

      this.ws.onerror = (error) => {
        console.error("Dual WebSocket error:", error);
        this.isConnecting = false;
      };

      this.ws.onclose = () => {
        console.log("Dual WebSocket disconnected");
        this.isConnecting = false;
        this.stopHeartbeat();

        if (this.shouldStayConnected) {
          this.attemptReconnect();
        }
      };
    } catch (error) {
      console.error("Error creating Dual WebSocket:", error);
      this.isConnecting = false;
    }
  }

  /**
   * Disconnect from Dual WebSocket server
   */
  disconnect(): void {
    this.shouldStayConnected = false;

    if (this.ws) {
      this.stopHeartbeat();
      this.ws.close();
      this.ws = null;
    }
    this.reconnectAttempts = 0;
    this.isConnecting = false;
  }

  /**
   * Subscribe to dual messages
   */
  subscribe(handler: DualMessageHandler): () => void {
    this.messageHandlers.add(handler);

    // Return unsubscribe function
    return () => {
      this.messageHandlers.delete(handler);
    };
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 30000); // Every 30 seconds
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * Attempt to reconnect
   */
  private attemptReconnect(): void {
    if (!this.shouldStayConnected) {
      console.log("Dual reconnection disabled");
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log("Max dual reconnection attempts reached. Retrying in 10s...");
      setTimeout(() => {
        if (this.shouldStayConnected) {
          this.reconnectAttempts = 0;
          this.connect();
        }
      }, 10000);
      return;
    }

    this.reconnectAttempts++;
    console.log(
      `Attempting dual reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`,
    );

    setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);
  }
}

// Export singleton instance
export const dualWsService = new DualWebSocketService();
