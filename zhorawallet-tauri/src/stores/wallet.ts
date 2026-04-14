import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WalletState, GasSettings, Transaction, PriceData, Network, Contact, BalanceSummary } from '@/types'
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
  const usbPath = ref<string | null>(null)
  const usbHasVault = ref<boolean>(false)
  const usbNeedsFormat = ref<boolean>(false)
  const broadcastLog = ref<string[]>([])
  
  // Network state
  const availableNetworks = ref<Network[]>([])
  const currentNetwork = ref<Network | null>(null)
  
  // Address book state
  const contacts = ref<Contact[]>([])

  // Computed
  const isWalletReady = computed(() => 
    state.value.isInitialized && !state.value.isLocked && state.value.address !== null
  )

  const balanceEth = computed(() => state.value.balance.eth)
  const balanceRub = computed(() => state.value.balance.rub)

  // Actions
  async function checkUsbStatus() {
    try {
      interface UsbStatusResponse {
        status: string
        path: string | null
        has_vault: boolean
        needs_format: boolean
      }
      
      const response = await invoke<UsbStatusResponse>('check_usb_status')
      usbStatus.value = response.status === 'connected' ? 'connected' : 'disconnected'
      usbPath.value = response.path
      usbHasVault.value = response.has_vault
      usbNeedsFormat.value = response.needs_format
    } catch (error) {
      console.error('Failed to check USB status:', error)
      usbStatus.value = 'disconnected'
      usbPath.value = null
      usbHasVault.value = false
      usbNeedsFormat.value = false
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

  // Network actions
  async function loadNetworks() {
    try {
      const networks = await invoke<Network[]>('get_all_networks')
      availableNetworks.value = networks
    } catch (error) {
      console.error('Failed to load networks:', error)
    }
  }

  async function loadCurrentNetwork() {
    try {
      const network = await invoke<Network>('get_current_network')
      currentNetwork.value = network
      state.value.network = network.name
    } catch (error) {
      console.error('Failed to load current network:', error)
    }
  }

  async function switchNetwork(networkId: string) {
    try {
      const network = await invoke<Network>('switch_network', { networkId })
      currentNetwork.value = network
      state.value.network = network.name
      // Refresh data after network switch
      await fetchBalance()
      await fetchTransactions()
    } catch (error) {
      console.error('Failed to switch network:', error)
      throw error
    }
  }

  // Address Book actions
  async function loadContacts() {
    try {
      const contactsList = await invoke<Contact[]>('get_all_contacts')
      contacts.value = contactsList
    } catch (error) {
      console.error('Failed to load contacts:', error)
      contacts.value = []
    }
  }

  async function addContact(name: string, address: string, note?: string) {
    try {
      const contact = await invoke<Contact>('add_contact', { name, address, note })
      contacts.value.push(contact)
      return contact
    } catch (error) {
      console.error('Failed to add contact:', error)
      throw error
    }
  }

  async function updateContact(id: string, name: string, address: string, note?: string) {
    try {
      await invoke('update_contact', { id, name, address, note })
      const index = contacts.value.findIndex(c => c.id === id)
      if (index !== -1) {
        contacts.value[index] = {
          ...contacts.value[index],
          name,
          address,
          note,
          updatedAt: Date.now(),
        }
      }
    } catch (error) {
      console.error('Failed to update contact:', error)
      throw error
    }
  }

  async function deleteContact(id: string) {
    try {
      await invoke('delete_contact', { id })
      contacts.value = contacts.value.filter(c => c.id !== id)
    } catch (error) {
      console.error('Failed to delete contact:', error)
      throw error
    }
  }

  async function searchContacts(query: string) {
    try {
      const results = await invoke<Contact[]>('search_contacts', { query })
      return results
    } catch (error) {
      console.error('Failed to search contacts:', error)
      return []
    }
  }

  // Transaction Cache actions
  async function getCachedTransactions(forceRefresh = false): Promise<Transaction[]> {
    if (!state.value.address) return []
    
    try {
      const txs = await invoke<Transaction[]>('get_cached_transactions', {
        address: state.value.address,
        forceRefresh
      })
      transactions.value = txs
      return txs
    } catch (error) {
      console.error('Failed to get cached transactions:', error)
      return []
    }
  }

  async function getBalanceSummary(): Promise<BalanceSummary> {
    if (!state.value.address) {
      return { totalReceived: 0, totalSent: 0, transactionCount: 0, lastUpdated: 0 }
    }
    
    try {
      const summary = await invoke<BalanceSummary>('get_balance_summary', {
        address: state.value.address
      })
      return summary
    } catch (error) {
      console.error('Failed to get balance summary:', error)
      return { totalReceived: 0, totalSent: 0, transactionCount: 0, lastUpdated: 0 }
    }
  }

  // Polling intervals
  let usbPollingInterval: number | null = null
  let pricePollingInterval: number | null = null
  let balancePollingInterval: number | null = null

  function startPolling() {
    // Check USB every 3 seconds
    usbPollingInterval = window.setInterval(checkUsbStatus, 3000)
    
    // Fetch price every 3 minutes
    pricePollingInterval = window.setInterval(fetchEthPrice, 180000)
    
    // Fetch balance and nonce every 30 seconds
    balancePollingInterval = window.setInterval(() => {
      if (isWalletReady.value) {
        fetchBalance()
        fetchNonce()
      }
    }, 30000)
  }

  function stopPolling() {
    if (usbPollingInterval !== null) {
      clearInterval(usbPollingInterval)
      usbPollingInterval = null
    }
    if (pricePollingInterval !== null) {
      clearInterval(pricePollingInterval)
      pricePollingInterval = null
    }
    if (balancePollingInterval !== null) {
      clearInterval(balancePollingInterval)
      balancePollingInterval = null
    }
  }

  return {
    state,
    priceData,
    transactions,
    currentGasSettings,
    usbStatus,
    usbPath,
    usbHasVault,
    usbNeedsFormat,
    broadcastLog,
    availableNetworks,
    currentNetwork,
    contacts,
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
    loadNetworks,
    loadCurrentNetwork,
    switchNetwork,
    loadContacts,
    addContact,
    updateContact,
    deleteContact,
    searchContacts,
    getCachedTransactions,
    getBalanceSummary,
    startPolling,
    stopPolling,
  }
})
