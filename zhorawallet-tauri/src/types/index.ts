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
