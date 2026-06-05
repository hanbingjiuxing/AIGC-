import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    }
});

// Request interceptor to add token
api.interceptors.request.use(config => {
    const token = localStorage.getItem('auth_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
}, error => {
    return Promise.reject(error);
});

// Response interceptor to handle errors
api.interceptors.response.use(response => {
    return response.data;
}, error => {
    if (error.response && error.response.status === 401) {
        // Token expired or invalid
        // If it's a login error (401), we should NOT redirect, but let the component handle the error
        if (!error.config.url.includes('/auth/login')) {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('user_info');
            window.location.href = '/login';
        }
    }
    return Promise.reject(error.response ? error.response.data : error);
});

const ApiService = {
    auth: {
        login: (data) => api.post('/auth/login', data),
        changePassword: (data) => api.post('/auth/change_password', data),
    },
    members: {
        list: (params) => api.get('/members', { params }),
        create: (data) => api.post('/members', data),
        update: (id, data) => api.put(`/members/${id}`, data),
        delete: (id) => api.delete(`/members/${id}`),
        resetPassword: (id) => api.post(`/members/${id}/reset_password`),
        getWorks: (id) => api.get(`/members/${id}/works`),
    },
    works: {
        list: (params) => api.get('/works', { params }),
        upload: (formData) => api.post('/works/upload', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        }),
        download: (id) => api.get(`/works/${id}/file`, { responseType: 'blob' }),
        getStats: () => api.get('/works/stats'),
    },
    attendance: {
        signin: () => api.post('/attendance/signin'),
        getHistory: () => api.get('/attendance/history'),
        getStats: () => api.get('/attendance/stats'),
        getConfig: () => api.get('/attendance/config'),
        setConfig: (data) => api.post('/attendance/config', data),
    },
    announcements: {
        list: () => api.get('/announcements'),
        create: (data) => api.post('/announcements', data),
        update: (id, data) => api.put(`/announcements/${id}`, data),
        delete: (id) => api.delete(`/announcements/${id}`),
    }
};

export default ApiService;
