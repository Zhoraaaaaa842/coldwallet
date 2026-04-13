<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-bg-secondary rounded-2xl border border-border p-6 w-[32rem]">
      <h2 class="text-2xl font-bold text-text-primary mb-2">Инициализация кошелька</h2>
      <p class="text-text-secondary mb-6">
        USB накопитель обнаружен, но кошелёк не инициализирован.
      </p>

      <div class="space-y-3">
        <div class="mb-4">
          <label class="block text-sm text-text-secondary mb-2">Пароль для шифрования</label>
          <input
            v-model="password"
            type="password"
            class="input-field"
            placeholder="Придумайте пароль"
          />
        </div>
        
        <button
          @click="$emit('create', password)"
          class="w-full bg-accent hover:bg-accent-hover active:bg-accent-dark text-white font-semibold px-6 py-4 rounded-xl transition-colors duration-200 flex items-center gap-3"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          <div class="text-left">
            <div class="font-semibold">Создать новый кошелёк</div>
            <div class="text-sm text-text-secondary">Генерация новой мнемонической фразы</div>
          </div>
        </button>

        <button
          @click="showImport = true"
          class="w-full bg-bg-tertiary hover:bg-bg-hover text-white font-medium px-6 py-4 rounded-xl transition-colors duration-200 flex items-center gap-3"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          <div class="text-left">
            <div class="font-semibold">Импортировать кошелёк</div>
            <div class="text-sm text-text-secondary">Восстановление из мнемонической фразы</div>
          </div>
        </button>

        <button
          @click="$emit('cancel')"
          class="w-full bg-bg-tertiary hover:bg-bg-hover text-text-secondary font-medium px-6 py-3 rounded-xl transition-colors duration-200"
        >
          Отмена
        </button>
      </div>

      <!-- Import Mnemonic Dialog -->
      <div v-if="showImport" class="mt-6 p-4 bg-bg-tertiary rounded-xl">
        <h3 class="text-lg font-semibold text-text-primary mb-3">Введите мнемоническую фразу</h3>
        <textarea
          v-model="mnemonic"
          class="input-field h-24 resize-none"
          placeholder="word1 word2 word3 ... word24"
        ></textarea>
        
        <div class="mt-4">
          <label class="block text-sm text-text-secondary mb-2">Пароль для шифрования</label>
          <input
            v-model="password"
            type="password"
            class="input-field"
            placeholder="Придумайте пароль"
          />
        </div>

        <div v-if="error" class="text-error text-sm mt-2">
          {{ error }}
        </div>

        <div class="flex gap-3 mt-4">
          <button
            @click="handleImport"
            class="btn-primary flex-1"
          >
            Импортировать
          </button>
          <button
            @click="showImport = false"
            class="btn-secondary flex-1"
          >
            Отмена
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  create: [password: string]
  import: [mnemonic: string, password: string]
  cancel: []
}>()

const showImport = ref(false)
const mnemonic = ref('')
const password = ref('')
const error = ref('')

function handleImport() {
  const words = mnemonic.value.trim().split(/\s+/)
  if (words.length !== 24) {
    error.value = 'Мнемоническая фраза должна содержать 24 слова'
    return
  }

  if (password.value.length < 6) {
    error.value = 'Пароль должен содержать минимум 6 символов'
    return
  }

  emit('import', mnemonic.value.trim(), password.value)
}
</script>
