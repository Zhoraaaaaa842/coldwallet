<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-title text-text-primary">Подписать & Отправить</h1>
      <p class="text-text-secondary mt-1">Управление транзакциями с USB накопителя</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Step 1: Sign Pending -->
      <div class="card">
        <h2 class="text-lg font-bold text-text-primary mb-4">Шаг 1: Подписать транзакции</h2>
        
        <!-- Scan Button -->
        <button
          @click="scanPendingTransactions"
          class="btn-secondary w-full mb-4"
          :disabled="loading"
        >
          <svg v-if="loading" class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Сканировать pending/ на USB
        </button>

        <!-- Pending Transactions List -->
        <div v-if="pendingTransactions.length === 0" class="text-center py-8 text-text-muted">
          <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <p>Нет ожидающих транзакций</p>
        </div>

        <div v-else class="space-y-3">
          <div 
            v-for="tx in pendingTransactions" 
            :key="tx.id"
            class="p-4 bg-bg-tertiary rounded-xl space-y-3"
          >
            <div class="flex items-center justify-between">
              <p class="text-sm text-text-secondary">Транзакция #{{ tx.id }}</p>
              <span class="text-xs text-text-muted">{{ tx.path }}</span>
            </div>

            <div class="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p class="text-text-muted">Получатель:</p>
                <p class="mono-text text-xs mt-1">{{ tx.data.to }}</p>
              </div>
              <div>
                <p class="text-text-muted">Сумма:</p>
                <p class="font-semibold text-text-primary mt-1">{{ tx.data.amount }} ETH</p>
              </div>
              <div>
                <p class="text-text-muted">Nonce:</p>
                <p class="font-semibold text-text-primary mt-1">{{ tx.data.nonce }}</p>
              </div>
            </div>

            <button
              @click="signTransaction(tx)"
              class="btn-primary w-full"
            >
              Подписать
            </button>
          </div>
        </div>
      </div>

      <!-- Step 2: Broadcast Signed -->
      <div class="card">
        <h2 class="text-lg font-bold text-text-primary mb-4">Шаг 2: Отправить в сеть</h2>
        
        <!-- Scan Button -->
        <button
          @click="scanSignedTransactions"
          class="btn-secondary w-full mb-4"
          :disabled="loading"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Сканировать signed/ на USB
        </button>

        <!-- Signed Transactions List -->
        <div v-if="signedTransactions.length === 0" class="text-center py-8 text-text-muted">
          <svg class="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>Нет подписанных транзакций</p>
        </div>

        <div v-else class="space-y-3">
          <div 
            v-for="tx in signedTransactions" 
            :key="tx.id"
            class="p-4 bg-bg-tertiary rounded-xl space-y-3"
          >
            <div class="flex items-center justify-between">
              <p class="text-sm text-text-secondary">Транзакция #{{ tx.id }}</p>
              <span class="text-xs text-text-muted">{{ tx.path }}</span>
            </div>

            <div class="text-sm">
              <p class="text-text-muted">Raw транзакция:</p>
              <p class="mono-text text-xs mt-1 break-all">{{ tx.data.rawTx.slice(0, 66) }}...</p>
            </div>

            <button
              @click="broadcastTransaction(tx)"
              class="btn-primary w-full"
            >
              Отправить в сеть
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Broadcast Log -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-bold text-text-primary">Лог операций</h2>
        <button @click="walletStore.clearBroadcastLog()" class="btn-secondary text-sm">
          Очистить
        </button>
      </div>

      <div class="bg-bg-primary rounded-xl p-4 h-64 overflow-y-auto font-mono text-sm">
        <div v-if="walletStore.broadcastLog.length === 0" class="text-text-muted">
          Нет записей
        </div>
        <div v-else class="space-y-1">
          <div 
            v-for="(log, index) in walletStore.broadcastLog" 
            :key="index"
            class="text-text-secondary"
          >
            {{ log }}
          </div>
        </div>
      </div>
    </div>

    <!-- Confirmation Dialog -->
    <div v-if="showConfirmDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-bg-secondary rounded-2xl border border-border p-6 w-[32rem]">
        <h2 class="text-xl font-bold text-text-primary mb-4">Подтверждение подписи</h2>
        
        <div class="space-y-3 mb-6">
          <div>
            <p class="text-sm text-text-secondary">Получатель:</p>
            <p class="mono-text mt-1">{{ confirmData.to }}</p>
          </div>
          <div>
            <p class="text-sm text-text-secondary">Сумма:</p>
            <p class="text-lg font-semibold text-text-primary mt-1">{{ confirmData.amount }} ETH</p>
          </div>
          <div>
            <p class="text-sm text-text-secondary">Nonce:</p>
            <p class="font-semibold text-text-primary mt-1">{{ confirmData.nonce }}</p>
          </div>
        </div>

        <p class="text-warning text-sm mb-4">
          ⚠️ Вы собираетесь подписать эту транзакцию приватным ключом?
        </p>

        <div class="flex gap-3">
          <button @click="confirmSign" class="btn-primary flex-1">
            Подписать
          </button>
          <button @click="showConfirmDialog = false" class="btn-secondary flex-1">
            Отмена
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useWalletStore } from '@/stores/wallet'
import type { UsbTransaction } from '@/types'
import { invoke } from '@tauri-apps/api/core'

const walletStore = useWalletStore()

const loading = ref(false)
const pendingTransactions = ref<UsbTransaction[]>([])
const signedTransactions = ref<UsbTransaction[]>([])
const showConfirmDialog = ref(false)
const confirmData = ref({ to: '', amount: '', nonce: 0 })
let currentTxToSign: UsbTransaction | null = null

async function scanPendingTransactions() {
  loading.value = true
  try {
    const txs = await invoke<UsbTransaction[]>('scan_pending_transactions')
    pendingTransactions.value = txs
    walletStore.addBroadcastLog(`Найдено ${txs.length} ожидающих транзакций на USB`)
  } catch (error: any) {
    walletStore.addBroadcastLog('Ошибка сканирования pending/: ' + error)
  } finally {
    loading.value = false
  }
}

async function scanSignedTransactions() {
  loading.value = true
  try {
    const txs = await invoke<UsbTransaction[]>('scan_signed_transactions')
    signedTransactions.value = txs
    walletStore.addBroadcastLog(`Найдено ${txs.length} подписанных транзакций на USB`)
  } catch (error: any) {
    walletStore.addBroadcastLog('Ошибка сканирования signed/: ' + error)
  } finally {
    loading.value = false
  }
}

function signTransaction(tx: UsbTransaction) {
  currentTxToSign = tx
  confirmData.value = {
    to: tx.data.to,
    amount: tx.data.amount,
    nonce: tx.data.nonce,
  }
  showConfirmDialog.value = true
}

async function confirmSign() {
  if (!currentTxToSign) return
  
  showConfirmDialog.value = false
  loading.value = true
  
  try {
    walletStore.addBroadcastLog(`Подписание транзакции #${currentTxToSign.id}...`)
    await invoke('sign_transaction', { tx: currentTxToSign })
    walletStore.addBroadcastLog(`Транзакция #${currentTxToSign.id} успешно подписана`)
    
    // Remove from pending list
    pendingTransactions.value = pendingTransactions.value.filter(t => t.id !== currentTxToSign!.id)
    
    // Auto-scan signed
    await scanSignedTransactions()
  } catch (error: any) {
    walletStore.addBroadcastLog('Ошибка подписи: ' + error)
  } finally {
    loading.value = false
    currentTxToSign = null
  }
}

async function broadcastTransaction(tx: UsbTransaction) {
  loading.value = true
  walletStore.addBroadcastLog(`Отправка транзакции #${tx.id} в сеть...`)
  
  try {
    const receipt = await invoke<any>('broadcast_transaction', { 
      rawTx: tx.data.rawTx 
    })
    
    walletStore.addBroadcastLog(`Транзакция #${tx.id} успешно отправлена`)
    walletStore.addBroadcastLog(`Hash: ${receipt.hash}`)
    
    // Remove from signed list
    signedTransactions.value = signedTransactions.value.filter(t => t.id !== tx.id)
    
    // Refresh balance
    setTimeout(() => {
      walletStore.fetchBalance()
      walletStore.fetchTransactions()
    }, 3000)
  } catch (error: any) {
    walletStore.addBroadcastLog('Ошибка отправки: ' + error)
  } finally {
    loading.value = false
  }
}
</script>
