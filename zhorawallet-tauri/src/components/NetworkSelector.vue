<template>
  <div class="relative">
    <button
      @click="isOpen = !isOpen"
      class="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-all duration-200 text-text-primary hover:text-white"
    >
      <Globe class="w-4 h-4" />
      <span class="text-sm font-medium">{{ walletStore.currentNetwork?.name || 'Select Network' }}</span>
      <ChevronDown :class="['w-4 h-4 transition-transform', isOpen ? 'rotate-180' : '']" />
    </button>

    <!-- Dropdown -->
    <div
      v-if="isOpen"
      class="absolute bottom-full left-0 mb-2 w-72 bg-bg-secondary border border-border rounded-lg shadow-2xl overflow-hidden z-50"
    >
      <div class="p-2 border-b border-border">
        <p class="text-xs font-semibold text-text-muted uppercase tracking-wide px-3 py-1">Networks</p>
      </div>
      <div class="max-h-64 overflow-y-auto">
        <button
          v-for="network in walletStore.availableNetworks"
          :key="network.id"
          @click="selectNetwork(network)"
          :class="[
            'w-full px-4 py-3 flex items-center gap-3 hover:bg-bg-hover transition-colors',
            walletStore.currentNetwork?.id === network.id ? 'bg-white/10' : ''
          ]"
        >
          <div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {{ getNetworkIcon(network.networkType) }}
          </div>
          <div class="flex-1 text-left">
            <p class="text-sm font-medium text-text-primary">{{ network.name }}</p>
            <p class="text-xs text-text-muted">Chain ID: {{ network.chainId }}</p>
          </div>
          <Check v-if="walletStore.currentNetwork?.id === network.id" class="w-4 h-4 text-green-500" />
        </button>
      </div>
    </div>

    <!-- Backdrop -->
    <div v-if="isOpen" @click="isOpen = false" class="fixed inset-0 z-40" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useWalletStore } from '@/stores/wallet'
import type { Network } from '@/types'
import { Globe, ChevronDown, Check } from 'lucide-vue-next'

const walletStore = useWalletStore()
const isOpen = ref(false)

async function selectNetwork(network: Network) {
  try {
    await walletStore.switchNetwork(network.id)
    isOpen.value = false
  } catch (error) {
    console.error('Failed to switch network:', error)
  }
}

function getNetworkIcon(networkType: string): string {
  const icons: Record<string, string> = {
    Ethereum: 'Ξ',
    Polygon: 'P',
    BSC: 'B',
    Arbitrum: 'A',
    Optimism: 'O',
  }
  return icons[networkType] || 'N'
}
</script>
