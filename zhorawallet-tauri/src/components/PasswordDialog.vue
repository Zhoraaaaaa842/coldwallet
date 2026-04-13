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
            @input="validatePassword"
            type="password"
            class="input-field"
            placeholder="••••••••"
            ref="passwordInput"
            required
            :class="{ 'border-error': passwordError }"
          />
          <div v-if="mode === 'create' || mode === 'import'" class="mt-3 space-y-2">
            <!-- Password strength indicator -->
            <div class="flex gap-1">
              <div
                v-for="i in 4"
                :key="i"
                class="h-1 flex-1 rounded-full transition-colors"
                :class="passwordStrength >= i ? getStrengthColor() : 'bg-bg-tertiary'"
              />
            </div>
            <p class="text-xs text-text-muted">
              Надежность: {{ passwordStrengthText }}
            </p>
            
            <!-- Password requirements -->
            <div class="space-y-1 text-xs">
              <p :class="password.length >= 12 ? 'text-success' : 'text-text-muted'">
                {{ password.length >= 12 ? '✓' : '○' }} Минимум 12 символов
              </p>
              <p :class="hasUpperCase ? 'text-success' : 'text-text-muted'">
                {{ hasUpperCase ? '✓' : '○' }} Заглавная буква
              </p>
              <p :class="hasLowerCase ? 'text-success' : 'text-text-muted'">
                {{ hasLowerCase ? '✓' : '○' }} Строчная буква
              </p>
              <p :class="hasNumber ? 'text-success' : 'text-text-muted'">
                {{ hasNumber ? '✓' : '○' }} Цифра
              </p>
              <p :class="hasSpecialChar ? 'text-success' : 'text-text-muted'">
                {{ hasSpecialChar ? '✓' : '○' }} Специальный символ
              </p>
            </div>
          </div>
        </div>

        <div v-if="mode === 'create'">
          <label class="block text-sm font-medium text-text-secondary mb-2">Подтвердите пароль</label>
          <input
            v-model="passwordConfirm"
            @input="validatePassword"
            type="password"
            class="input-field"
            placeholder="••••••••"
            required
            :class="{ 'border-error': passwordConfirmError }"
          />
          <p v-if="passwordConfirmError" class="text-error text-sm mt-2">{{ passwordConfirmError }}</p>
        </div>

        <div v-if="passwordError" class="bg-error/10 border border-error/30 rounded-lg p-3">
          <p class="text-error text-sm">{{ passwordError }}</p>
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
import { ref, computed, onMounted } from 'vue'

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
const passwordError = ref('')
const passwordConfirmError = ref('')
const passwordInput = ref<HTMLInputElement | null>(null)

// Password strength validation
const hasUpperCase = computed(() => /[A-ZА-Я]/.test(password.value))
const hasLowerCase = computed(() => /[a-zа-я]/.test(password.value))
const hasNumber = computed(() => /[0-9]/.test(password.value))
const hasSpecialChar = computed(() => /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(password.value))

const passwordStrength = computed(() => {
  let score = 0
  if (password.value.length >= 12) score++
  if (hasUpperCase.value && hasLowerCase.value) score++
  if (hasNumber.value) score++
  if (hasSpecialChar.value) score++
  return score
})

const passwordStrengthText = computed(() => {
  if (passwordStrength.value >= 4) return 'Отличный'
  if (passwordStrength.value >= 3) return 'Хороший'
  if (passwordStrength.value >= 2) return 'Средний'
  if (passwordStrength.value >= 1) return 'Слабый'
  return 'Очень слабый'
})

function getStrengthColor() {
  if (passwordStrength.value >= 4) return 'bg-success'
  if (passwordStrength.value >= 3) return 'bg-warning'
  return 'bg-error'
}

function validatePassword() {
  passwordError.value = ''
  passwordConfirmError.value = ''
  
  if (props.mode === 'unlock') return
  
  // Check minimum length
  if (password.value.length < 12) {
    passwordError.value = 'Пароль должен содержать минимум 12 символов'
    return
  }
  
  if (password.value.length > 128) {
    passwordError.value = 'Пароль не может быть длиннее 128 символов'
    return
  }
  
  // Check character classes (need at least 3 of 4)
  let charClasses = 0
  if (hasUpperCase.value) charClasses++
  if (hasLowerCase.value) charClasses++
  if (hasNumber.value) charClasses++
  if (hasSpecialChar.value) charClasses++
  
  if (charClasses < 3) {
    passwordError.value = 'Пароль должен содержать как минимум 3 из 4 типов символов (заглавные, строчные, цифры, специальные)'
    return
  }
  
  // Check common weak passwords
  const weakPasswords = ['password', '123456789012', 'qwerty12345678', 'abcdef12345678']
  if (weakPasswords.includes(password.value.toLowerCase())) {
    passwordError.value = 'Этот пароль слишком простой, используйте другой'
    return
  }
  
  // Check confirmation
  if (props.mode === 'create' && passwordConfirm.value) {
    if (password.value !== passwordConfirm.value) {
      passwordConfirmError.value = 'Пароли не совпадают'
    }
  }
}

onMounted(() => {
  passwordInput.value?.focus()
})

function handleSubmit() {
  validatePassword()
  
  if (passwordError.value) return
  
  if (props.mode === 'create' && password.value !== passwordConfirm.value) {
    error.value = 'Пароли не совпадают'
    return
  }

  if (password.value.length < 12) {
    error.value = 'Пароль должен содержать минимум 12 символов'
    return
  }

  emit('success')
}
</script>
