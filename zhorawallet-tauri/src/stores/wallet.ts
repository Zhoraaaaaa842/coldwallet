import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WalletState, GasSettings, Transaction, PriceData } from '@/types'
import { invoke } from '@tauri-apps/api/core'

export const useWalletStore = defineStore('wallet', () => {
  const state = ref<WalletState>({
    address: null,
    balance: { eth: '0', rub: '0' },
    nonce: 0,
    isInitialized: false,
    isLocked: true,
    network: 'Ethereum Mainnet',
  })

  const priceData = ref<PriceData>({
    ethRub: 0,
    lastUpdated: 0,
  })

  const transactions = ref<Transaction[]>([])
  const currentGasSettings = ref<GasSettings>({
    type: 'eip1559',
    gasLimit: 21000,
    maxFeePerGas: 20,
    maxPriorityFeePerGas: 2,
  })

  const usbStatus = ref<'connected' | 'disconnected'>('disconnected')
  const broadcastLog = ref<string[]>([])

  // Computed
  const isWalletReady = computed(() => 
    state.value.isInitialized && !state.value.isLocked && state.value.address !== null
  )

  const balanceEth = computed(() => state.value.balance.eth)
  const balanceRub = computed(() => state.value.balance.rub)

  // Actions
  async function checkUsbStatus() {
    try {
      const status = await invoke<string>('check_usb_status')
      usbStatus.value = status === 'connected' ? 'connected' : 'disconnected'
    } catch (error) {
      console.error('Failed to check USB status:', error)
      usbStatus.value = 'disconnected'
    }
  }

  async function initializeWallet(password: string) {
    try {
      const result = await invoke<string>('initialize_wallet', { password })
      state.value.address = result
      state.value.isInitialized = true
      state.value.isLocked = false
      return result
    } catch (error) {
      console.error('Failed to initialize wallet:', error)
      throw error
    }
  }

  async function importFromMnemonic(mnemonic: string, password: string) {
    try {
      const address = await invoke<string>('import_from_mnemonic', { mnemonic, password })
      state.value.address = address
      state.value.isInitialized = true
      state.value.isLocked = false
      return address
    } catch (error) {
      console.error('Failed to import mnemonic:', error)
      throw error
    }
  }

  async function unlockWallet(password: string): Promise<boolean> {
    try {
      const address = await invoke<string>('unlock_wallet', { password })
      state.value.address = address
      state.value.isLocked = false
      return true
    } catch (error) {
      console.error('Failed to unlock wallet:', error)
      throw error
    }
  }

  function lockWallet() {
    state.value.isLocked = true
    state.value.address = null
  }

  async function fetchBalance() {
    if (!state.value.address) return
    
    try {
      const balance = await invoke<string>('get_balance', { address: state.value.address })
      state.value.balance.eth = balance
      updateRubBalance()
    } catch (error) {
      console.error('Failed to fetch balance:', error)
    }
  }

  async function fetchNonce() {
    if (!state.value.address) return
    
    try {
      const nonce = await invoke<number>('get_nonce', { address: state.value.address })
      state.value.nonce = nonce
    } catch (error) {
      console.error('Failed to fetch nonce:', error)
    }
  }

  async function fetchEthPrice() {
    try {
      const price = await invoke<number>('fetch_eth_price_rub')
      priceData.value.ethRub = price
      priceData.value.lastUpdated = Date.now()
      updateRubBalance()
    } catch (error) {
      console.error('Failed to fetch ETH price:', error)
    }
  }

  function updateRubBalance() {
    if (priceData.value.ethRub > 0) {
      const eth = parseFloat(state.value.balance.eth)
      state.value.balance.rub = (eth * priceData.value.ethRub).toFixed(2)
    }
  }

  async function fetchTransactions() {
    if (!state.value.address) return
    
    try {
      const txs = await invoke<Transaction[]>('get_transaction_history', { 
        address: state.value.address 
      })
      transactions.value = txs
    } catch (error) {
      console.error('Failed to fetch transactions:', error)
    }
  }

  function addBroadcastLog(message: string) {
    broadcastLog.value.push(`[${new Date().toLocaleTimeString()}] ${message}`)
  }

  function clearBroadcastLog() {
    broadcastLog.value = []
  }

  // Start polling for updates
  let pollingInterval: number | null = null

  function startPolling() {
    // Check USB every 3 seconds
    setInterval(checkUsbStatus, 3000)
    
    // Fetch price every 3 minutes
    setInterval(fetchEthPrice, 180000)
    
    // Fetch balance and nonce every 30 seconds
    setInterval(() => {
      if (isWalletReady.value) {
        fetchBalance()
        fetchNonce()
      }
    }, 30000)
  }

  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
  }

  return {
    state,
    priceData,
    transactions,
    currentGasSettings,
    usbStatus,
    broadcastLog,
    isWalletReady,
    balanceEth,
    balanceRub,
    checkUsbStatus,
    initializeWallet,
    importFromMnemonic,
    unlockWallet,
    lockWallet,
    fetchBalance,
    fetchNonce,
    fetchEthPrice,
    updateRubBalance,
    fetchTransactions,
    addBroadcastLog,
    clearBroadcastLog,
    startPolling,
    stopPolling,
  }
})
