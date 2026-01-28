import axios from 'axios';

const api = axios.create({
    baseURL: 'http://127.0.0.1:8000/api',
});

export default {
    uploadFile(file, onUploadProgress) {
        const formData = new FormData();
        formData.append('file', file);

        return api.post('/upload', formData, {
            onUploadProgress,
        });
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
