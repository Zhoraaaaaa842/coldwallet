<template>
  <div class="flex h-screen bg-bg-primary">
    <!-- Sidebar -->
    <aside class="w-64 bg-bg-secondary border-r border-border flex flex-col">
      <!-- Logo -->
      <div class="p-6 border-b border-border">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-accent rounded-xl flex items-center justify-center">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <div>
            <h1 class="text-xl font-bold text-text-primary">ZhoraWallet</h1>
            <div class="flex items-center gap-2">
              <div 
                class="w-2 h-2 rounded-full" 
                :class="walletStore.usbStatus === 'connected' ? 'bg-success' : 'bg-error'"
              ></div>
              <span class="text-xs text-text-muted">
                {{ walletStore.usbStatus === 'connected' ? 'USB подключен' : 'USB отключен' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-2">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="navigateTo(item.path)"
          :class="[
            'w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200',
            route.path === item.path 
              ? 'bg-accent text-white' 
              : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
          ]"
        >
          <component :is="item.icon" class="w-5 h-5" />
          <span class="font-medium">{{ item.label }}</span>
        </button>
      </nav>

      <!-- Network & Version -->
      <div class="p-4 border-t border-border">
        <div class="text-xs text-text-muted space-y-1">
          <p>{{ walletStore.state.network }}</p>
          <p>v1.0.0</p>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto">
      <div class="p-8">
        <router-view />
      </div>
    </main>

    <!-- Password Dialog -->
    <PasswordDialog
      v-if="showPasswordDialog"
      :mode="passwordDialogMode"
      @success="onPasswordSuccess"
      @cancel="showPasswordDialog = false"
    />

    <!-- Wallet Init Dialog -->
    <WalletInitDialog
      v-if="showWalletInitDialog"
      @create="handleCreateWallet"
      @import="handleImportWallet"
      @cancel="showWalletInitDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useWalletStore } from '@/stores/wallet'
import { Send, QrCode, Shield, Settings, Home } from 'lucide-vue-next'
import PasswordDialog from '@/components/PasswordDialog.vue'
import WalletInitDialog from '@/components/WalletInitDialog.vue'

const route = useRoute()
const router = useRouter()
const walletStore = useWalletStore()

const navItems = [
  { path: '/', label: 'Кошелёк', icon: Home },
  { path: '/send', label: 'Отправить', icon: Send },
  { path: '/receive', label: 'Получить', icon: QrCode },
  { path: '/sign', label: 'Подписать', icon: Shield },
  { path: '/settings', label: 'Настройки', icon: Settings },
]

function navigateTo(path: string) {
  router.push(path)
}

const showPasswordDialog = ref(false)
const passwordDialogMode = ref<'unlock' | 'create' | 'import'>('unlock')
const showWalletInitDialog = ref(false)

function onPasswordSuccess() {
  showPasswordDialog.value = false
  walletStore.fetchBalance()
  walletStore.fetchNonce()
  walletStore.fetchTransactions()
  walletStore.fetchEthPrice()
}

async function handleCreateWallet(password: string) {
  try {
    await walletStore.initializeWallet(password)
    showWalletInitDialog.value = false
    walletStore.fetchEthPrice()
  } catch (error) {
    console.error('Failed to create wallet:', error)
  }
}

async function handleImportWallet(mnemonic: string, password: string) {
  try {
    await walletStore.importFromMnemonic(mnemonic, password)
    showWalletInitDialog.value = false
    walletStore.fetchEthPrice()
  } catch (error) {
    console.error('Failed to import wallet:', error)
  }
}

onMounted(async () => {
  // Check if wallet exists
  try {
    await walletStore.checkUsbStatus()
    if (!walletStore.state.isInitialized) {
      showWalletInitDialog.value = true
    } else if (walletStore.state.isLocked) {
      passwordDialogMode.value = 'unlock'
      showPasswordDialog.value = true
    }
  } catch (error) {
    console.error('Failed to check wallet status:', error)
  }
})
</script>
