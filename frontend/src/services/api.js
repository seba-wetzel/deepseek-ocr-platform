import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
    baseURL: API_URL,
});

export default {
    // Changed upload to accept prompt_id
    uploadFile(file, promptId = null, onUploadProgress) {
        let formData = new FormData();
        formData.append("file", file);
        if (promptId) {
            formData.append("prompt_id", promptId);
        }

        return axios.post(`${API_URL}/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            },
            onUploadProgress
        });
    },

    getPrompts() {
        return axios.get(`${API_URL}/prompts`);
    },

    createPrompt(data) {
        return axios.post(`${API_URL}/prompts`, data);
    },

    updatePrompt(id, data) {
        return axios.put(`${API_URL}/prompts/${id}`, data);
    },
    getStatus(jobId) {
        return api.get(`/status/${jobId}`);
    },
    getResult(jobId) {
        return api.get(`/result/${jobId}`);
    },
    async getJobs() {
        return api.get('/jobs');
    },

    async deleteJob(jobId) {
        return api.delete(`/jobs/${jobId}`);
    },

    async cancelJob(jobId) {
        return api.post(`/jobs/${jobId}/cancel`);
    },

    getExportUrl(jobId, format = 'excel') {
        const baseURL = api.defaults.baseURL;
        return `${baseURL}/export/${jobId}?format=${format}`;
    }
};
