<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-bg-secondary rounded-2xl border border-border p-6 w-96">
      <h2 class="text-xl font-bold text-text-primary mb-4">
        {{ mode === 'unlock' ? 'Разблокировать кошелёк' : mode === 'create' ? 'Создать пароль' : 'Импорт кошелька' }}
      </h2>
      
      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm text-text-secondary mb-2">Пароль</label>
          <input
            v-model="password"
            type="password"
            class="input-field"
            placeholder="Введите пароль"
            ref="passwordInput"
            required
          />
        </div>

        <div v-if="mode === 'create'">
          <label class="block text-sm text-text-secondary mb-2">Подтвердите пароль</label>
          <input
            v-model="passwordConfirm"
            type="password"
            class="input-field"
            placeholder="Повторите пароль"
            required
          />
        </div>

        <div v-if="error" class="text-error text-sm">
          {{ error }}
        </div>

        <div class="flex gap-3">
          <button type="submit" class="btn-primary flex-1">
            {{ mode === 'unlock' ? 'Разблокировать' : 'Продолжить' }}
          </button>
          <button type="button" @click="$emit('cancel')" class="btn-secondary flex-1">
            Отмена
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const props = defineProps<{
  mode: 'unlock' | 'create' | 'import'
}>()

const emit = defineEmits<{
  success: []
  cancel: []
}>()

const password = ref('')
const passwordConfirm = ref('')
const error = ref('')
const passwordInput = ref<HTMLInputElement | null>(null)

onMounted(() => {
  passwordInput.value?.focus()
})

function handleSubmit() {
  if (props.mode === 'create' && password.value !== passwordConfirm.value) {
    error.value = 'Пароли не совпадают'
    return
  }

  if (password.value.length < 6) {
    error.value = 'Пароль должен содержать минимум 6 символов'
    return
  }

  emit('success')
}
</script>
