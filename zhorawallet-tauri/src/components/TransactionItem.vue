<template>
  <div 
    class="flex items-center gap-4 p-4 rounded-xl bg-bg-tertiary hover:bg-bg-hover transition-colors cursor-pointer"
    @click="openEtherscan"
  >
    <!-- Arrow Icon -->
    <div
      class="w-10 h-10 rounded-full flex items-center justify-center"
      :class="(transaction.type === 'incoming' || transaction.tx_type === 'incoming') ? 'bg-success/20' : 'bg-error/20'"
    >
      <svg v-if="transaction.type === 'incoming' || transaction.tx_type === 'incoming'" class="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
      <svg v-else class="w-5 h-5 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
    </div>

    <!-- Info -->
    <div class="flex-1 min-w-0">
      <p class="mono-text text-text-primary truncate">
        {{ txType === 'incoming' ? transaction.from : transaction.to }}
      </p>
      <p class="text-xs text-text-muted mt-1">
        {{ formatTimestamp(transaction.timestamp) }}
      </p>
    </div>

    <!-- Amount -->
    <div class="text-right">
      <p
        class="font-semibold"
        :class="txType === 'incoming' ? 'text-success' : 'text-error'"
      >
        {{ txType === 'incoming' ? '+' : '-' }}{{ formatEth(transaction.value) }} ETH
      </p>
      <p class="text-sm text-text-secondary">
        ≈ {{ calculateRub(transaction.value) }} ₽
      </p>
    </div>

    <!-- Status -->
    <div class="flex items-center gap-2">
      <div 
        class="w-2 h-2 rounded-full"
        :class="{
          'bg-success': transaction.status === 'confirmed',
          'bg-warning': transaction.status === 'pending',
          'bg-error': transaction.status === 'failed',
        }"
      ></div>
      <span class="text-xs text-text-muted capitalize">{{ transaction.status }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineProps } from 'vue'
import type { Transaction } from '@/types'
import { useWalletStore } from '@/stores/wallet'

const props = defineProps<{
  transaction: Transaction
}>()

const walletStore = useWalletStore()

// Support both type and tx_type fields
const txType = computed(() => props.transaction.tx_type || props.transaction.type)

function formatTimestamp(timestamp: number): string {
  return new Date(timestamp * 1000).toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatEth(wei: string): string {
  const eth = parseFloat(wei) / 1e18
  return eth.toFixed(6)
}

function calculateRub(wei: string): string {
  const eth = parseFloat(wei) / 1e18
  const rub = eth * walletStore.priceData.ethRub
  return rub.toFixed(2)
}

function openEtherscan() {
  if (!props.transaction.hash) return
  window.open(`https://etherscan.io/tx/${props.transaction.hash}`, '_blank')
}
</script>
