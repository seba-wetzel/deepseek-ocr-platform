<script setup>
import { ref, onMounted } from 'vue';
import FileUpload from './components/FileUpload.vue';
import ResultViewer from './components/ResultViewer.vue';
import api from './services/api';

const jobs = ref([]);
const loading = ref(false);
const jobResults = ref({}); // { jobId: [results] }
const activeConnections = new Map(); // jobId -> EventSource

const fetchJobs = async () => {
    loading.value = true;
    try {
        const response = await api.getJobs();
        jobs.value = response.data;
        
        // Restore SSE for processing jobs
        jobs.value.forEach(job => {
            if (job.status === 'processing' || job.status === 'queued') {
                monitorJob(job.id);
            }
            // Optional: Fetch results for completed jobs if we want to expand them immediately
            // But better to fetch on demand or if expanded.
            // For now, let's just leave results empty until "fetched".
            // Since we don't have "onExpand" event yet properly wired for lazyload,
            // we might need to fetch results for completed jobs eagerly or add lazy logic.
            // Lets fetch results for completed jobs to correspond with previous behavior 
            // where they showed up if expanded.
            if (job.status === 'completed') {
                fetchJobResults(job.id);
            }
        });

    } catch (err) {
        console.error("Error fetching jobs:", err);
    } finally {
        loading.value = false;
    }
};

const monitorJob = (jobId) => {
    if (activeConnections.has(jobId)) return; // Already monitoring

    console.log(`[App] Starting SSE for ${jobId}`);
    const es = new EventSource(`http://localhost:8000/api/status/${jobId}/stream`);
    activeConnections.set(jobId, es);

    es.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.error) return;

            updateJobState(jobId, data.status, data.progress);

            if (data.status === 'completed') {
                es.close();
                activeConnections.delete(jobId);
                fetchJobResults(jobId);
            } else if (data.status === 'error' || data.status === 'cancelled') {
                es.close();
                activeConnections.delete(jobId);
            }
        } catch (e) {
            console.error(e);
        }
    };

    es.onerror = () => {
        // Simple error handling: close and stop monitoring
        const job = jobs.value.find(j => j.id === jobId);
        if (job && job.status === 'completed') {
            es.close();
            activeConnections.delete(jobId);
        }
    };
};

const fetchJobResults = async (jobId) => {
    try {
        const response = await api.getResult(jobId);
        jobResults.value[jobId] = response.data;
    } catch (err) {
        console.error(`Error fetching results for ${jobId}:`, err);
    }
};

const handleUploadSuccess = (jobId) => {
    console.log('Upload success:', jobId);
    const newJob = {
        id: jobId,
        status: 'queued', 
        progress: 0,
        created_at: new Date().toISOString()
    };
    jobs.value.unshift(newJob);
    monitorJob(jobId);
};

const updateJobState = (id, status, progress) => {
    const jobIndex = jobs.value.findIndex(j => j.id === id);
    if (jobIndex !== -1) {
        jobs.value[jobIndex].status = status;
        jobs.value[jobIndex].progress = progress;
    }
};

const handleCancelJob = async (jobId) => {
    try {
        await api.cancelJob(jobId);
        // Status update to 'cancelled' will come via SSE before connection closes
    } catch (err) {
        console.error("Cancel failed:", err);
    }
};

const handleDeleteJob = async (jobId) => {
    try {
        await api.deleteJob(jobId);
        // Remove locally
        jobs.value = jobs.value.filter(job => job.id !== jobId);
        delete jobResults.value[jobId];
        
        // Close connection if exists
        if (activeConnections.has(jobId)) {
            activeConnections.get(jobId).close();
            activeConnections.delete(jobId);
        }
    } catch (err) {
        console.error("Delete failed:", err);
    }
};

onMounted(() => {
    fetchJobs();
});
</script>

<template>
  <div class="app-container">
    <header class="main-header">
        <div class="logo">
            <span class="logo-icon">🔮</span>
            <h1>DeepSeek <span class="highlight">OCR</span></h1>
        </div>
        <p class="tagline">Next-Gen Local PDF Intelligence</p>
    </header>

    <main class="main-content">
        <FileUpload @upload-success="handleUploadSuccess" />
        
        <!-- Pass jobs and results to ResultViewer -->
        <ResultViewer 
            :jobs="jobs" 
            :results="jobResults"
            :loading="loading" 
            @cancel-job="handleCancelJob" 
            @delete-job="handleDeleteJob"
        />
    </main>
  </div>
</template>

<style scoped>
.app-container {
    min-height: 100vh;
    padding: 2rem;
    max-width: 900px;
    margin: 0 auto;
}

.main-header {
    text-align: center;
    margin-bottom: 3rem;
}

.logo {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.logo-icon {
    font-size: 2.5rem;
}

h1 {
    font-size: 3rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.05em;
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.highlight {
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.tagline {
    font-size: 1.25rem;
    color: #64748b;
    margin: 0;
    font-weight: 400;
}

.main-content {
    display: flex;
    flex-direction: column;
    gap: 2rem;
}
</style>
