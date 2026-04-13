<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-title text-text-primary">Получить ETH</h1>
      <p class="text-text-secondary mt-1">Генерация QR-кода и сканирование входящих транзакций</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Generate QR -->
      <div class="card">
        <h2 class="text-lg font-bold text-text-primary mb-4">Сгенерировать QR-код</h2>
        
        <div class="flex flex-col items-center space-y-4">
          <!-- QR Code -->
          <div class="bg-white p-4 rounded-xl">
            <qrcode-vue 
              v-if="walletStore.state.address"
              :value="qrUri" 
              :size="250" 
              level="M"
            />
            <div v-else class="w-[250px] h-[250px] flex items-center justify-center bg-bg-tertiary rounded-xl">
              <p class="text-text-muted">Кошелёк не инициализирован</p>
            </div>
          </div>

          <!-- Address -->
          <div class="w-full">
            <p class="text-sm text-text-secondary mb-2">Ваш адрес:</p>
            <div class="mono-text bg-bg-tertiary rounded-xl p-3 text-sm break-all">
              {{ walletStore.state.address || '0x...' }}
            </div>
          </div>

          <!-- Optional Amount -->
          <div class="w-full">
            <label class="block text-sm text-text-secondary mb-2">Сумма (опционально, ETH)</label>
            <input
              v-model.number="qrAmount"
              type="number"
              class="input-field"
              placeholder="0.0"
              step="0.00000001"
              min="0"
            />
          </div>

          <!-- Buttons -->
          <div class="flex gap-3 w-full">
            <button @click="generateQr" class="btn-primary flex-1">
              Сгенерировать QR
            </button>
            <button @click="saveQrImage" class="btn-secondary">
              Сохранить PNG
            </button>
          </div>
        </div>
      </div>

      <!-- Scan QR -->
      <div class="card">
        <h2 class="text-lg font-bold text-text-primary mb-4">Сканировать QR-код</h2>
        
        <div class="space-y-4">
          <!-- Upload QR Image -->
          <div>
            <label class="block text-sm text-text-secondary mb-2">Загрузить изображение QR</label>
            <div 
              class="border-2 border-dashed border-border rounded-xl p-8 text-center cursor-pointer hover:border-accent transition-colors"
              @click="handleClickUpload"
              @dragover.prevent
              @drop.prevent="handleFileDrop"
            >
              <input
                ref="qrFileInput"
                type="file"
                accept="image/png,image/jpeg,image/jpg"
                class="hidden"
                @change="handleFileUpload"
              />
              <svg class="w-12 h-12 mx-auto text-text-muted mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p class="text-text-secondary">Перетащите изображение сюда или нажмите для выбора</p>
              <p class="text-xs text-text-muted mt-2">PNG, JPG</p>
            </div>
          </div>

          <!-- Manual URI Input -->
          <div>
            <label class="block text-sm text-text-secondary mb-2">Или введите URI вручную</label>
            <textarea
              v-model="manualUri"
              class="input-field h-20 resize-none"
              placeholder="ethereum:0x...?value=..."
            ></textarea>
          </div>

          <!-- Parse Button -->
          <button
            @click="parseUri"
            class="btn-primary w-full"
            :disabled="!hasQrData"
          >
            Разобрать URI
          </button>

          <!-- Result -->
          <div v-if="scanResult" class="p-4 bg-bg-tertiary rounded-xl space-y-3">
            <h3 class="font-semibold text-text-primary">Результат:</h3>
            
            <div>
              <p class="text-sm text-text-secondary">Адрес:</p>
              <p class="mono-text text-sm mt-1">{{ scanResult.address }}</p>
            </div>

            <div v-if="scanResult.amount">
              <p class="text-sm text-text-secondary">Сумма:</p>
              <p class="text-lg font-semibold text-text-primary mt-1">{{ scanResult.amount }} ETH</p>
            </div>

            <!-- Fill Send Form Button -->
            <button
              @click="fillSendForm"
              class="btn-secondary w-full"
            >
              Заполнить форму отправки
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import QrcodeVue from 'qrcode.vue'
import { useWalletStore } from '@/stores/wallet'

const router = useRouter()
const walletStore = useWalletStore()

const qrFileInput = ref<HTMLInputElement | null>(null)
const qrAmount = ref(0)
const manualUri = ref('')
const scanResult = ref<{ address: string; amount?: string } | null>(null)

const qrUri = computed(() => {
  if (!walletStore.state.address) return ''
  let uri = `ethereum:${walletStore.state.address}`
  if (qrAmount.value > 0) {
    const wei = BigInt(Math.floor(qrAmount.value * 1e18))
    uri += `?value=${wei}`
  }
  return uri
})

const hasQrData = computed(() => {
  return manualUri.value.trim() !== ''
})

function generateQr() {
  // QR is auto-generated via computed property
}

async function saveQrImage() {
  // In a real implementation, we would use html2canvas or similar
  // For now, we'll invoke a Tauri command to save the QR
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    await invoke('save_qr_image', {
      uri: qrUri.value,
      path: 'qr_code.png',
    })
  } catch (error) {
    console.error('Failed to save QR image:', error)
  }
}

function handleClickUpload() {
  qrFileInput.value?.click()
}

function handleFileUpload(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    decodeQrFromFile(input.files[0])
  }
}

function handleFileDrop(event: DragEvent) {
  const files = event.dataTransfer?.files
  if (files && files[0]) {
    decodeQrFromFile(files[0])
  }
}

async function decodeQrFromFile(file: File) {
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const arrayBuffer = await file.arrayBuffer()
    const uint8Array = new Uint8Array(arrayBuffer)
    
    const uri = await invoke<string>('decode_qr_from_image', {
      imageData: Array.from(uint8Array),
    })
    
    manualUri.value = uri
    parseUri()
  } catch (error) {
    console.error('Failed to decode QR:', error)
  }
}

function parseUri() {
  const uri = manualUri.value.trim()
  if (!uri) return

  // Parse EIP-681 URI
  const match = uri.match(/^ethereum:([0-9a-fA-F]+)(\?value=(\d+))?$/i)
  if (match) {
    scanResult.value = {
      address: match[1],
      amount: match[3] ? (BigInt(match[3]) / BigInt(1e18)).toString() : undefined,
    }
  } else if (uri.startsWith('0x') && uri.length === 42) {
    scanResult.value = { address: uri }
  } else {
    scanResult.value = { address: 'Неверный формат URI' }
  }
}

function fillSendForm() {
  if (!scanResult.value) return
  
  // Navigate to send page with pre-filled data
  router.push({
    path: '/send',
    query: {
      to: scanResult.value.address,
      amount: scanResult.value.amount || '0',
    },
  })
}
</script>
