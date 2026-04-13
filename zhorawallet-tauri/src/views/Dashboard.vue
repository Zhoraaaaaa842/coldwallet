<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-title text-text-primary">Кошелёк</h1>
      <p class="text-text-secondary mt-1">Управление ETH кошельком</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Balance Card -->
      <div class="lg:col-span-2 card-balance">
        <div class="space-y-4">
          <div>
            <p class="text-text-secondary text-sm">Баланс</p>
            <p class="text-balance-rub text-text-primary mt-1">
              {{ walletStore.balanceRub }} ₽
            </p>
            <p class="text-balance-eth text-text-secondary mt-1">
              {{ walletStore.balanceEth }} ETH
            </p>
          </div>

          <!-- Address -->
          <div 
            class="flex items-center gap-2 bg-bg-tertiary rounded-xl px-4 py-3 cursor-pointer hover:bg-bg-hover transition-colors"
            @click="copyAddress"
          >
            <span class="mono-text text-text-secondary flex-1">{{ displayAddress }}</span>
            <svg class="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-3">
            <button @click="router.push('/receive')" class="btn-primary flex-1">
              Получить
            </button>
            <button @click="router.push('/send')" class="btn-primary flex-1">
              Отправить
            </button>
            <button @click="refreshBalance" class="btn-secondary" :disabled="loading">
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
              class="btn-secondary"
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
        <div class="card">
          <p class="text-text-muted text-sm">Nonce</p>
          <p class="text-2xl font-bold text-text-primary mt-1">{{ walletStore.state.nonce }}</p>
        </div>
        
        <div class="card">
          <p class="text-text-muted text-sm">Сеть</p>
          <p class="text-lg font-semibold text-text-primary mt-1">{{ walletStore.state.network }}</p>
        </div>

        <div class="card">
          <p class="text-text-muted text-sm">Цена ETH</p>
          <p class="text-2xl font-bold text-text-primary mt-1">{{ walletStore.priceData.ethRub }} ₽</p>
          <p class="text-xs text-text-muted mt-1">
            Обновлено: {{ formatTime(walletStore.priceData.lastUpdated) }}
          </p>
        </div>

        <div class="card">
          <div class="flex items-center gap-2">
            <div 
              class="w-3 h-3 rounded-full" 
              :class="walletStore.usbStatus === 'connected' ? 'bg-success' : 'bg-error'"
            ></div>
            <p class="text-text-secondary">
              {{ walletStore.usbStatus === 'connected' ? 'USB подключен' : 'USB отключен' }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Transaction History -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xl font-bold text-text-primary">История транзакций</h2>
        
        <!-- Filter Chips -->
        <div class="flex gap-2">
          <button
            v-for="filter in ['Все', 'Входящие', 'Исходящие']"
            :key="filter"
            @click="currentFilter = filter"
            :class="[
              'px-4 py-2 rounded-xl text-sm font-medium transition-colors',
              currentFilter === filter
                ? 'bg-accent text-white'
                : 'bg-bg-tertiary text-text-secondary hover:bg-bg-hover'
            ]"
          >
            {{ filter }}
          </button>
        </div>
      </div>

      <div class="space-y-2">
        <div v-if="filteredTransactions.length === 0" class="text-center py-12 text-text-muted">
          <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p>Транзакции не найдены</p>
        </div>

        <template v-else v-for="(tx, index) in filteredTransactions" :key="tx.hash + index">
          <!-- Date Header -->
          <div v-if="shouldShowDate(tx)" class="text-sm text-text-muted mt-4 mb-2">
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
import TransactionItem from '@/components/TransactionItem.vue'
import type { Transaction } from '@/types'

const router = useRouter()
const walletStore = useWalletStore()

const loading = ref(false)
const currentFilter = ref('Все')

const displayAddress = computed(() => {
  if (!walletStore.state.address) return '0x...'
  const addr = walletStore.state.address
  return `${addr.slice(0, 10)}...${addr.slice(-8)}`
})

const filteredTransactions = computed(() => {
  if (currentFilter.value === 'Все') return walletStore.transactions
  if (currentFilter.value === 'Входящие') 
    return walletStore.transactions.filter(tx => tx.type === 'incoming')
  if (currentFilter.value === 'Исходящие')
    return walletStore.transactions.filter(tx => tx.type === 'outgoing')
  return walletStore.transactions
})

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
  } catch (error) {
    console.error('Failed to copy address:', error)
  }
}

async function refreshBalance() {
  loading.value = true
  try {
    await Promise.all([
      walletStore.fetchBalance(),
      walletStore.fetchNonce(),
      walletStore.fetchTransactions(),
    ])
  } finally {
    loading.value = false
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
