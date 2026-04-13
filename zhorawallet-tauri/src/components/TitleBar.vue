<template>
  <div
    class="fixed top-0 left-0 right-0 h-12 flex items-center justify-between px-4 z-50 bg-gradient-to-b from-black/80 via-black/40 to-transparent backdrop-blur-md border-b border-white/5"
    style="-webkit-app-region: drag; app-region: drag;"
  >
    <!-- Left: Logo & Title -->
    <div class="flex items-center gap-3" style="-webkit-app-region: drag; app-region: drag;">
      <div class="w-6 h-6 bg-white rounded-md flex items-center justify-center">
        <svg class="w-4 h-4 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      </div>
      <span class="text-sm font-semibold text-white tracking-wide">ZHORAWALLET</span>
    </div>

    <!-- Center: USB Status -->
    <div class="flex items-center gap-2" style="-webkit-app-region: drag; app-region: drag;">
      <div
        class="w-1.5 h-1.5 rounded-full transition-colors duration-300"
        :class="usbConnected ? 'bg-success shadow-[0_0_8px_rgba(0,210,106,0.6)]' : 'bg-error/50'"
      ></div>
      <span class="text-xs text-text-secondary font-medium">
        {{ usbConnected ? 'USB Connected' : 'USB Disconnected' }}
      </span>
    </div>

    <!-- Right: Window Controls -->
    <div class="flex items-center gap-1" style="-webkit-app-region: no-drag; app-region: no-drag;">
      <button
        @click.stop="minimizeWindow"
        class="w-11 h-8 flex items-center justify-center hover:bg-white/10 transition-colors duration-150 rounded group cursor-pointer"
        type="button"
      >
        <svg class="w-4 h-4 text-text-secondary group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
        </svg>
      </button>
      <button
        @click.stop="maximizeWindow"
        class="w-11 h-8 flex items-center justify-center hover:bg-white/10 transition-colors duration-150 rounded group cursor-pointer"
        type="button"
      >
        <svg class="w-3.5 h-3.5 text-text-secondary group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V6a2 2 0 012-2h2M4 16v2a2 2 0 002 2h2m8-16h2a2 2 0 012 2v2m-4 12h2a2 2 0 002-2v-2" />
        </svg>
      </button>
      <button
        @click.stop="closeWindow"
        class="w-11 h-8 flex items-center justify-center hover:bg-error transition-colors duration-150 rounded group cursor-pointer"
        type="button"
      >
        <svg class="w-4 h-4 text-text-secondary group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWalletStore } from '@/stores/wallet'
import { getCurrentWindow } from '@tauri-apps/api/window'

const walletStore = useWalletStore()

const usbConnected = computed(() => walletStore.usbStatus === 'connected')

async function minimizeWindow() {
  try {
    const window = getCurrentWindow()
    await window.minimize()
  } catch (error) {
    console.error('Failed to minimize:', error)
  }
}

async function maximizeWindow() {
  try {
    const window = getCurrentWindow()
    await window.toggleMaximize()
  } catch (error) {
    console.error('Failed to maximize:', error)
  }
}

async function closeWindow() {
  try {
    const window = getCurrentWindow()
    await window.close()
  } catch (error) {
    console.error('Failed to close:', error)
  }
}
</script>
