<script setup>
import { ref, onMounted } from 'vue';
import FileSelector from './components/FileSelector.vue';
import PromptManager from './components/PromptManager.vue';
import ResultViewer from './components/ResultViewer.vue';
import api from './services/api';

const jobs = ref([]);
const loading = ref(false);
const jobResults = ref({}); // { jobId: [results] }
const activeConnections = new Map(); // jobId -> EventSource

// New State for Selection
const selectedFile = ref(null);
const selectedPromptId = ref(null);
const prompts = ref([]); 
const isUploading = ref(false);
const uploadProgress = ref(0);
const uploadError = ref(null);

const fetchPrompts = async () => {
    try {
        const response = await api.getPrompts();
        prompts.value = response.data;
        
        // Select default if no selection
        if (!selectedPromptId.value && prompts.value.length > 0) {
            const defaultPrompt = prompts.value.find(p => p.is_default) || prompts.value[0];
            selectedPromptId.value = defaultPrompt.id;
        }
    } catch (e) {
        console.error("Failed to load prompts", e);
    }
};

const handleSavePrompt = async (promptData) => {
    try {
        let newId = promptData.id;
        if (newId) {
            await api.updatePrompt(newId, promptData);
        } else {
            const res = await api.createPrompt(promptData);
            newId = res.data.id;
        }
        await fetchPrompts();
        selectedPromptId.value = newId; 
    } catch (e) {
        alert("Error guardando prompt: " + e.message); 
    }
};

// ... fetchJobs, monitorJob, fetchJobResults ... (Keep existing helpers)

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

const updateJobState = (id, status, progress) => {
    const jobIndex = jobs.value.findIndex(j => j.id === id);
    if (jobIndex !== -1) {
        jobs.value[jobIndex].status = status;
        jobs.value[jobIndex].progress = progress;
    }
};

// Orchestration Actions
const startProcessing = async () => {
    if (!selectedFile.value) {
        uploadError.value = "Por favor selecciona un archivo.";
        return;
    }
    
    isUploading.value = true;
    uploadError.value = null;
    uploadProgress.value = 0;

    try {
        const response = await api.uploadFile(selectedFile.value, selectedPromptId.value, (event) => {
            uploadProgress.value = Math.round((event.loaded * 100) / event.total);
        });
        
        const jobId = response.data.job_id;
        
        // Add to local list immediately
        const newJob = {
            id: jobId,
            status: 'queued', 
            progress: 0,
            created_at: new Date().toISOString()
        };
        jobs.value.unshift(newJob);
        monitorJob(jobId);
        
        // Reset file selection but keep prompt
        selectedFile.value = null;
        
    } catch (err) {
        uploadError.value = "Error al procesar: " + (err.response?.data?.detail || err.message);
    } finally {
        isUploading.value = false;
    }
};

const handleCancelJob = async (jobId) => {
    try {
        await api.cancelJob(jobId);
    } catch (err) {
        console.error("Cancel failed:", err);
    }
};

const handleDeleteJob = async (jobId) => {
    try {
        await api.deleteJob(jobId);
        jobs.value = jobs.value.filter(job => job.id !== jobId);
        delete jobResults.value[jobId];
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
    fetchPrompts();
});
</script>

<template>
  <div class="app-container">
    <header class="main-header">
        <div class="logo">
            <span class="logo-icon">🔮</span>
            <h1>DeepSeek <span class="highlight">OCR</span></h1>
        </div>
        <p class="tagline">Inteligencia PDF Local de Nueva Generación</p>
    </header>

    <main class="main-content">
        <!-- New Job Creation Section -->
        <section class="creation-panel">
            <div class="panel-left">
                <FileSelector v-model="selectedFile" />
            </div>
            
            <div class="panel-right">
                <PromptManager 
                    v-model="selectedPromptId" 
                    :prompts="prompts"
                    @save-prompt="handleSavePrompt"
                />
                
                <div class="action-area">
                    <div v-if="uploadError" class="error-msg">{{ uploadError }}</div>
                    
                    <button 
                        v-if="!isUploading"
                        @click="startProcessing" 
                        class="process-btn" 
                        :disabled="!selectedFile"
                    >
                        🚀 Procesar Documento
                    </button>
                    
                    <div v-else class="upload-progress">
                        <div class="spinner"></div>
                        <span>Subiendo... {{ uploadProgress }}%</span>
                    </div>
                </div>
            </div>
        </section>

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
/* Keep existing header styles... */
.app-container {
    min-height: 100vh;
    padding: 2rem;
    max-width: 1000px; /* Increased width for side-by-side */
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
.logo-icon { font-size: 2.5rem; }
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

/* Creation Panel Styles */
.creation-panel {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    align-items: flex-start;
}

@media (max-width: 768px) {
    .creation-panel {
        grid-template-columns: 1fr;
    }
}

.action-area {
    margin-top: 1rem;
}

.process-btn {
    width: 100%;
    padding: 1rem;
    background: #6366f1;
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s, transform 0.1s;
}
.process-btn:hover:not(:disabled) {
    background: #4f46e5;
    transform: translateY(-1px);
}
.process-btn:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
    opacity: 0.8;
}

.upload-progress {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 1rem;
    background: #f1f5f9;
    border-radius: 12px;
    color: #475569;
    font-weight: 500;
}

.spinner {
    width: 20px;
    height: 20px;
    border: 2px solid #cbd5e1;
    border-top-color: #6366f1;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

.error-msg {
    color: #ef4444;
    text-align: center;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>


