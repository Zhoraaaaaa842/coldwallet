export interface Transaction {
  hash: string
  from: string
  to: string
  value: string
  nonce: number
  gasPrice?: string
  maxFeePerGas?: string
  maxPriorityFeePerGas?: string
  gasLimit: number
  timestamp: number
  status: 'pending' | 'confirmed' | 'failed'
  type: 'incoming' | 'outgoing'
  tx_type?: 'incoming' | 'outgoing' // For cached transactions
  confirmations?: number
}

export interface WalletState {
  address: string | null
  balance: {
    eth: string
    rub: string
  }
  nonce: number
  isInitialized: boolean
  isLocked: boolean
  network: string
}

export interface GasSettings {
  type: 'eip1559' | 'legacy'
  gasLimit: number
  // EIP-1559
  maxFeePerGas?: number
  maxPriorityFeePerGas?: number
  // Legacy
  gasPrice?: number
}

export interface UsbTransaction {
  id: string
  path: string
  data: any
  status: 'pending' | 'signed' | 'broadcasted'
}

export interface PriceData {
  ethRub: number
  lastUpdated: number
}

export interface Network {
  id: string
  name: string
  networkType: string
  chainId: number
  rpcUrl: string
  explorerUrl: string
  currencySymbol: string
  currencyDecimals: number
}

export interface Contact {
  id: string
  name: string
  address: string
  note?: string
  createdAt: number
  updatedAt: number
}

export interface BalanceSummary {
  totalReceived: number
  totalSent: number
  transactionCount: number
  lastUpdated: number
}
