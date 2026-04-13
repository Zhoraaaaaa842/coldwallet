<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('cancel')" />

    <!-- Dialog -->
    <div class="relative bg-bg-card border border-border rounded-2xl shadow-2xl max-w-md w-full mx-4 p-6 space-y-6">
      <!-- Header -->
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center flex-shrink-0">
          <AlertTriangle class="w-5 h-5 text-red-500" />
        </div>
        <h2 class="text-xl font-bold text-text-primary">{{ title }}</h2>
      </div>

      <!-- Message -->
      <p class="text-text-secondary text-sm">{{ message }}</p>

      <!-- Actions -->
      <div class="flex gap-3">
        <button
          @click="$emit('cancel')"
          class="flex-1 px-4 py-2.5 bg-bg-secondary border border-border rounded-lg text-text-primary font-medium hover:bg-bg-hover transition-colors"
        >
          Отмена
        </button>
        <button
          @click="$emit('confirm')"
          class="flex-1 px-4 py-2.5 bg-red-500 text-white rounded-lg font-medium hover:bg-red-600 transition-colors"
        >
          Удалить
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'

defineProps<{
  title: string
  message: string
}>()

defineEmits<{
  confirm: []
  cancel: []
}>()
</script>
