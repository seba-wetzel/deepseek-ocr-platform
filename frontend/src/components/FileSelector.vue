<script setup>
import { ref } from 'vue';

const props = defineProps({
    modelValue: { type: Object, default: null } // The File object
});

const emit = defineEmits(['update:modelValue']);

const isDragging = ref(false);

const handleDrop = (e) => {
    isDragging.value = false;
    const files = e.dataTransfer.files;
    if (files.length) selectFile(files[0]);
};

const handleFileSelect = (e) => {
    const files = e.target.files;
    if (files.length) selectFile(files[0]);
};

const selectFile = (file) => {
    if (file.type !== 'application/pdf') {
        alert("Solo se permiten archivos PDF."); // Or emit error event? For simplicity, alert now or parent validation.
        return;
    }
    emit('update:modelValue', file);
};

const clearFile = () => {
    emit('update:modelValue', null);
};
</script>

<template>
    <div class="file-selector">
        <div 
            v-if="!modelValue"
            class="drop-zone" 
            :class="{ 'dragging': isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleDrop"
            @click="$refs.fileInput.click()"
        >
            <input type="file" ref="fileInput" @change="handleFileSelect" accept="application/pdf" hidden>
            <div class="content">
                <div class="icon">📄</div>
                <h3>Sube tu PDF</h3>
                <p>Arrastra archivos o haz clic para buscar</p>
            </div>
        </div>

        <div v-else class="selected-file-card">
            <div class="file-info">
                <span class="icon">📄</span>
                <span class="filename">{{ modelValue.name }}</span>
                <button @click="clearFile" class="change-btn" title="Cambiar archivo">✕</button>
            </div>
        </div>
    </div>
</template>

<style scoped>
.drop-zone {
    border: 2px dashed #e2e8f0;
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    background: rgba(255, 255, 255, 0.5);
    cursor: pointer;
    transition: all 0.2s;
}
.drop-zone:hover, .drop-zone.dragging {
    border-color: #6366f1;
    background: rgba(99, 102, 241, 0.05);
}

.selected-file-card {
    background: white;
    padding: 1rem;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
}
.file-info {
    display: flex;
    align-items: center;
    gap: 1rem;
}
.filename {
    flex: 1;
    font-weight: 500;
    color: #1e293b;
}
.icon {
    font-size: 1.5rem;
}
.drop-zone .icon {
    font-size: 3rem;
    margin-bottom: 1rem;
}
.content h3 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 600;
    color: #1e293b;
}
.content p {
    color: #64748b;
    margin: 0.5rem 0 0;
}
.change-btn {
    background: none;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    padding: 0.25rem;
    font-size: 1.2rem;
}
.change-btn:hover {
    color: #ef4444;
}
</style>
