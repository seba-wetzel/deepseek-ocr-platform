<script setup>
import { ref, watch, onMounted } from 'vue';

const props = defineProps({
    modelValue: { type: Number, default: null },
    prompts: { type: Array, default: () => [] }
});

const emit = defineEmits(['update:modelValue', 'save-prompt']);

// Internal UI State
const isEditing = ref(false);
const promptForm = ref({ id: null, name: '', content: '', description: '' });

// Watch Prompts to set default if needed
watch(() => props.prompts, (newPrompts) => {
    if (!props.modelValue && newPrompts.length > 0) {
        const defaultPrompt = newPrompts.find(p => p.is_default) || newPrompts[0];
        emit('update:modelValue', defaultPrompt.id);
    }
}, { immediate: true });

// Watch selection to update form preview & editor state
watch(() => props.modelValue, (newId) => {
    // If ID changes, we assume we might need to close edit mode if it was a create action?
    // Or at least update the form content.
    if (newId) {
        const p = props.prompts.find(pr => pr.id === newId);
        if (p) {
            promptForm.value = { ...p };
            // If we were editing a new prompt and we got a valid ID, assume save success & close edit?
            // This is "optimistic" or "reactive" UI.
            // Let's rely on explicit save success? 
            // Actually, if modelValue changes to the new ID (which App.vue does), we should probably exit edit mode if we were editing.
            if (isEditing.value) {
                isEditing.value = false;
            }
        }
    }
}, { immediate: true });

const toggleEditMode = () => {
    isEditing.value = !isEditing.value;
    if (isEditing.value && props.modelValue) {
        // Populate form with current
        const p = props.prompts.find(pr => pr.id === props.modelValue);
        if (p) promptForm.value = { ...p };
    }
};

const startNewPrompt = () => {
    promptForm.value = { id: null, name: 'Nuevo Prompt', content: '<image>\n<|grounding|>', description: '' };
    emit('update:modelValue', null);
    isEditing.value = true;
};

const savePrompt = () => {
    if (!promptForm.value.name || !promptForm.value.content) {
        alert("Nombre y Contenido son requeridos.");
        return;
    }
    emit('save-prompt', promptForm.value);
    isEditing.value = false;
};

const cancelEdit = () => {
    isEditing.value = false;
    // Restore selection form view
    if (props.modelValue) {
        const p = props.prompts.find(pr => pr.id === props.modelValue);
        if (p) promptForm.value = { ...p };
    }
};
</script>

<template>
    <div class="prompt-manager">
        <div class="prompt-header">
            <label>Configuración del Modelo</label>
            <div class="prompt-actions">
                <button @click="startNewPrompt" class="text-btn small" v-if="!isEditing">+ Nuevo</button>
                <button @click="toggleEditMode" class="text-btn small" v-if="modelValue && !isEditing">
                    Editar
                </button>
                <button @click="cancelEdit" class="text-btn small cancel" v-if="isEditing">
                    Cancelar
                </button>
            </div>
        </div>

        <div class="prompt-selector" v-if="!isEditing">
            <select :value="modelValue" @input="$emit('update:modelValue', parseInt($event.target.value))" class="prompt-select">
                <option v-for="p in prompts" :key="p.id" :value="p.id">
                    {{ p.name }} {{ p.is_default ? '(Default)' : '' }}
                </option>
            </select>
            
            <div class="prompt-preview">
                {{ promptForm.content }}
            </div>
        </div>

        <div class="prompt-editor" v-else>
            <input v-model="promptForm.name" placeholder="Nombre del Prompt" class="input-name" />
            <textarea v-model="promptForm.content" class="input-content" rows="6"></textarea>
            <button @click="savePrompt" class="save-btn">Guardar Prompt</button>
        </div>
    </div>
</template>

<style scoped>
.prompt-manager {
    background: white;
    padding: 1.25rem;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
}
.prompt-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
}
.prompt-header label {
    font-weight: 600;
    color: #475569;
    font-size: 0.9rem;
}

.prompt-select {
    width: 100%;
    padding: 0.5rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
}
 .prompt-preview {
    background: #f1f5f9;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.85rem;
    color: #334155;
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    line-height: 1.5;
}

.input-name {
    width: 100%;
    margin-bottom: 0.5rem;
    padding: 0.5rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
}
.input-content {
    width: 100%;
    margin-bottom: 0.5rem;
    padding: 0.5rem;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.85rem;
}

.text-btn {
    background: none;
    border: none;
    color: #6366f1;
    cursor: pointer;
    font-size: 0.85rem;
    margin-left: 0.5rem;
}
.text-btn:hover {
    text-decoration: underline;
}
.text-btn.cancel {
    color: #ef4444;
}

.save-btn {
    background: #10b981;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    cursor: pointer;
    width: 100%;
    font-weight: 500;
}
.save-btn:hover {
    background: #059669;
}
</style>
