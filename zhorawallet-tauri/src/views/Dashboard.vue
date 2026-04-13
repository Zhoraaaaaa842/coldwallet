<template>
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-4xl font-black text-white tracking-tight">Кошелёк</h1>
      <p class="text-text-secondary mt-2">Управление вашим Ethereum кошельком</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Balance Card -->
      <div class="lg:col-span-2 card-balance relative overflow-hidden">
        <!-- Subtle gradient overlay -->
        <div class="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent pointer-events-none"></div>

        <div class="relative space-y-6">
          <div>
            <p class="text-text-muted text-sm font-medium uppercase tracking-wider">Баланс</p>
            <p class="text-balance-rub text-white mt-2 font-black tracking-tight">
              {{ walletStore.balanceRub }} ₽
            </p>
            <p class="text-balance-eth text-text-secondary mt-1 font-bold">
              {{ walletStore.balanceEth }} ETH
            </p>
          </div>

          <!-- Address -->
          <div
            class="flex items-center gap-3 bg-black/40 rounded-lg px-4 py-3 cursor-pointer hover:bg-black/60 transition-all duration-200 border border-border group"
            @click="copyAddress"
          >
            <span class="mono-text text-text-secondary flex-1 text-sm">{{ displayAddress }}</span>
            <svg class="w-4 h-4 text-text-muted group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-3">
            <button @click="router.push('/receive')" class="flex-1 bg-white hover:bg-gray-200 text-black font-semibold px-6 py-3 rounded-lg transition-all duration-200">
              Получить
            </button>
            <button @click="router.push('/send')" class="flex-1 bg-white hover:bg-gray-200 text-black font-semibold px-6 py-3 rounded-lg transition-all duration-200">
              Отправить
            </button>
            <button @click="refreshBalance" class="bg-bg-tertiary hover:bg-bg-hover text-white px-4 py-3 rounded-lg transition-colors duration-200" :disabled="loading">
              <svg v-if="loading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
            <button
              @click="openEtherscan"
              class="bg-bg-tertiary hover:bg-bg-hover text-white px-4 py-3 rounded-lg transition-colors duration-200"
              title="Открыть в Etherscan"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Info Cards -->
      <div class="space-y-4">
        <div class="card hover:border-border-light transition-colors duration-200">
          <p class="text-text-muted text-xs font-medium uppercase tracking-wider">Nonce</p>
          <p class="text-3xl font-bold text-white mt-2">{{ walletStore.state.nonce }}</p>
        </div>

        <div class="card hover:border-border-light transition-colors duration-200">
          <p class="text-text-muted text-xs font-medium uppercase tracking-wider">Сеть</p>
          <p class="text-lg font-semibold text-white mt-2">{{ walletStore.currentNetwork?.name || walletStore.state.network }}</p>
        </div>

        <div class="card hover:border-border-light transition-colors duration-200">
          <p class="text-text-muted text-xs font-medium uppercase tracking-wider">Получено</p>
          <p class="text-2xl font-bold text-success mt-2">{{ balanceSummaryData.totalReceived.toFixed(6) }} ETH</p>
          <p class="text-xs text-text-dim mt-1">
            {{ balanceSummaryData.transactionCount }} транзакций
          </p>
        </div>

        <div class="card hover:border-border-light transition-colors duration-200">
          <p class="text-text-muted text-xs font-medium uppercase tracking-wider">Отправлено</p>
          <p class="text-2xl font-bold text-error mt-2">{{ balanceSummaryData.totalSent.toFixed(6) }} ETH</p>
          <p class="text-xs text-text-dim mt-1">
            Обновлено: {{ formatBalanceSummaryLastUpdated() }}
          </p>
        </div>

        <div class="card hover:border-border-light transition-colors duration-200">
          <p class="text-text-muted text-xs font-medium uppercase tracking-wider">Цена ETH</p>
          <p class="text-3xl font-bold text-white mt-2">{{ walletStore.priceData.ethRub }} ₽</p>
          <p class="text-xs text-text-dim mt-2">
            {{ formatTime(walletStore.priceData.lastUpdated) }}
          </p>
        </div>

        <div class="card hover:border-border-light transition-colors duration-200">
          <div class="flex items-center gap-2">
            <div
              class="w-2 h-2 rounded-full transition-all duration-300"
              :class="walletStore.usbStatus === 'connected' ? 'bg-success shadow-[0_0_8px_rgba(0,210,106,0.6)]' : 'bg-error/50'"
            ></div>
            <p class="text-sm text-text-secondary font-medium">
              {{ walletStore.usbStatus === 'connected' ? 'USB Connected' : 'USB Disconnected' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Transaction History -->
    <div class="card">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-2xl font-bold text-white">История транзакций</h2>

        <!-- Filter Chips -->
        <div class="flex gap-2">
          <button
            v-for="filter in ['Все', 'Входящие', 'Исходящие']"
            :key="filter"
            @click="currentFilter = filter"
            :class="[
              'px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200',
              currentFilter === filter
                ? 'bg-white text-black'
                : 'bg-bg-tertiary text-text-secondary hover:bg-bg-hover hover:text-white'
            ]"
          >
            {{ filter }}
          </button>
        </div>
      </div>

      <div class="space-y-2">
        <div v-if="filteredTransactions.length === 0" class="text-center py-16 text-text-muted">
          <svg class="w-20 h-20 mx-auto mb-4 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p class="text-lg">Транзакции не найдены</p>
          <p class="text-sm text-text-dim mt-1">История транзакций появится здесь</p>
        </div>

        <template v-else v-for="(tx, index) in filteredTransactions" :key="tx.hash + index">
          <!-- Date Header -->
          <div v-if="shouldShowDate(tx)" class="text-xs font-semibold text-text-muted uppercase tracking-wider mt-6 mb-3">
            {{ formatDateHeader(tx.timestamp) }}
          </div>

          <!-- Transaction Item -->
          <TransactionItem :transaction="tx" />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWalletStore } from '@/stores/wallet'
import { useNotification } from '@/composables/useNotification'
import TransactionItem from '@/components/TransactionItem.vue'
import type { Transaction, BalanceSummary } from '@/types'

const router = useRouter()
const walletStore = useWalletStore()
const { success, error: showError } = useNotification()

const loading = ref(false)
const currentFilter = ref('Все')
const balanceSummaryData = ref<BalanceSummary>({
  totalReceived: 0,
  totalSent: 0,
  transactionCount: 0,
  lastUpdated: 0,
})

const displayAddress = computed(() => {
  if (!walletStore.state.address) return '0x...'
  const addr = walletStore.state.address
  return `${addr.slice(0, 10)}...${addr.slice(-8)}`
})

const filteredTransactions = computed(() => {
  const txs = walletStore.transactions
  if (currentFilter.value === 'Все') return txs
  
  return txs.filter(tx => {
    const txType = tx.tx_type || tx.type
    if (currentFilter.value === 'Входящие') return txType === 'incoming'
    if (currentFilter.value === 'Исходящие') return txType === 'outgoing'
    return true
  })
})

function formatBalanceSummaryLastUpdated(): string {
  if (!balanceSummaryData.value.lastUpdated) return '-'
  return new Date(balanceSummaryData.value.lastUpdated).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

function shouldShowDate(tx: Transaction): boolean {
  const idx = walletStore.transactions.indexOf(tx)
  if (idx === 0) return true
  const prevTx = walletStore.transactions[idx - 1]
  return getDateKey(tx.timestamp) !== getDateKey(prevTx.timestamp)
}

function getDateKey(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toISOString().split('T')[0]
}

function formatDateHeader(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (date.toDateString() === today.toDateString()) return 'Сегодня'
  if (date.toDateString() === yesterday.toDateString()) return 'Вчера'
  
  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

function formatTime(timestamp: number): string {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function copyAddress() {
  if (!walletStore.state.address) return
  try {
    await navigator.clipboard.writeText(walletStore.state.address)
    success('Адрес скопирован в буфер обмена')
  } catch (error) {
    console.error('Failed to copy address:', error)
    showError('Не удалось скопировать адрес')
  }
}

async function refreshBalance() {
  loading.value = true
  try {
    await Promise.all([
      walletStore.fetchBalance(),
      walletStore.fetchNonce(),
      walletStore.getCachedTransactions(),
      loadBalanceSummary(),
    ])
    success('Данные обновлены')
  } catch (err) {
    showError('Не удалось обновить данные')
  } finally {
    loading.value = false
  }
}

async function loadBalanceSummary() {
  try {
    balanceSummaryData.value = await walletStore.getBalanceSummary()
  } catch (error) {
    console.error('Failed to load balance summary:', error)
  }
}

function openEtherscan() {
  if (!walletStore.state.address) return
  window.open(`https://etherscan.io/address/${walletStore.state.address}`, '_blank')
}

onMounted(() => {
  refreshBalance()
})
</script>
