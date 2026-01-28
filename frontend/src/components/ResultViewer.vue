<script setup>
import JobResult from './JobResult.vue';

defineProps({
    jobs: {
        type: Array,
        default: () => []
    },
    results: {
        type: Object,
        default: () => ({})
    },
    loading: {
        type: Boolean,
        default: false
    }
});

defineEmits(['delete-job', 'cancel-job']);
</script>

<template>
    <div class="result-list-container">
        <h3>Processing History</h3>
        
        <div v-if="loading && jobs.length === 0" class="loading-state">
            Loading history...
        </div>

        <div v-else-if="jobs.length === 0" class="empty-state">
            No documents processed yet. Upload a PDF to start!
        </div>

        <div class="jobs-stack">
            <JobResult 
                v-for="job in jobs" 
                :key="job.id" 
                :job-id="job.id"
                :status="job.status"
                :progress="job.progress"
                :results="results[job.id] || []"
                class="job-item-card"
                @cancel="$emit('cancel-job', $event)"
                @delete="$emit('delete-job', $event)"
            />
        </div>
    </div>
</template>

<style scoped>
.result-list-container {
    margin-top: 2rem;
}

h3 {
    font-size: 1.25rem;
    color: #475569;
    margin-bottom: 1.5rem;
    font-weight: 600;
}

.jobs-stack {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.loading-state, .empty-state {
    text-align: center;
    padding: 3rem;
    color: #94a3b8;
    background: #f8fafc;
    border-radius: 12px;
    border: 2px dashed #e2e8f0;
}

/* Animations for new items? */
.job-item-card {
    transition: all 0.3s ease;
}
</style>
