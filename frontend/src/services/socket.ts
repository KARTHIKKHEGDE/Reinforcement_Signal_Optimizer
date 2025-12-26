/**
 * WebSocket Service
 * Real-time data streaming from backend
 */

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export interface SimulationMetrics {
    time: number;
    queue_length: number;
    waiting_time: number;
    total_waiting_time: number;
    vehicle_count: number;
    departed_vehicles: number;
    arrived_vehicles: number;
    traffic_lights: Record<string, {
        phase: number;
        state: string;
    }>;
    timestamp: number;
}

type MessageHandler = (data: SimulationMetrics) => void;

class WebSocketService {
    private ws: WebSocket | null = null;
    private messageHandlers: Set<MessageHandler> = new Set();
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 2000;
    private isConnecting = false;

    /**
     * Connect to WebSocket server
     */
    connect(): void {
        if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
            console.log('WebSocket already connected or connecting');
            return;
        }

        this.isConnecting = true;
        console.log('Connecting to WebSocket:', WS_URL);

        try {
            this.ws = new WebSocket(WS_URL);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnecting = false;
                this.reconnectAttempts = 0;

                // Send ping to keep connection alive
                this.startHeartbeat();
            };

            this.ws.onmessage = (event) => {
                try {
                    const data: SimulationMetrics = JSON.parse(event.data);

                    // Notify all registered handlers
                    this.messageHandlers.forEach(handler => {
                        handler(data);
                    });
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnecting = false;
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnecting = false;
                this.stopHeartbeat();
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Error creating WebSocket:', error);
            this.isConnecting = false;
        }
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect(): void {
        if (this.ws) {
            this.stopHeartbeat();
            this.ws.close();
            this.ws = null;
        }
        this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
    }

    /**
     * Subscribe to messages
     */
    subscribe(handler: MessageHandler): () => void {
        this.messageHandlers.add(handler);

        // Return unsubscribe function
        return () => {
            this.messageHandlers.delete(handler);
        };
    }

    /**
     * Attempt to reconnect
     */
    private attemptReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            return;
        }

        this.reconnectAttempts++;
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);

        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay);
    }

    /**
     * Heartbeat to keep connection alive
     */
    private heartbeatInterval: number | null = null;

    private startHeartbeat(): void {
        this.heartbeatInterval = window.setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 30000); // Send ping every 30 seconds
    }

    private stopHeartbeat(): void {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Get connection status
     */
    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }
}

// Export singleton instance
export const wsService = new WebSocketService();
