<template>
  <div class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
    <div class="bg-bg-card rounded-2xl border border-border p-8 w-[420px] shadow-2xl">
      <h2 class="text-2xl font-bold text-white mb-2">
        {{ mode === 'unlock' ? 'Разблокировать кошелёк' : mode === 'create' ? 'Создать пароль' : 'Импорт кошелька' }}
      </h2>
      <p class="text-text-secondary text-sm mb-6">
        {{ mode === 'unlock' ? 'Введите пароль для доступа к кошельку' : 'Создайте надежный пароль для защиты' }}
      </p>

      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div>
          <label class="block text-sm font-medium text-text-secondary mb-2">Пароль</label>
          <input
            v-model="password"
            type="password"
            class="input-field"
            placeholder="••••••••"
            ref="passwordInput"
            required
          />
        </div>

        <div v-if="mode === 'create'">
          <label class="block text-sm font-medium text-text-secondary mb-2">Подтвердите пароль</label>
          <input
            v-model="passwordConfirm"
            type="password"
            class="input-field"
            placeholder="••••••••"
            required
          />
        </div>

        <div v-if="error" class="bg-error/10 border border-error/30 rounded-lg p-3">
          <p class="text-error text-sm">{{ error }}</p>
        </div>

        <div class="flex gap-3 pt-2">
          <button type="submit" class="flex-1 bg-white hover:bg-gray-200 text-black font-semibold px-6 py-3 rounded-lg transition-all duration-200">
            {{ mode === 'unlock' ? 'Разблокировать' : 'Продолжить' }}
          </button>
          <button type="button" @click="$emit('cancel')" class="flex-1 bg-bg-tertiary hover:bg-bg-hover text-text-secondary font-medium px-6 py-3 rounded-lg transition-colors duration-200">
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
