<template>
  <div class="flex h-screen bg-bg-primary relative">
    <!-- Animated Background -->
    <ParticlesBackground />

    <!-- Custom Title Bar -->
    <TitleBar />

    <!-- Sidebar -->
    <aside class="w-64 bg-bg-secondary border-r border-border flex flex-col pt-12 relative z-10">
      <!-- Wallet Info -->
      <div class="p-6 border-b border-border">
        <div class="space-y-3">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 bg-white rounded-lg flex items-center justify-center">
              <svg class="w-5 h-5 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <div>
              <h2 class="text-sm font-bold text-text-primary">Cold Wallet</h2>
              <p class="text-xs text-text-muted">Ethereum</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-1">
        <button
          v-for="item in navItems"
          :key="item.path"
          @click="navigateTo(item.path)"
          :class="[
            'w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group relative',
            route.path === item.path
              ? 'bg-white text-black'
              : 'text-text-secondary hover:bg-bg-hover hover:text-white'
          ]"
        >
          <component :is="item.icon" class="w-5 h-5" />
          <span class="font-semibold text-sm">{{ item.label }}</span>
          <div
            v-if="route.path === item.path"
            class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-white rounded-r"
          ></div>
        </button>
      </nav>

      <!-- Network & Version -->
      <div class="p-4 border-t border-border space-y-3">
        <NetworkSelector />
        <div class="text-xs text-text-muted space-y-1">
          <p>v1.0.0</p>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto pt-12 relative z-10">
      <div class="p-8 max-w-7xl mx-auto">
        <router-view />
      </div>
    </main>

    <!-- Notification Container -->
    <NotificationContainer />

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
import { Send, QrCode, Shield, Settings, Home, Users } from 'lucide-vue-next'
import TitleBar from '@/components/TitleBar.vue'
import ParticlesBackground from '@/components/ParticlesBackground.vue'
import NotificationContainer from '@/components/NotificationContainer.vue'
import PasswordDialog from '@/components/PasswordDialog.vue'
import WalletInitDialog from '@/components/WalletInitDialog.vue'
import NetworkSelector from '@/components/NetworkSelector.vue'

const route = useRoute()
const router = useRouter()
const walletStore = useWalletStore()

const navItems = [
  { path: '/', label: 'Кошелёк', icon: Home },
  { path: '/send', label: 'Отправить', icon: Send },
  { path: '/receive', label: 'Получить', icon: QrCode },
  { path: '/contacts', label: 'Контакты', icon: Users },
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
  // Load networks
  await walletStore.loadNetworks()
  await walletStore.loadCurrentNetwork()
  
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
