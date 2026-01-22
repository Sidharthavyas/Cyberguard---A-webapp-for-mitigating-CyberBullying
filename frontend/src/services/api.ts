/**
 * Axios HTTP client configuration with auth headers.
 */

import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
    baseURL: API_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json'
    }
});

// Add auth token to requests if available
api.interceptors.request.use(
    (config: any) => {
        const token = localStorage.getItem('twitter_access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error: any) => {
        return Promise.reject(error);
    }
);

// Handle response errors
api.interceptors.response.use(
    (response: any) => response,
    (error: any) => {
        if (error.response?.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('twitter_access_token');
            localStorage.removeItem('twitter_user_id');
            localStorage.removeItem('twitter_username');
            window.location.href = '/';
        }
        return Promise.reject(error);
    }
);

// API endpoints
export const authAPI = {
    login: () => {
        window.location.href = `${API_URL}/auth/twitter/login`;
    },
    logout: async (userId: string) => {
        const response = await api.post(`/auth/logout/${userId}`);
        return response.data;
    }
};

export const statsAPI = {
    getStats: async () => {
        const response = await api.get('/stats');
        return response.data;
    }
};
