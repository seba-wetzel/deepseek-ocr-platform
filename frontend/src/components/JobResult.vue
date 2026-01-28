<script setup>
import { computed, ref } from 'vue';
import api from '../services/api';
import { JOB_STATUS_LABELS } from '../constants';

const props = defineProps({
    jobId: { type: String, required: true },
    status: { type: String, default: 'processing' },
    progress: { type: Number, default: 0 },
    results: { type: Array, default: () => [] },
    initiallyExpanded: { type: Boolean, default: false }
});

const emit = defineEmits(['cancel', 'delete']);

const isCardExpanded = ref(props.initiallyExpanded);
const expandedPages = ref(new Set());

// Computed helpers
const isProcessing = computed(() => props.status === 'processing' || props.status === 'queued');
const isCompleted = computed(() => props.status === 'completed');
const statusLabel = computed(() => JOB_STATUS_LABELS[props.status] || props.status);

// Actions
const toggleCard = () => {
    isCardExpanded.value = !isCardExpanded.value;
};

const togglePage = (pageNumber) => {
    if (expandedPages.value.has(pageNumber)) {
        expandedPages.value.delete(pageNumber);
    } else {
        expandedPages.value.add(pageNumber);
    }
};

const isExpanded = (pageNumber) => expandedPages.value.has(pageNumber);

// Download functions (Okay to keep here as they just open URLs)
const downloadExcel = () => {
    window.open(api.getExportUrl(props.jobId, 'excel'), '_blank');
};

const downloadCsv = () => {
    window.open(api.getExportUrl(props.jobId, 'csv'), '_blank');
};

// Interaction functions - Just emit
const onCancel = () => {
    if (!confirm('¿Estás seguro de que deseas cancelar este trabajo?')) return;
    emit('cancel', props.jobId);
};

const onDelete = () => {
    if (!confirm('¿Estás seguro de que deseas eliminar este trabajo?')) return;
    emit('delete', props.jobId);
};
</script>

<template>
    <div class="result-viewer">
        <div class="header" @click="toggleCard">
            <div class="header-left">
                <button class="toggle-btn" :class="{ rotated: isCardExpanded }">▶</button>
                <h2>
                    {{ isProcessing ? 'Procesando Documento...' : 'Resultados del Documento' }}
                    <span class="job-id-label">#{{ jobId.slice(0,8) }}</span>
                </h2>
            </div>
            <div class="header-right">
                <div class="status-badge" :class="status">
                    {{ statusLabel }} {{ isProcessing ? `(${progress}%)` : '' }}
                </div>
                
                <!-- Cancel Button -->
                <button 
                    v-if="isProcessing" 
                    @click.stop="onCancel" 
                    class="action-icon-btn cancel-btn" 
                    title="Cancelar Trabajo"
                >
                    ✕
                </button>

                <!-- Delete Button -->
                <button 
                    v-if="!isProcessing" 
                    @click.stop="onDelete" 
                    class="action-icon-btn delete-btn" 
                    title="Eliminar Trabajo"
                >
                    🗑️
                </button>
            </div>
        </div>

        <div v-show="isCardExpanded">
            <div v-if="isProcessing" class="progress-bar-container">
                <div class="progress-bar" :style="{ width: progress + '%' }"></div>
            </div>

            <div class="actions" v-if="isCompleted">
                <button @click="downloadExcel" class="action-btn">
                    📥 Descargar Excel
                </button>
                <button @click="downloadCsv" class="action-btn">
                    📊 Descargar CSV
                </button>
            </div>
            
            <!-- Result List ... -->

            <div class="result-content">
                <div v-if="results && results.length > 0" class="accordion-list">
                    <div 
                        v-for="page in results" 
                        :key="page.page" 
                        class="accordion-item" 
                        :class="{ 'is-expanded': isExpanded(page.page) }"
                    >
                        <div class="accordion-header" @click="togglePage(page.page)">
                            <div class="page-title">Página {{ page.page }}</div>
                            <button class="expand-btn">
                                {{ isExpanded(page.page) ? 'Colapsar' : 'Expandir' }}
                            </button>
                        </div>
                        
                        <div class="accordion-content">
                            <pre class="text-content">{{ page.text }}</pre>
                        </div>
                        
                        <div v-if="!isExpanded(page.page)" class="preview-overlay" @click="togglePage(page.page)"></div>
                    </div>
                </div>
                
                <div v-else-if="!isProcessing" class="empty-state">
                    No hay resultados para mostrar.
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.result-viewer {
    background: white;
    border-radius: 16px;
    padding: 1.5rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    margin-bottom: 1.5rem; /* Add spacing between cards */
}

/* Header Styles */
.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    user-select: none;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.action-icon-btn {
    background: transparent;
    border: none;
    font-size: 1.1rem;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 50%;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
}

.action-icon-btn:hover {
    background: #f1f5f9;
}

.cancel-btn {
    color: #ef4444;
}
.cancel-btn:hover {
    background: #fee2e2;
}

.delete-btn {
    color: #94a3b8;
}
.delete-btn:hover {
    color: #ef4444;
    background: #fee2e2;
}

.toggle-btn {
    background: none;
    border: none;
    font-size: 0.8rem;
    color: #94a3b8;
    transition: transform 0.2s ease;
    cursor: pointer;
    padding: 0;
}

.toggle-btn.rotated {
    transform: rotate(90deg);
}

.job-id-label {
    font-size: 0.8rem;
    color: #94a3b8;
    font-weight: 400;
    margin-left: 0.5rem;
    font-family: monospace;
}

h2 {
    margin: 0;
    font-size: 1.5rem;
    color: #1e293b;
}

.status-badge {
    padding: 0.5rem 1rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
    text-transform: uppercase;
}

.status-badge.processing { background: #e0e7ff; color: #4f46e5; }
.status-badge.completed { background: #dcfce7; color: #166534; }
.status-badge.error { background: #fee2e2; color: #991b1b; }

.progress-bar-container {
    height: 8px;
    background: #f1f5f9;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 2rem;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #6366f1, #818cf8);
    transition: width 0.3s ease;
}

.actions {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
}

.btn {
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    border: none;
}

.btn-primary { background: #6366f1; color: white; }
.btn-primary:hover { background: #4f46e5; }
.btn-secondary { background: #f1f5f9; color: #475569; }
.btn-secondary:hover { background: #e2e8f0; }

/* Accordion Styles */
.accordion-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.accordion-item {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    transition: all 0.3s ease;
    background: #f8fafc;
}

.accordion-item:hover {
    border-color: #cbd5e1;
}

.accordion-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    background: white;
    cursor: pointer;
    border-bottom: 1px solid transparent;
}

.is-expanded .accordion-header {
    border-bottom-color: #e2e8f0;
}

.page-title {
    font-weight: 600;
    color: #334155;
}

.expand-btn {
    background: transparent;
    border: 1px solid #e2e8f0;
    padding: 0.25rem 0.75rem;
    border-radius: 6px;
    font-size: 0.75rem;
    color: #64748b;
    cursor: pointer;
}

.accordion-content {
    padding: 1.5rem;
    background: #ffffff;
    /* Collapsed State Logic */
    max-height: 150px; /* Fixed height for preview */
    overflow: hidden;
    transition: max-height 0.3s ease-in-out;
}

.is-expanded .accordion-content {
    max-height: none; /* Let it grow */
    overflow: visible;
}

.text-content {
    margin: 0;
    white-space: pre-wrap;
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.9rem;
    color: #475569;
    line-height: 1.5;
}

/* Gradient Overlay for Preview */
.preview-overlay {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 80px;
    background: linear-gradient(to bottom, transparent, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 100%);
    cursor: pointer;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 0.5rem;
}

.empty-state {
    text-align: center;
    padding: 3rem;
    color: #94a3b8;
}
</style>
