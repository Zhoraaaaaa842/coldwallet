<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('cancel')" />

    <!-- Dialog -->
    <div class="relative bg-bg-card border border-border rounded-2xl shadow-2xl max-w-lg w-full mx-4 p-6 space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-bold text-text-primary">
          {{ mode === 'add' ? 'Добавить контакт' : 'Редактировать контакт' }}
        </h2>
        <button @click="$emit('cancel')" class="text-text-muted hover:text-text-primary transition-colors">
          <X class="w-5 h-5" />
        </button>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <!-- Name -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-text-secondary">Имя</label>
          <input
            v-model="form.name"
            @input="validateName"
            type="text"
            required
            maxlength="100"
            placeholder="Введите имя контакта"
            class="w-full px-4 py-3 bg-bg-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-white/20"
            :class="{ 'border-red-500': errors.name }"
          />
          <p v-if="errors.name" class="text-xs text-red-500">{{ errors.name }}</p>
        </div>

        <!-- Address -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-text-secondary">Адрес</label>
          <input
            v-model="form.address"
            @input="validateAddress"
            type="text"
            required
            placeholder="0x..."
            class="w-full px-4 py-3 bg-bg-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted font-mono text-sm focus:outline-none focus:ring-2 focus:ring-white/20"
            :class="{ 'border-red-500': errors.address }"
          />
          <p v-if="errors.address" class="text-xs text-red-500">{{ errors.address }}</p>
        </div>

        <!-- Note -->
        <div class="space-y-2">
          <label class="text-sm font-medium text-text-secondary">Заметка (необязательно)</label>
          <textarea
            v-model="form.note"
            rows="3"
            placeholder="Дополнительная заметка о контакте"
            class="w-full px-4 py-3 bg-bg-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-white/20 resize-none"
          />
        </div>

        <!-- Actions -->
        <div class="flex gap-3 pt-4">
          <button
            type="button"
            @click="$emit('cancel')"
            class="flex-1 px-4 py-2.5 bg-bg-secondary border border-border rounded-lg text-text-primary font-medium hover:bg-bg-hover transition-colors"
          >
            Отмена
          </button>
          <button
            type="submit"
            :disabled="!isValid || isSubmitting"
            class="flex-1 px-4 py-2.5 bg-white text-black rounded-lg font-medium hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {{ isSubmitting ? 'Сохранение...' : 'Сохранить' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Contact } from '@/types'
import { X } from 'lucide-vue-next'

const props = defineProps<{
  mode: 'add' | 'edit'
  contact?: Contact | null
}>()

const emit = defineEmits<{
  save: [contact: Partial<Contact>]
  cancel: []
}>()

const form = ref({
  name: '',
  address: '',
  note: '',
})

const errors = ref({
  name: '',
  address: '',
})

const isSubmitting = ref(false)

// Watch for contact prop changes
watch(() => props.contact, (contact) => {
  if (contact && props.mode === 'edit') {
    form.value = {
      name: contact.name,
      address: contact.address,
      note: contact.note || '',
    }
  }
}, { immediate: true })

// Validation
function validateName() {
  const name = form.value.name.trim()
  
  if (!name) {
    errors.value.name = 'Имя обязательно'
    return false
  }
  
  if (name.length > 100) {
    errors.value.name = 'Имя не может быть длиннее 100 символов'
    return false
  }
  
  // Check for control characters
  if (/[\x00-\x1F\x7F]/.test(name)) {
    errors.value.name = 'Имя содержит недопустимые символы'
    return false
  }
  
  errors.value.name = ''
  return true
}

function validateAddress() {
  const address = form.value.address.trim()
  
  // Basic Ethereum address validation
  if (!address) {
    errors.value.address = 'Адрес обязателен'
    return false
  }
  
  if (!/^0x[0-9a-fA-F]{40}$/.test(address)) {
    errors.value.address = 'Неверный формат адреса Ethereum'
    return false
  }
  
  errors.value.address = ''
  return true
}

const isValid = computed(() => {
  return validateName() && validateAddress()
})

async function handleSubmit() {
  if (!isValid.value) return
  
  isSubmitting.value = true
  
  try {
    emit('save', {
      name: form.value.name.trim(),
      address: form.value.address.trim().toLowerCase(),
      note: form.value.note.trim() || undefined,
    })
  } finally {
    isSubmitting.value = false
  }
}
</script>
