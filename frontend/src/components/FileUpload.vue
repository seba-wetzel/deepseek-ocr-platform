<script setup>
import { ref } from 'vue';
import api from '../services/api';

const emit = defineEmits(['upload-success']);

const isDragging = ref(false);
const isUploading = ref(false);
const progress = ref(0);
const error = ref(null);

const handleDrop = (e) => {
    isDragging.value = false;
    const files = e.dataTransfer.files;
    if (files.length) uploadFile(files[0]);
};

const handleFileSelect = (e) => {
    const files = e.target.files;
    if (files.length) uploadFile(files[0]);
};

const uploadFile = async (file) => {
    if (file.type !== 'application/pdf') {
        error.value = "Only PDF files are supported.";
        return;
    }

    isUploading.value = true;
    error.value = null;
    progress.value = 0;

    try {
        const response = await api.uploadFile(file, (event) => {
            progress.value = Math.round((event.loaded * 100) / event.total);
        });
        emit('upload-success', response.data.job_id);
    } catch (err) {
        error.value = "Upload failed: " + (err.response?.data?.detail || err.message);
    } finally {
        isUploading.value = false;
    }
};
</script>

<template>
    <div class="upload-container">
        <div 
            class="drop-zone" 
            :class="{ 'dragging': isDragging, 'uploading': isUploading }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="$refs.fileInput.click()"
        >
            <input type="file" ref="fileInput" @change="handleFileSelect" accept="application/pdf" hidden>
            
            <div v-if="!isUploading" class="content">
                <div class="icon">📄</div>
                <h3>Upload your PDF</h3>
                <p>Drag & drop or click to browse</p>
                <p class="sub-text">Large files supported</p>
            </div>

            <div v-else class="progress-container">
                <div class="loader"></div>
                <p>Uploading... {{ progress }}%</p>
            </div>
        </div>

        <div v-if="error" class="error-message">
            {{ error }}
        </div>
    </div>
</template>

<style scoped>
.upload-container {
    width: 100%;
    max-width: 600px;
    margin: 0 auto;
}

.drop-zone {
    border: 2px dashed #e2e8f0;
    border-radius: 16px;
    padding: 3rem;
    text-align: center;
    background: rgba(255, 255, 255, 0.5);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}

.drop-zone:hover, .drop-zone.dragging {
    border-color: #6366f1;
    background: rgba(99, 102, 241, 0.05);
    transform: translateY(-2px);
    box-shadow: 0 10px 25px rgba(0,0,0,0.05);
}

.icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}

h3 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #1e293b;
}

p {
    color: #64748b;
    margin: 0.5rem 0 0;
}

.sub-text {
    font-size: 0.875rem;
    opacity: 0.7;
}

.progress-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
}

.loader {
    width: 40px;
    height: 40px;
    border: 3px solid #e2e8f0;
    border-top-color: #6366f1;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 1rem;
}

.error-message {
    margin-top: 1rem;
    padding: 1rem;
    background: #fee2e2;
    color: #991b1b;
    border-radius: 8px;
    text-align: center;
    font-size: 0.9rem;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
</style>
