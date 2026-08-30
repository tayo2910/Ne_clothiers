<script setup>
import { ref } from 'vue'
import client from '@/api/client'
import StatusBadge from '@/components/StatusBadge.vue'
import ProgressTracker from '@/components/ProgressTracker.vue'

const searchQuery = ref('')
const results = ref([])
const searched = ref(false)
const loading = ref(false)
const selectedOrder = ref(null)
const submitting = ref(false)
const receiptFile = ref(null)

const detailForm = ref({
  delivery_date: '',
  amount: '',
  notes: '',
})

async function handleSearch() {
  if (!searchQuery.value.trim()) return
  loading.value = true
  searched.value = true
  try {
    const res = await client.get('/orders/search', {
      params: { q: searchQuery.value.trim() },
    })
    results.value = res.data
  } catch {
    results.value = []
  } finally {
    loading.value = false
  }
}

function selectOrder(order) {
  selectedOrder.value = order
  detailForm.value.delivery_date = order.delivery_date || ''
  detailForm.value.amount = order.amount ? String(order.amount) : ''
  detailForm.value.notes = order.notes || ''
}

function onReceiptFile(e) {
  receiptFile.value = e.target.files?.[0] || null
}

async function submitDetails() {
  if (!selectedOrder.value) return
  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('delivery_date', detailForm.value.delivery_date)
    fd.append('amount', detailForm.value.amount)
    fd.append('notes', detailForm.value.notes)
    if (receiptFile.value) fd.append('receipt', receiptFile.value)

    const res = await client.put(`/orders/${selectedOrder.value.id}`, fd)
    Object.assign(selectedOrder.value, res.data)
    const idx = results.value.findIndex((o) => o.id === selectedOrder.value.id)
    if (idx !== -1) results.value[idx] = res.data
  } catch {
    alert('Failed to update order.')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <div class="text-center mb-8">
      <h1 class="text-3xl font-bold text-white">Order Tracking</h1>
      <p class="text-slate-400 mt-2">Search for an order by ID, customer name, or phone number</p>
    </div>

    <div class="max-w-xl mx-auto mb-8">
      <div class="flex space-x-2">
        <input
          v-model="searchQuery"
          @keyup.enter="handleSearch"
          type="text"
          placeholder="Search by Order ID, Name, or Phone..."
          class="flex-1 bg-card border border-white/10 rounded-xl px-5 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors text-sm"
        />
        <button
          @click="handleSearch"
          class="px-6 py-3 rounded-xl bg-primary hover:bg-primary-light text-white font-medium transition-all duration-200 cursor-pointer"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-center py-8">
      <svg class="animate-spin h-8 w-8 mx-auto text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
      </svg>
    </div>

    <div
      v-if="searched && !loading && results.length === 0"
      class="text-center py-12"
    >
      <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-800 flex items-center justify-center">
        <svg class="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <p class="text-slate-400">No orders found matching "{{ searchQuery }}"</p>
    </div>

    <div class="grid md:grid-cols-2 gap-6">
      <div class="space-y-4">
        <div
          v-for="order in results"
          :key="order.id"
          @click="selectOrder(order)"
          class="bg-card border border-white/5 rounded-xl p-5 cursor-pointer transition-all duration-200 hover:border-primary/30"
          :class="selectedOrder?.id === order.id ? 'border-primary/50 ring-1 ring-primary/30' : ''"
        >
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="text-sm font-mono text-primary-light">#{{ order.id || order.order_id }}</p>
              <p class="text-white font-medium">{{ order.name }}</p>
            </div>
            <StatusBadge :status="order.status" />
          </div>
          <div class="text-xs text-slate-400 space-y-1">
            <p>{{ order.phone }}</p>
            <p class="capitalize">{{ order.outfit_type }}</p>
            <p>{{ new Date(order.created_at || order.date).toLocaleDateString() }}</p>
          </div>
          <div class="mt-3">
            <ProgressTracker :currentStatus="order.status" />
          </div>
        </div>
      </div>

      <div
        v-if="selectedOrder"
        class="bg-card border border-white/5 rounded-xl p-6 h-fit sticky top-24"
      >
        <h3 class="text-lg font-semibold text-accent mb-4">Order Details</h3>
        <div class="text-sm text-slate-300 mb-4 space-y-1">
          <p><span class="text-slate-500">Order ID:</span> #{{ selectedOrder.id }}</p>
          <p><span class="text-slate-500">Customer:</span> {{ selectedOrder.name }}</p>
          <p><span class="text-slate-500">Outfit:</span> {{ selectedOrder.outfit_type }}</p>
          <p><span class="text-slate-500">Status:</span> {{ selectedOrder.status }}</p>
          <p><span class="text-slate-500">Amount:</span> {{ selectedOrder.amount || 'Not set' }}</p>
        </div>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">Delivery Date</label>
            <input
              v-model="detailForm.delivery_date"
              type="date"
              class="w-full bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-primary transition-colors"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">Amount</label>
            <input
              v-model="detailForm.amount"
              type="number"
              step="0.01"
              placeholder="0.00"
              class="w-full bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">Notes</label>
            <textarea
              v-model="detailForm.notes"
              rows="3"
              placeholder="Additional notes..."
              class="w-full bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors resize-none"
            ></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">Receipt</label>
            <div
              class="border-2 border-dashed border-white/10 rounded-lg p-4 text-center cursor-pointer hover:border-white/20 transition-colors"
              @click="document.getElementById('receiptInput')?.click()"
            >
              <input id="receiptInput" type="file" accept="image/*,.pdf" class="hidden" @change="onReceiptFile" />
              <p class="text-xs text-slate-400">{{ receiptFile ? receiptFile.name : 'Tap to upload receipt' }}</p>
            </div>
          </div>
          <button
            @click="submitDetails"
            :disabled="submitting"
            class="w-full py-2.5 rounded-lg font-medium text-white transition-all duration-200 cursor-pointer"
            :class="!submitting ? 'bg-primary hover:bg-primary-light' : 'bg-slate-800 text-slate-500 cursor-not-allowed'"
          >
            {{ submitting ? 'Updating...' : 'Update Order' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
