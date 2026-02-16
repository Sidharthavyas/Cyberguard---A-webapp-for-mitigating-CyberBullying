/**
 * Axios HTTP client configuration with auth headers.
 */

import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
    baseURL: API_URL,
    timeout: 30000,  // 30s to handle HF Spaces cold starts
    headers: {
        'Content-Type': 'application/json'
    }
});

// Add auth token to requests if available (check all platforms)
api.interceptors.request.use(
    (config: any) => {
        const token = localStorage.getItem('twitter_access_token') || localStorage.getItem('discord_access_token');
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
            // Token expired or invalid - clear all platform keys
            localStorage.removeItem('twitter_access_token');
            localStorage.removeItem('twitter_user_id');
            localStorage.removeItem('twitter_username');
            localStorage.removeItem('discord_access_token');
            localStorage.removeItem('discord_user_id');
            localStorage.removeItem('discord_username');
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

export const analyticsAPI = {
    getSummary: async () => {
        const response = await api.get('/analytics/summary');
        return response.data;
    }
};

export const settingsAPI = {
    getSettings: async (userId: string) => {
        const response = await api.get(`/settings/${userId}`);
        return response.data;
    },
    updateSettings: async (userId: string, payload: any) => {
        const response = await api.post(`/settings/${userId}`, payload);
        return response.data;
    }
};

export const historyAPI = {
    getEvents: async (platform: string = 'all', limit: number = 50, skip: number = 0, action?: string) => {
        const params: any = { platform, limit, skip };
        if (action) params.action = action;
        const response = await api.get('/history', { params });
        return response.data;
    },
    getMessages: async (platform: string = 'all', limit: number = 50, skip: number = 0) => {
        const response = await api.get('/messages', { params: { platform, limit, skip } });
        return response.data;
    },
    getStats: async () => {
        const response = await api.get('/history/stats');
        return response.data;
    }
};