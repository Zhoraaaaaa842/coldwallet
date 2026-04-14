<template>
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-4xl font-black text-white tracking-tight">Настройки</h1>
      <p class="text-text-secondary mt-2">Управление кошельком и параметрами безопасности</p>
    </div>

    <div class="max-w-3xl space-y-6">
      <!-- Wallet Info -->
      <div class="card space-y-5">
        <h2 class="text-xl font-bold text-white">Информация о кошельке</h2>

        <div class="space-y-4">
          <div class="p-4 bg-bg-tertiary rounded-lg">
            <p class="text-xs text-text-muted uppercase tracking-wider mb-2">Адрес кошелька</p>
            <div class="flex items-center gap-3">
              <p class="mono-text text-sm text-white flex-1">{{ walletStore.state.address || 'Не инициализирован' }}</p>
              <button
                v-if="walletStore.state.address"
                @click="copyAddress"
                class="p-2 hover:bg-bg-hover rounded-lg transition-colors"
              >
                <svg class="w-4 h-4 text-text-secondary hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="p-4 bg-bg-tertiary rounded-lg">
              <p class="text-xs text-text-muted uppercase tracking-wider mb-2">Статус</p>
              <div class="flex items-center gap-2">
                <div
                  class="w-2 h-2 rounded-full transition-all duration-300"
                  :class="walletStore.state.isLocked ? 'bg-error/50' : 'bg-success shadow-[0_0_8px_rgba(0,210,106,0.6)]'"
                ></div>
                <span class="text-sm font-semibold text-white">{{ walletStore.state.isLocked ? 'Заблокирован' : 'Разблокирован' }}</span>
              </div>
            </div>

            <div class="p-4 bg-bg-tertiary rounded-lg">
              <p class="text-xs text-text-muted uppercase tracking-wider mb-2">Сеть</p>
              <p class="text-sm font-semibold text-white">{{ walletStore.state.network }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Security Actions -->
      <div class="card space-y-5">
        <h2 class="text-xl font-bold text-white">Безопасность</h2>

        <div class="space-y-3">
          <button
            @click="lockWallet"
            class="w-full bg-bg-tertiary hover:bg-bg-hover text-white font-semibold px-6 py-4 rounded-lg transition-all duration-200 flex items-center gap-4 group"
            :disabled="walletStore.state.isLocked"
            :class="walletStore.state.isLocked ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <div class="w-12 h-12 bg-bg-hover rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <div class="text-left flex-1">
              <div class="font-bold">Заблокировать кошелёк</div>
              <div class="text-sm text-text-secondary">Требуется пароль для разблокировки</div>
            </div>
          </button>

          <button
            @click="showBackupMnemonic = true"
            class="w-full bg-bg-tertiary hover:bg-bg-hover text-white font-semibold px-6 py-4 rounded-lg transition-all duration-200 flex items-center gap-4 group"
            :disabled="walletStore.state.isLocked"
            :class="walletStore.state.isLocked ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <div class="w-12 h-12 bg-bg-hover rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div class="text-left flex-1">
              <div class="font-bold">Показать seed-фразу</div>
              <div class="text-sm text-text-secondary">Резервная копия мнемонической фразы</div>
            </div>
          </button>

          <button
            @click="exportWalletData"
            class="w-full bg-bg-tertiary hover:bg-bg-hover text-white font-semibold px-6 py-4 rounded-lg transition-all duration-200 flex items-center gap-4 group"
            :disabled="walletStore.state.isLocked"
            :class="walletStore.state.isLocked ? 'opacity-50 cursor-not-allowed' : ''"
          >
            <div class="w-12 h-12 bg-bg-hover rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
            </div>
            <div class="text-left flex-1">
              <div class="font-bold">Экспорт данных</div>
              <div class="text-sm text-text-secondary">Сохранить информацию о кошельке</div>
            </div>
          </button>
        </div>
      </div>

      <!-- RPC Settings -->
      <div class="card space-y-5">
        <h2 class="text-xl font-bold text-white">Настройки сети</h2>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-text-secondary mb-2">RPC Endpoint</label>
            <input
              v-model="rpcUrl"
              type="text"
              class="input-field"
              placeholder="https://eth.llamarpc.com"
            />
            <p class="text-xs text-text-muted mt-2">Используется для взаимодействия с Ethereum сетью</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-text-secondary mb-2">Etherscan API Key (опционально)</label>
            <input
              v-model="etherscanApiKey"
              type="text"
              class="input-field"
              placeholder="Введите API ключ для истории транзакций"
            />
            <p class="text-xs text-text-muted mt-2">Для получения истории транзакций через Etherscan</p>
          </div>

          <button @click="saveRpcSettings" class="bg-white hover:bg-gray-200 text-black font-semibold px-6 py-3 rounded-lg transition-all duration-200">
            Сохранить настройки
          </button>
        </div>
      </div>

      <!-- USB Settings -->
      <div class="card space-y-5">
        <h2 class="text-xl font-bold text-white">USB накопитель</h2>

        <div class="space-y-4">
          <div class="p-4 bg-bg-tertiary rounded-lg">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-semibold text-white">Статус подключения</p>
                <p class="text-xs text-text-muted mt-1">{{ usbPath || 'Вставьте флешку' }}</p>
              </div>
              <div
                class="w-3 h-3 rounded-full transition-all duration-300"
                :class="walletStore.usbStatus === 'connected' ? 'bg-success shadow-[0_0_8px_rgba(0,210,106,0.6)]' : 'bg-error/50'"
              ></div>
            </div>
          </div>

          <!-- Warning/Info Messages -->
          <div v-if="walletStore.usbStatus === 'connected' && walletStore.usbNeedsFormat" class="p-4 bg-warning/10 border border-warning/30 rounded-lg">
            <div class="flex items-start gap-3">
              <span class="text-2xl">⚠️</span>
              <div>
                <p class="text-sm font-semibold text-warning">Требуется подготовка USB</p>
                <p class="text-xs text-text-muted mt-1">
                  На флешке не обнаружен файл wallet.vault. При создании кошелька он будет записан автоматически.
                </p>
              </div>
            </div>
          </div>

          <div v-else-if="walletStore.usbStatus === 'connected' && walletStore.usbHasVault" class="p-4 bg-success/10 border border-success/30 rounded-lg">
            <div class="flex items-start gap-3">
              <span class="text-2xl">✅</span>
              <div>
                <p class="text-sm font-semibold text-success">USB готова к работе</p>
                <p class="text-xs text-text-muted mt-1">
                  Файл wallet.vault обнаружен. Кошелёк может работать с этой флешкой.
                </p>
              </div>
            </div>
          </div>

          <button @click="checkUsb" class="btn-secondary w-full">
            Проверить USB
          </button>
        </div>
      </div>

      <!-- About -->
      <div class="card space-y-4">
        <h2 class="text-xl font-bold text-white">О приложении</h2>

        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 bg-white rounded-lg flex items-center justify-center">
              <svg class="w-7 h-7 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <div>
              <p class="text-lg font-bold text-white">ZhoraWallet</p>
              <p class="text-sm text-text-secondary">Version 1.0.0</p>
            </div>
          </div>

          <div class="p-4 bg-bg-tertiary rounded-lg space-y-2 text-sm">
            <p class="text-text-secondary">
              Холодный кошелёк Ethereum с air-gapped подписью транзакций через USB накопитель
            </p>
            <div class="flex gap-2 text-xs text-text-muted">
              <span>Tauri 2.0</span>
              <span>•</span>
              <span>Vue 3</span>
              <span>•</span>
              <span>Rust</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Backup Mnemonic Dialog -->
    <div v-if="showBackupMnemonic" class="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div class="bg-bg-card rounded-2xl border border-border p-8 w-[600px] shadow-2xl">
        <div class="flex items-start gap-4 mb-6">
          <div class="w-12 h-12 bg-warning/20 rounded-lg flex items-center justify-center flex-shrink-0">
            <svg class="w-6 h-6 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h2 class="text-2xl font-bold text-white mb-2">Важное предупреждение</h2>
            <p class="text-warning text-sm">
              Никогда не показывайте seed-фразу кому-либо и не храните её в цифровом виде.
              Запишите её на бумаге и храните в безопасном месте.
            </p>
          </div>
        </div>

        <button
          v-if="!mnemonic"
          @click="showMnemonic"
          class="bg-white hover:bg-gray-200 text-black font-semibold px-6 py-3 rounded-lg transition-all duration-200 w-full mb-4"
        >
          Я понимаю риск, показать фразу
        </button>

        <div v-if="mnemonic" class="p-6 bg-bg-tertiary rounded-xl mb-6 border border-border-light">
          <p class="text-xs text-text-muted uppercase tracking-wider mb-3">Ваша seed-фраза (24 слова)</p>
          <div class="grid grid-cols-3 gap-3">
            <div
              v-for="(word, index) in mnemonicWords"
              :key="index"
              class="p-3 bg-bg-hover rounded-lg"
            >
              <span class="text-xs text-text-muted">{{ index + 1 }}.</span>
              <span class="text-sm font-mono text-white ml-2">{{ word }}</span>
            </div>
          </div>
        </div>

        <button @click="closeBackupDialog" class="bg-bg-tertiary hover:bg-bg-hover text-white font-medium px-6 py-3 rounded-lg transition-colors duration-200 w-full">
          Закрыть
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWalletStore } from '@/stores/wallet'
import { invoke } from '@tauri-apps/api/core'

const walletStore = useWalletStore()

const rpcUrl = ref('https://eth.llamarpc.com')
const etherscanApiKey = ref('')
const showBackupMnemonic = ref(false)
const mnemonic = ref('')
const usbPath = ref('')

const mnemonicWords = computed(() => {
  return mnemonic.value ? mnemonic.value.split(' ') : []
})

function lockWallet() {
  walletStore.lockWallet()
}

async function copyAddress() {
  if (!walletStore.state.address) return
  try {
    await navigator.clipboard.writeText(walletStore.state.address)
  } catch (error) {
    console.error('Failed to copy address:', error)
  }
}

async function showMnemonic() {
  try {
    mnemonic.value = await invoke<string>('get_mnemonic')
  } catch (error: any) {
    console.error('Failed to get mnemonic:', error)
  }
}

function closeBackupDialog() {
  showBackupMnemonic.value = false
  mnemonic.value = ''
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
    a.download = `wallet_${walletStore.state.address?.slice(0, 8)}_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to export wallet data:', error)
  }
}

function saveRpcSettings() {
  localStorage.setItem('rpc_url', rpcUrl.value)
  localStorage.setItem('etherscan_api_key', etherscanApiKey.value)
  alert('Настройки сети сохранены')
}

async function checkUsb() {
  await walletStore.checkUsbStatus()
  // Update USB path display
  if (walletStore.usbStatus === 'connected') {
    usbPath.value = walletStore.usbPath || 'USB обнаружен'
  } else {
    usbPath.value = ''
  }
}

onMounted(() => {
  const savedRpc = localStorage.getItem('rpc_url')
  const savedApiKey = localStorage.getItem('etherscan_api_key')
  if (savedRpc) rpcUrl.value = savedRpc
  if (savedApiKey) etherscanApiKey.value = savedApiKey
  checkUsb()
})
</script>
