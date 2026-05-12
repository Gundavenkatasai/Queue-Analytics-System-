/**
 * Axios API Client Service
 * Handles all communication with Laravel backend
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
    response => response,
    error => {
        console.error('API Error:', error.message);
        return Promise.reject(error);
    }
);

/**
 * Fetch latest statistics
 */
export const fetchStats = async () => {
    try {
        const response = await apiClient.get('/stats');
        return response.data;
    } catch (error) {
        console.error('Error fetching stats:', error);
        throw error;
    }
};

/**
 * Fetch historical data (time-series)
 */
export const fetchHistory = async () => {
    try {
        const response = await apiClient.get('/history');
        return response.data;
    } catch (error) {
        console.error('Error fetching history:', error);
        throw error;
    }
};

/**
 * Fetch statistics summary
 */
export const fetchStatsSummary = async (minutes = 60) => {
    try {
        const response = await apiClient.get('/stats-summary', {
            params: { minutes },
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching stats summary:', error);
        throw error;
    }
};

/**
 * Check API health
 */
export const checkHealth = async () => {
    try {
        const response = await apiClient.get('/health');
        return response.data;
    } catch (error) {
        console.error('API Health Check Failed:', error);
        return { status: 'error', message: 'API unreachable' };
    }
};

export default apiClient;
