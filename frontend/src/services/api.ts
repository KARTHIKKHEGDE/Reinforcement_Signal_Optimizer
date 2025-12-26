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
    traffic_scenario?: 'peak' | 'offpeak';
    location?: string;
}

export interface SimulationResponse {
    status: string;
    message: string;
    mode?: string;
    traffic_scenario?: string;
    location?: string;
}

export interface LocationConfig {
    name: string;
    description: string;
    real_world_stats: {
        avg_wait_time: number;
        avg_queue_length: number;
        vehicle_flow_per_hour: number;
    };
    simulation_config: any;
}

export type LocationsMap = Record<string, LocationConfig>;

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
 * Get available locations
 */
export const getLocations = async (): Promise<LocationsMap> => {
    const response = await apiClient.get<LocationsMap>('/api/simulation/locations');
    return response.data;
};

/**
 * Start simulation
 */
export const startSimulation = async (
    mode: 'fixed' | 'rl',
    useGui: boolean = true,
    trafficScenario: 'peak' | 'offpeak' = 'peak',
    location: string = 'silk_board'
): Promise<SimulationResponse> => {
    const response = await apiClient.post<SimulationResponse>('/api/simulation/start', {
        mode,
        use_gui: useGui,
        traffic_scenario: trafficScenario,
        location
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
