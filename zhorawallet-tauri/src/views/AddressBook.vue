<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-text-primary">Адресная книга</h1>
        <p class="text-sm text-text-muted mt-1">Управление контактами и адресами</p>
      </div>
      <button
        @click="showAddContact = true"
        class="px-4 py-2 bg-white text-black rounded-lg font-medium hover:bg-gray-200 transition-colors flex items-center gap-2"
      >
        <Plus class="w-4 h-4" />
        Добавить контакт
      </button>
    </div>

    <!-- Search -->
    <div class="relative">
      <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
      <input
        v-model="searchQuery"
        @input="handleSearch"
        type="text"
        placeholder="Поиск по имени, адресу или заметке..."
        class="w-full pl-10 pr-4 py-3 bg-bg-secondary border border-border rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-white/20"
      />
    </div>

    <!-- Contacts List -->
    <div class="bg-bg-secondary border border-border rounded-lg overflow-hidden">
      <div v-if="filteredContacts.length === 0" class="p-12 text-center">
        <Users class="w-12 h-12 text-text-muted mx-auto mb-4" />
        <p class="text-text-primary font-medium mb-2">
          {{ searchQuery ? 'Ничего не найдено' : 'Нет контактов' }}
        </p>
        <p class="text-sm text-text-muted">
          {{ searchQuery ? 'Попробуйте изменить запрос' : 'Добавьте первый контакт' }}
        </p>
      </div>

      <div v-else class="divide-y divide-border">
        <div
          v-for="contact in filteredContacts"
          :key="contact.id"
          class="p-4 hover:bg-bg-hover transition-colors group"
        >
          <div class="flex items-start gap-4">
            <!-- Avatar -->
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold flex-shrink-0">
              {{ contact.name.charAt(0).toUpperCase() }}
            </div>

            <!-- Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <h3 class="font-semibold text-text-primary truncate">{{ contact.name }}</h3>
                  <p class="text-sm text-text-muted font-mono mt-1">{{ contact.address }}</p>
                  <p v-if="contact.note" class="text-sm text-text-muted mt-1 truncate">{{ contact.note }}</p>
                </div>

                <!-- Actions -->
                <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    @click="copyAddress(contact.address)"
                    class="p-2 hover:bg-white/10 rounded-lg transition-colors"
                    title="Копировать адрес"
                  >
                    <Copy class="w-4 h-4 text-text-muted" />
                  </button>
                  <button
                    @click="editContact(contact)"
                    class="p-2 hover:bg-white/10 rounded-lg transition-colors"
                    title="Редактировать"
                  >
                    <Edit class="w-4 h-4 text-text-muted" />
                  </button>
                  <button
                    @click="confirmDelete(contact)"
                    class="p-2 hover:bg-red-500/20 rounded-lg transition-colors"
                    title="Удалить"
                  >
                    <Trash2 class="w-4 h-4 text-red-500" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Contact Dialog -->
    <ContactFormDialog
      v-if="showAddContact || editingContact"
      :mode="showAddContact ? 'add' : 'edit'"
      :contact="editingContact"
      @save="handleSaveContact"
      @cancel="closeDialogs"
    />

    <!-- Delete Confirmation Dialog -->
    <ConfirmDialog
      v-if="deletingContact"
      title="Удалить контакт"
      message="Вы уверены, что хотите удалить этот контакт? Это действие нельзя отменить."
      @confirm="handleDeleteContact"
      @cancel="deletingContact = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useWalletStore } from '@/stores/wallet'
import type { Contact } from '@/types'
import { Plus, Search, Users, Copy, Edit, Trash2 } from 'lucide-vue-next'
import ContactFormDialog from '@/components/ContactFormDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useNotifications } from '@/composables/useNotifications'

const walletStore = useWalletStore()
const { success, error } = useNotifications()

const searchQuery = ref('')
const filteredContacts = ref<Contact[]>([])
const showAddContact = ref(false)
const editingContact = ref<Contact | null>(null)
const deletingContact = ref<Contact | null>(null)

// Computed for displaying contacts
const allContacts = computed(() => walletStore.contacts)

// Search handler
async function handleSearch() {
  if (searchQuery.value.trim()) {
    const results = await walletStore.searchContacts(searchQuery.value.trim())
    filteredContacts.value = results
  } else {
    filteredContacts.value = allContacts.value
  }
}

// Copy address to clipboard
function copyAddress(address: string) {
  navigator.clipboard.writeText(address)
  success('Адрес скопирован в буфер обмена')
}

// Edit contact
function editContact(contact: Contact) {
  editingContact.value = contact
  showAddContact.value = false
}

// Delete confirmation
function confirmDelete(contact: Contact) {
  deletingContact.value = contact
}

// Save contact (add or edit)
async function handleSaveContact(contact: Partial<Contact>) {
  try {
    if (editingContact.value?.id) {
      await walletStore.updateContact(
        editingContact.value.id,
        contact.name!,
        contact.address!,
        contact.note
      )
      success('Контакт обновлён')
    } else {
      await walletStore.addContact(
        contact.name!,
        contact.address!,
        contact.note
      )
      success('Контакт добавлен')
    }
    closeDialogs()
    await loadContacts()
  } catch (err: any) {
    error(err.message || 'Ошибка при сохранении контакта')
  }
}

// Delete contact
async function handleDeleteContact() {
  if (!deletingContact.value) return
  
  try {
    await walletStore.deleteContact(deletingContact.value.id)
    success('Контакт удалён')
    deletingContact.value = null
    await loadContacts()
  } catch (err: any) {
    error(err.message || 'Ошибка при удалении контакта')
  }
}

// Close dialogs
function closeDialogs() {
  showAddContact.value = false
  editingContact.value = null
  deletingContact.value = null
}

// Load contacts
async function loadContacts() {
  await walletStore.loadContacts()
  filteredContacts.value = walletStore.contacts
}

onMounted(async () => {
  await loadContacts()
})
</script>
