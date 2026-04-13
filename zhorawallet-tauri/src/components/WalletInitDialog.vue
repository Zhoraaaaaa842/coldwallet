<template>
  <div class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
    <div class="bg-bg-card rounded-2xl border border-border p-8 w-[520px] shadow-2xl">
      <h2 class="text-3xl font-bold text-white mb-2">Добро пожаловать</h2>
      <p class="text-text-secondary mb-8">
        USB накопитель обнаружен. Создайте новый кошелёк или импортируйте существующий.
      </p>

      <div class="space-y-4">
        <div v-if="!showImport" class="mb-6">
          <label class="block text-sm font-medium text-text-secondary mb-2">Пароль для шифрования</label>
          <input
            v-model="password"
            type="password"
            class="input-field"
            placeholder="Создайте надежный пароль"
          />
          <p class="text-xs text-text-muted mt-2">Минимум 6 символов</p>
        </div>

        <button
          @click="$emit('create', password)"
          class="w-full bg-white hover:bg-gray-200 text-black font-semibold px-6 py-4 rounded-xl transition-all duration-200 flex items-center gap-4 group"
        >
          <div class="w-12 h-12 bg-black rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <div class="text-left flex-1">
            <div class="font-bold text-lg">Создать новый кошелёк</div>
            <div class="text-sm text-gray-600">Генерация новой seed-фразы из 24 слов</div>
          </div>
        </button>

        <button
          @click="showImport = true"
          class="w-full bg-bg-tertiary hover:bg-bg-hover text-white font-medium px-6 py-4 rounded-xl transition-all duration-200 flex items-center gap-4 group"
        >
          <div class="w-12 h-12 bg-bg-hover rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </div>
          <div class="text-left flex-1">
            <div class="font-bold text-lg">Импортировать кошелёк</div>
            <div class="text-sm text-text-secondary">Восстановление из существующей seed-фразы</div>
          </div>
        </button>
      </div>

      <!-- Import Mnemonic Dialog -->
      <div v-if="showImport" class="mt-6 p-6 bg-bg-tertiary rounded-xl border border-border">
        <h3 class="text-xl font-bold text-white mb-4">Введите seed-фразу</h3>
        <textarea
          v-model="mnemonic"
          class="input-field h-32 resize-none font-mono text-sm"
          placeholder="word1 word2 word3 ... word24"
        ></textarea>

        <div class="mt-4">
          <label class="block text-sm font-medium text-text-secondary mb-2">Пароль для шифрования</label>
          <input
            v-model="password"
            type="password"
            class="input-field"
            placeholder="Создайте надежный пароль"
          />
        </div>

        <div v-if="error" class="bg-error/10 border border-error/30 rounded-lg p-3 mt-4">
          <p class="text-error text-sm">{{ error }}</p>
        </div>

        <div class="flex gap-3 mt-6">
          <button
            @click="handleImport"
            class="flex-1 bg-white hover:bg-gray-200 text-black font-semibold px-6 py-3 rounded-lg transition-all duration-200"
          >
            Импортировать
          </button>
          <button
            @click="showImport = false"
            class="flex-1 bg-bg-hover hover:bg-bg-tertiary text-text-secondary font-medium px-6 py-3 rounded-lg transition-colors duration-200"
          >
            Назад
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
