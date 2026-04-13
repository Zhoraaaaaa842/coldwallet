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
            @input="validatePassword"
            type="password"
            class="input-field"
            placeholder="Создайте надежный пароль"
            :class="{ 'border-error': passwordError }"
          />
          <div v-if="passwordError" class="text-error text-xs mt-2">{{ passwordError }}</div>
          <p v-else class="text-xs text-text-muted mt-2">Минимум 12 символов, 3 из 4 типов символов</p>
        </div>

        <button
          @click="handleCreate"
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
          @input="validateMnemonic"
          class="input-field h-32 resize-none font-mono text-sm"
          placeholder="word1 word2 word3 ... (12, 15, 18, 21 или 24 слова)"
        ></textarea>
        
        <!-- Mnemonic validation info -->
        <div class="mt-3 space-y-2">
          <p class="text-xs text-text-muted">
            Количество слов: {{ wordCount }}
          </p>
          <div v-if="mnemonic.trim()" class="flex gap-1">
            <div
              v-for="i in 5"
              :key="i"
              class="h-1 flex-1 rounded-full transition-colors"
              :class="validWordCount >= i ? 'bg-success' : 'bg-bg-secondary'"
            />
          </div>
          <p v-if="!isValidWordCount" class="text-error text-xs">
            Поддерживаются только 12, 15, 18, 21 или 24 слова
          </p>
        </div>

        <div class="mt-4">
          <label class="block text-sm font-medium text-text-secondary mb-2">Пароль для шифрования</label>
          <input
            v-model="password"
            @input="validatePassword"
            type="password"
            class="input-field"
            placeholder="Создайте надежный пароль"
            :class="{ 'border-error': passwordError }"
          />
          <div v-if="passwordError" class="text-error text-xs mt-2">{{ passwordError }}</div>
        </div>

        <!-- Duplicate words warning -->
        <div v-if="hasDuplicateWords" class="bg-warning/10 border border-warning/30 rounded-lg p-3 mt-4">
          <p class="text-warning text-sm">
            ⚠️ Обнаружены повторяющиеся слова. Это может быть нормально, но проверьте фразу.
          </p>
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
import { ref, computed } from 'vue'

const emit = defineEmits<{
  create: [password: string]
  import: [mnemonic: string, password: string]
  cancel: []
}>()

const showImport = ref(false)
const mnemonic = ref('')
const password = ref('')
const error = ref('')
const passwordError = ref('')

// Mnemonic validation
const wordCount = computed(() => {
  if (!mnemonic.value.trim()) return 0
  return mnemonic.value.trim().split(/\s+/).length
})

const validWordCount = computed(() => {
  if (wordCount.value <= 12) return 1
  if (wordCount.value <= 15) return 2
  if (wordCount.value <= 18) return 3
  if (wordCount.value <= 21) return 4
  return 5
})

const isValidWordCount = computed(() => {
  return [12, 15, 18, 21, 24].includes(wordCount.value)
})

const hasDuplicateWords = computed(() => {
  if (!mnemonic.value.trim()) return false
  const words = mnemonic.value.trim().toLowerCase().split(/\s+/)
  const uniqueWords = new Set(words)
  return uniqueWords.size !== words.length
})

// Password validation
function validatePassword() {
  passwordError.value = ''
  
  if (!password.value) return
  
  if (password.value.length < 12) {
    passwordError.value = 'Минимум 12 символов'
    return
  }
  
  if (password.value.length > 128) {
    passwordError.value = 'Максимум 128 символов'
    return
  }
  
  // Check character classes
  let charClasses = 0
  if (/[A-ZА-Я]/.test(password.value)) charClasses++
  if (/[a-zа-я]/.test(password.value)) charClasses++
  if (/[0-9]/.test(password.value)) charClasses++
  if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password.value)) charClasses++
  
  if (charClasses < 3) {
    passwordError.value = 'Нужно 3 из 4 типов символов'
  }
}

// Mnemonic validation
function validateMnemonic() {
  error.value = ''
  
  // Check for non-ASCII characters
  if (/[^\x00-\x7F]/.test(mnemonic.value)) {
    error.value = 'Мнемоническая фраза должна содержать только ASCII символы'
    return
  }
}

function handleImport() {
  const words = mnemonic.value.trim().split(/\s+/)
  
  if (![12, 15, 18, 21, 24].includes(words.length)) {
    error.value = 'Мнемоническая фраза должна содержать 12, 15, 18, 21 или 24 слова'
    return
  }
  
  // Check for duplicate words (warning only, not blocking)
  const uniqueWords = new Set(words.map(w => w.toLowerCase()))
  if (uniqueWords.size !== words.length) {
    console.warn('Duplicate words detected in mnemonic')
  }

  if (password.value.length < 12) {
    error.value = 'Пароль должен содержать минимум 12 символов'
    return
  }
  
  // Validate password complexity
  let charClasses = 0
  if (/[A-ZА-Я]/.test(password.value)) charClasses++
  if (/[a-zа-я]/.test(password.value)) charClasses++
  if (/[0-9]/.test(password.value)) charClasses++
  if (/[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password.value)) charClasses++
  
  if (charClasses < 3) {
    error.value = 'Пароль слишком простой. Нужно 3 из 4 типов символов'
    return
  }

  emit('import', mnemonic.value.trim(), password.value)
}

function handleCreate() {
  validatePassword()
  
  if (passwordError.value) {
    error.value = passwordError.value
    return
  }
  
  if (password.value.length < 12) {
    error.value = 'Пароль должен содержать минимум 12 символов'
    return
  }
  
  emit('create', password.value)
}
</script>
