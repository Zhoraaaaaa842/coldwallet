<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-title text-text-primary">Настройки</h1>
      <p class="text-text-secondary mt-1">Управление кошельком и параметрами</p>
    </div>

    <div class="max-w-2xl space-y-6">
      <!-- Wallet Info -->
      <div class="card space-y-4">
        <h2 class="text-lg font-bold text-text-primary">Информация о кошельке</h2>
        
        <div class="space-y-3">
          <div>
            <p class="text-sm text-text-secondary">Адрес:</p>
            <p class="mono-text text-sm mt-1">{{ walletStore.state.address || 'Не инициализирован' }}</p>
          </div>

          <div>
            <p class="text-sm text-text-secondary">Статус:</p>
            <div class="flex items-center gap-2 mt-1">
              <div 
                class="w-2 h-2 rounded-full" 
                :class="walletStore.state.isLocked ? 'bg-error' : 'bg-success'"
              ></div>
              <span>{{ walletStore.state.isLocked ? 'Заблокирован' : 'Разблокирован' }}</span>
            </div>
          </div>

          <div>
            <p class="text-sm text-text-secondary">Сеть:</p>
            <p class="font-semibold text-text-primary mt-1">{{ walletStore.state.network }}</p>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="card space-y-4">
        <h2 class="text-lg font-bold text-text-primary">Действия</h2>
        
        <div class="space-y-3">
          <button
            @click="lockWallet"
            class="btn-secondary w-full"
            :disabled="walletStore.state.isLocked"
          >
            Заблокировать кошелёк
          </button>

          <button
            @click="showBackupMnemonic = true"
            class="btn-secondary w-full"
            :disabled="walletStore.state.isLocked"
          >
            Резервная копия мнемонической фразы
          </button>

          <button
            @click="exportWalletData"
            class="btn-secondary w-full"
            :disabled="walletStore.state.isLocked"
          >
            Экспорт данных кошелька
          </button>
        </div>
      </div>

      <!-- RPC Settings -->
      <div class="card space-y-4">
        <h2 class="text-lg font-bold text-text-primary">Настройки RPC</h2>
        
        <div>
          <label class="block text-sm text-text-secondary mb-2">RPC URL</label>
          <input
            v-model="rpcUrl"
            type="text"
            class="input-field"
            placeholder="https://eth.llamarpc.com"
          />
        </div>

        <button @click="saveRpcSettings" class="btn-primary">
          Сохранить
        </button>
      </div>

      <!-- About -->
      <div class="card space-y-4">
        <h2 class="text-lg font-bold text-text-primary">О приложении</h2>
        
        <div class="space-y-2 text-sm">
          <p class="text-text-secondary">
            <span class="text-text-primary font-semibold">ZhoraWallet</span> v1.0.0
          </p>
          <p class="text-text-muted">
            Холодный кошелёк Ethereum с air-gapped подписью через USB
          </p>
          <p class="text-text-muted">
            Tauri + Vue.js + Rust
          </p>
        </div>
      </div>
    </div>

    <!-- Backup Mnemonic Dialog -->
    <div v-if="showBackupMnemonic" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-bg-secondary rounded-2xl border border-border p-6 w-[32rem]">
        <h2 class="text-xl font-bold text-text-primary mb-4">⚠️ Важное предупреждение</h2>
        
        <p class="text-warning text-sm mb-4">
          Никогда не показывайте мнемоническую фразу кому-либо и не храните её в цифровом виде.
          Запишите её на бумаге и храните в безопасном месте.
        </p>

        <button @click="showMnemonic" class="btn-primary w-full mb-4">
          Я понимаю риск, показать фразу
        </button>

        <div v-if="mnemonic" class="p-4 bg-bg-tertiary rounded-xl mb-4">
          <p class="text-sm text-text-secondary mb-2">Ваша мнемоническая фраза (24 слова):</p>
          <p class="mono-text text-lg text-text-primary">{{ mnemonic }}</p>
        </div>

        <button @click="showBackupMnemonic = false" class="btn-secondary w-full">
          Закрыть
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useWalletStore } from '@/stores/wallet'
import { invoke } from '@tauri-apps/api/core'

const walletStore = useWalletStore()

const rpcUrl = ref('https://eth.llamarpc.com')
const showBackupMnemonic = ref(false)
const mnemonic = ref('')

function lockWallet() {
  walletStore.lockWallet()
}

async function showMnemonic() {
  try {
    mnemonic.value = await invoke<string>('get_mnemonic')
  } catch (error: any) {
    console.error('Failed to get mnemonic:', error)
  }
}

async function exportWalletData() {
  try {
    const data = {
      address: walletStore.state.address,
      network: walletStore.state.network,
      nonce: walletStore.state.nonce,
      exportedAt: new Date().toISOString(),
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'wallet_data.json'
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to export wallet data:', error)
  }
}

function saveRpcSettings() {
  // In a real implementation, we would save this to Tauri store
  localStorage.setItem('rpc_url', rpcUrl.value)
  alert('RPC настройки сохранены')
}

onMounted(() => {
  const savedRpc = localStorage.getItem('rpc_url')
  if (savedRpc) {
    rpcUrl.value = savedRpc
  }
})
</script>
