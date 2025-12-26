/**
 * API Service
 * HTTP client for REST API calls
 */
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface SimulationRequest {
    mode: 'fixed' | 'rl';
    use_gui: boolean;
}

export interface SimulationResponse {
    status: string;
    message: string;
    mode?: string;
}

export interface SimulationStatus {
    running: boolean;
    pid: number | null;
    traci_connected: boolean;
    active_connections: number;
    current_metrics: any;
}

export interface MetricsSummary {
    status: string;
    summary?: {
        total_vehicles: number;
        average_queue: number;
        average_waiting_time: number;
        simulation_time: number;
        throughput: {
            departed: number;
            arrived: number;
        };
    };
    message?: string;
}

/**
 * Start simulation
 */
export const startSimulation = async (
    mode: 'fixed' | 'rl',
    useGui: boolean = true
): Promise<SimulationResponse> => {
    const response = await apiClient.post<SimulationResponse>('/api/simulation/start', {
        mode,
        use_gui: useGui,
    });
    return response.data;
};

/**
 * Stop simulation
 */
export const stopSimulation = async (): Promise<SimulationResponse> => {
    const response = await apiClient.post<SimulationResponse>('/api/simulation/stop');
    return response.data;
};

/**
 * Reset simulation
 */
export const resetSimulation = async (): Promise<SimulationResponse> => {
    const response = await apiClient.post<SimulationResponse>('/api/simulation/reset');
    return response.data;
};

/**
 * Get simulation status
 */
export const getSimulationStatus = async (): Promise<SimulationStatus> => {
    const response = await apiClient.get<SimulationStatus>('/api/simulation/status');
    return response.data;
};

/**
 * Get current metrics
 */
export const getCurrentMetrics = async () => {
    const response = await apiClient.get('/api/metrics/current');
    return response.data;
};

/**
 * Get metrics summary
 */
export const getMetricsSummary = async (): Promise<MetricsSummary> => {
    const response = await apiClient.get<MetricsSummary>('/api/metrics/summary');
    return response.data;
};

export default apiClient;
