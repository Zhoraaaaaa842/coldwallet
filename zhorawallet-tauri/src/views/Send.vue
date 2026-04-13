<template>
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-4xl font-black text-white tracking-tight">Отправить ETH</h1>
      <p class="text-text-secondary mt-2">Создание транзакции для отправки</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Send Form -->
      <div class="card space-y-6">
        <!-- Recipient Address -->
        <div>
          <label class="block text-sm text-text-secondary mb-2">Адрес получателя</label>
          <input
            v-model="recipientAddress"
            type="text"
            class="input-field"
            placeholder="0x..."
            :class="{ 'border-error': errors.address }"
            @input="validateAddress"
          />
          <p v-if="errors.address" class="text-error text-sm mt-2">{{ errors.address }}</p>
        </div>

        <!-- Amount -->
        <div>
          <label class="block text-sm text-text-secondary mb-2">Сумма (ETH)</label>
          <input
            v-model.number="amount"
            type="number"
            class="input-field"
            placeholder="0.0"
            step="0.00000001"
            min="0"
            :class="{ 'border-error': errors.amount }"
          />
          <p v-if="errors.amount" class="text-error text-sm mt-2">{{ errors.amount }}</p>
          <p class="text-xs text-text-muted mt-2">
            Доступно: {{ walletStore.balanceEth }} ETH
          </p>
        </div>

        <!-- Max Button -->
        <button
          @click="setMaxAmount"
          class="btn-secondary w-full"
          :disabled="!walletStore.balanceEth || parseFloat(walletStore.balanceEth) === 0"
        >
          Максимум
        </button>
      </div>

      <!-- Gas Settings -->
      <div class="card space-y-4">
        <h2 class="text-lg font-bold text-text-primary">Настройки газа</h2>

        <!-- Fetch Gas Button -->
        <button
          @click="fetchCurrentGas"
          class="btn-secondary w-full"
          :disabled="loading"
        >
          <svg v-if="loading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Получить текущий газ
        </button>

        <!-- Transaction Type -->
        <div>
          <label class="block text-sm text-text-secondary mb-2">Тип транзакции</label>
          <select
            v-model="walletStore.currentGasSettings.type"
            class="input-field"
          >
            <option value="eip1559">EIP-1559 (рекомендуется)</option>
            <option value="legacy">Legacy</option>
          </select>
        </div>

        <!-- EIP-1559 Settings -->
        <template v-if="walletStore.currentGasSettings.type === 'eip1559'">
          <div>
            <label class="block text-sm text-text-secondary mb-2">Max Fee (Gwei)</label>
            <input
              v-model.number="walletStore.currentGasSettings.maxFeePerGas"
              type="number"
              class="input-field"
              step="0.1"
              min="0"
            />
          </div>

          <div>
            <label class="block text-sm text-text-secondary mb-2">Priority Fee (Gwei)</label>
            <input
              v-model.number="walletStore.currentGasSettings.maxPriorityFeePerGas"
              type="number"
              class="input-field"
              step="0.1"
              min="0"
            />
          </div>
        </template>

        <!-- Legacy Settings -->
        <template v-else>
          <div>
            <label class="block text-sm text-text-secondary mb-2">Gas Price (Gwei)</label>
            <input
              v-model.number="walletStore.currentGasSettings.gasPrice"
              type="number"
              class="input-field"
              step="0.1"
              min="0"
            />
          </div>
        </template>

        <!-- Gas Limit -->
        <div>
          <label class="block text-sm text-text-secondary mb-2">Gas Limit</label>
          <input
            v-model.number="walletStore.currentGasSettings.gasLimit"
            type="number"
            class="input-field"
            min="21000"
            step="1"
          />
        </div>

        <!-- Estimated Fee -->
        <div class="p-4 bg-bg-tertiary rounded-xl">
          <p class="text-sm text-text-secondary">
            Примерная комиссия: <span class="font-semibold text-text-primary">{{ estimatedFee }} ETH</span>
          </p>
        </div>
      </div>
    </div>

    <!-- Submit Button -->
    <div class="flex justify-center">
      <button
        @click="createTransaction"
        class="btn-primary px-12 py-4 text-lg"
        :disabled="!canSubmit || loading"
      >
        <svg v-if="loading" class="w-6 h-6 animate-spin inline mr-2" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        Создать TX >> USB
      </button>
    </div>

    <!-- Error/Success Messages -->
    <div v-if="submitError" class="card bg-error/10 border-error">
      <p class="text-error">{{ submitError }}</p>
    </div>

    <div v-if="submitSuccess" class="card bg-success/10 border-success">
      <p class="text-success">Транзакция успешно создана и сохранена на USB!</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useWalletStore } from '@/stores/wallet'
import { useNotification } from '@/composables/useNotification'
import { invoke } from '@tauri-apps/api/core'

const route = useRoute()
const walletStore = useWalletStore()
const { success, error: showError } = useNotification()

const recipientAddress = ref('')
const amount = ref(0)
const loading = ref(false)
const submitError = ref('')
const submitSuccess = ref(false)
const errors = ref<{ address?: string; amount?: string }>({})

const canSubmit = computed(() => {
  return recipientAddress.value && 
         amount.value > 0 && 
         !errors.value.address && 
         !errors.value.amount &&
         walletStore.isWalletReady
})

const estimatedFee = computed(() => {
  const gas = walletStore.currentGasSettings
  let feeGwei = 0
  
  if (gas.type === 'eip1559') {
    feeGwei = (gas.maxFeePerGas || 0) * gas.gasLimit
  } else {
    feeGwei = (gas.gasPrice || 0) * gas.gasLimit
  }
  
  return (feeGwei / 1e9).toFixed(8)
})

function validateAddress() {
  const addr = recipientAddress.value.trim()
  if (!addr) {
    errors.value.address = ''
    return
  }
  
  if (!addr.startsWith('0x')) {
    errors.value.address = 'Адрес должен начинаться с 0x'
    return
  }
  
  if (addr.length !== 42) {
    errors.value.address = 'Неверная длина адреса'
    return
  }
  
  if (!addr.match(/^0x[0-9a-fA-F]{40}$/)) {
    errors.value.address = 'Неверный формат адреса'
    return
  }
  
  errors.value.address = ''
}

function setMaxAmount() {
  const balance = parseFloat(walletStore.balanceEth)
  const fee = parseFloat(estimatedFee.value)
  const maxAmount = Math.max(0, balance - fee)
  amount.value = maxAmount
}

async function fetchCurrentGas() {
  loading.value = true
  try {
    const gasData = await invoke<any>('fetch_gas_settings')
    walletStore.currentGasSettings = {
      type: 'eip1559',
      gasLimit: 21000,
      maxFeePerGas: gasData.maxFeePerGas,
      maxPriorityFeePerGas: gasData.maxPriorityFeePerGas,
    }
    success('Настройки газа обновлены')
  } catch (error: any) {
    submitError.value = 'Не удалось получить настройки газа: ' + error
    showError('Не удалось получить настройки газа')
  } finally {
    loading.value = false
  }
}

async function createTransaction() {
  submitError.value = ''
  submitSuccess.value = false

  if (!canSubmit.value) {
    submitError.value = 'Заполните все поля корректно'
    showError('Заполните все поля корректно')
    return
  }

  loading.value = true
  try {
    await invoke('create_unsigned_transaction', {
      to: recipientAddress.value,
      amount: amount.value.toString(),
      gasSettings: walletStore.currentGasSettings,
      nonce: walletStore.state.nonce,
    })

    submitSuccess.value = true
    success('Транзакция создана и сохранена на USB!')

    // Clear form
    recipientAddress.value = ''
    amount.value = 0

    // Refresh balance after 2 seconds
    setTimeout(() => {
      walletStore.fetchBalance()
    }, 2000)
  } catch (error: any) {
    submitError.value = 'Ошибка создания транзакции: ' + error
    showError('Ошибка создания транзакции')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // Pre-fill from query params (from QR scan)
  if (route.query.to) {
    recipientAddress.value = route.query.to as string
    validateAddress()
  }
  if (route.query.amount) {
    amount.value = parseFloat(route.query.amount as string)
  }

  fetchCurrentGas()
})
</script>
