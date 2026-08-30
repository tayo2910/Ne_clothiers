<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useCustomerStore } from '@/stores/customers'
import { useScanStore } from '@/stores/scan'

const route = useRoute()
const customerStore = useCustomerStore()

const outfitTypes = [
  { id: 'agbada', label: 'Agbada' },
  { id: 'senator', label: 'Senator' },
  { id: 'suit', label: 'Suit' },
  { id: 'kaftan', label: 'Kaftan' },
]

const selectedOutfit = ref('')
const unit = ref('cm')
const fromScan = ref(false)
const phoneLookup = ref('')
const phoneFound = ref(null)
const submitting = ref(false)
const successData = ref(null)
const upperOpen = ref(true)
const lowerOpen = ref(true)
const designPhoto = ref(null)
const designPreview = ref(null)

const customer = reactive({
  name: '',
  phone: '',
  email: '',
})

const upper = reactive({
  chest: '',
  stomach: '',
  shoulder: '',
  sleeve_length: '',
  neck: '',
  round_sleeve: '',
  top_length: '',
})

const lower = reactive({
  trouser_length: '',
  trouser_waist: '',
  hips: '',
  laps: '',
  knee: '',
  ankle: '',
})

const errors = reactive({})
const phoneRegex = /^\+?[\d\s-]{10,15}$/
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!customer.name.trim()) errors.name = 'Name is required'
  if (!customer.phone.trim()) {
    errors.phone = 'Phone is required'
  } else if (!phoneRegex.test(customer.phone.trim())) {
    errors.phone = 'Invalid phone number'
  }
  if (customer.email && !emailRegex.test(customer.email.trim())) {
    errors.email = 'Invalid email address'
  }
  if (!selectedOutfit.value) errors.outfit = 'Please select an outfit type'
  return Object.keys(errors).length === 0
}

async function lookupPhone() {
  if (!phoneLookup.value.trim()) return
  const result = await customerStore.lookupByPhone(phoneLookup.value.trim())
  if (result) {
    phoneFound.value = result
    customer.name = result.name || ''
    customer.phone = result.phone || ''
    customer.email = result.email || ''
  } else {
    phoneFound.value = null
  }
}

function onDesignPhoto(e) {
  const file = e.target.files?.[0]
  if (file) {
    designPhoto.value = file
    const reader = new FileReader()
    reader.onload = (ev) => { designPreview.value = ev.target.result }
    reader.readAsDataURL(file)
  }
}

function removeDesign() {
  designPhoto.value = null
  designPreview.value = null
}

async function handleSubmit() {
  if (!validate()) return
  submitting.value = true
  try {
    const payload = {
      outfit_type: selectedOutfit.value,
      unit: unit.value,
      name: customer.name.trim(),
      phone: customer.phone.trim(),
      email: customer.email.trim() || undefined,
      measurements: {
        upper: { ...upper },
        lower: { ...lower },
      },
    }
    Object.keys(payload.measurements.upper).forEach((k) => {
      if (!payload.measurements.upper[k]) delete payload.measurements.upper[k]
    })
    Object.keys(payload.measurements.lower).forEach((k) => {
      if (!payload.measurements.lower[k]) delete payload.measurements.lower[k]
    })

    if (designPhoto.value) payload.design_photo = designPhoto.value

    const res = await customerStore.createCustomer(payload)
    successData.value = {
      orderId: res.order_id || res['Order ID'] || '',
      emailSent: res.email_sent || false,
      whatsappSent: res.whatsapp_sent || false,
    }
  } catch (err) {
    alert(err.response?.data?.detail || 'Submission failed. Please try again.')
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  selectedOutfit.value = ''
  customer.name = ''
  customer.phone = ''
  customer.email = ''
  designPhoto.value = null
  designPreview.value = null
  phoneLookup.value = ''
  phoneFound.value = null
  Object.keys(upper).forEach((k) => (upper[k] = ''))
  Object.keys(lower).forEach((k) => (lower[k] = ''))
  Object.keys(errors).forEach((k) => delete errors[k])
  successData.value = null
}

onMounted(() => {
  if (route.query.fromScan === 'true') {
    fromScan.value = true
    const scanStore = useScanStore()
    const m = scanStore.measurements
    if (m && Object.keys(m).length > 0) {
      if (m.chest) upper.chest = String(m.chest)
      if (m.stomach) upper.stomach = String(m.stomach)
      if (m.shoulder) upper.shoulder = String(m.shoulder)
      if (m.sleeve_length) upper.sleeve_length = String(m.sleeve_length)
      if (m.neck) upper.neck = String(m.neck)
      if (m.round_sleeve) upper.round_sleeve = String(m.round_sleeve)
      if (m.top_length) upper.top_length = String(m.top_length)
      if (m.trouser_length) lower.trouser_length = String(m.trouser_length)
      if (m.trouser_waist) lower.trouser_waist = String(m.trouser_waist)
      if (m.hips) lower.hips = String(m.hips)
      if (m.laps) lower.laps = String(m.laps)
      if (m.knee) lower.knee = String(m.knee)
      if (m.ankle) lower.ankle = String(m.ankle)
    }
  }
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-8">
    <div class="text-center mb-8">
      <h1 class="text-3xl font-bold text-white">New Measurement</h1>
      <p class="text-slate-400 mt-2">Enter customer details and body measurements</p>
      <span
        v-if="fromScan"
        class="inline-block mt-2 px-3 py-1 bg-primary/20 text-primary-light text-xs rounded-full"
      >Prefilled from AI Scan</span>
    </div>

    <div v-if="successData" class="bg-card border border-green-500/30 rounded-xl p-8 text-center mb-8">
      <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
        <svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h2 class="text-2xl font-bold text-green-400 mb-2">Order Submitted!</h2>
      <p class="text-slate-300 mb-1">
        Order ID: <span class="font-mono text-white font-bold">{{ successData.orderId }}</span>
      </p>
      <div class="flex items-center justify-center space-x-4 mt-4">
        <span class="flex items-center text-sm" :class="successData.emailSent ? 'text-green-400' : 'text-slate-500'">
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Email {{ successData.emailSent ? 'Sent' : 'Failed' }}
        </span>
        <span class="flex items-center text-sm" :class="successData.whatsappSent ? 'text-green-400' : 'text-slate-500'">
          <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          WhatsApp {{ successData.whatsappSent ? 'Sent' : 'Failed' }}
        </span>
      </div>
      <button
        @click="resetForm"
        class="mt-6 px-6 py-2.5 rounded-lg bg-primary hover:bg-primary-light text-white font-medium transition-all duration-200 cursor-pointer"
      >New Order</button>
    </div>

    <div v-else class="space-y-6">
      <div class="bg-card border border-white/5 rounded-xl p-6">
        <h3 class="text-lg font-semibold text-accent mb-4">Outfit Type</h3>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <button
            v-for="outfit in outfitTypes"
            :key="outfit.id"
            @click="selectedOutfit = outfit.id"
            class="p-4 rounded-xl border-2 text-center transition-all duration-200 cursor-pointer"
            :class="
              selectedOutfit === outfit.id
                ? 'border-primary bg-primary/10 text-primary-light'
                : 'border-white/10 bg-white/5 text-slate-400 hover:border-white/20'
            "
          >
            <span class="text-2xl block mb-1">{{ outfit.label.charAt(0) }}</span>
            <span class="text-sm font-medium">{{ outfit.label }}</span>
          </button>
        </div>
        <p v-if="errors.outfit" class="text-red-400 text-xs mt-2">{{ errors.outfit }}</p>
      </div>

      <div class="bg-card border border-white/5 rounded-xl p-6">
        <h3 class="text-lg font-semibold text-accent mb-4">Returning Customer?</h3>
        <div class="flex space-x-2">
          <input
            v-model="phoneLookup"
            @keyup.enter="lookupPhone"
            type="text"
            placeholder="Enter phone number to lookup"
            class="flex-1 bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors"
          />
          <button
            @click="lookupPhone"
            class="px-4 py-2.5 rounded-lg bg-primary/20 text-primary-light hover:bg-primary/30 font-medium text-sm transition-colors cursor-pointer"
          >Lookup</button>
        </div>
        <p v-if="phoneFound" class="text-green-400 text-xs mt-2">Customer found! Info filled automatically.</p>
      </div>

      <div class="bg-card border border-white/5 rounded-xl p-6">
        <h3 class="text-lg font-semibold text-accent mb-4">Customer Information</h3>
        <div class="grid md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">
              Full Name <span class="text-red-400">*</span>
            </label>
            <input
              v-model="customer.name"
              type="text"
              placeholder="John Doe"
              class="w-full bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors"
              :class="errors.name ? 'border-red-500/50' : ''"
            />
            <p v-if="errors.name" class="text-red-400 text-xs mt-1">{{ errors.name }}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">
              Phone <span class="text-red-400">*</span>
            </label>
            <input
              v-model="customer.phone"
              type="tel"
              placeholder="+234 800 000 0000"
              class="w-full bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors"
              :class="errors.phone ? 'border-red-500/50' : ''"
            />
            <p v-if="errors.phone" class="text-red-400 text-xs mt-1">{{ errors.phone }}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-300 mb-1.5">Email</label>
            <input
              v-model="customer.email"
              type="email"
              placeholder="john@example.com"
              class="w-full bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors"
              :class="errors.email ? 'border-red-500/50' : ''"
            />
            <p v-if="errors.email" class="text-red-400 text-xs mt-1">{{ errors.email }}</p>
          </div>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-card border border-white/5 rounded-xl p-6">
          <h3 class="text-lg font-semibold text-accent mb-4">Measurement Unit</h3>
          <div class="flex space-x-2">
            <button
              @click="unit = 'cm'"
              class="flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer"
              :class="unit === 'cm' ? 'bg-primary text-white' : 'bg-slate-800 text-slate-400 hover:text-white'"
            >Centimeters (cm)</button>
            <button
              @click="unit = 'inches'"
              class="flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 cursor-pointer"
              :class="unit === 'inches' ? 'bg-primary text-white' : 'bg-slate-800 text-slate-400 hover:text-white'"
            >Inches (in)</button>
          </div>
        </div>
        <div class="bg-card border border-white/5 rounded-xl p-6">
          <h3 class="text-lg font-semibold text-accent mb-4">Design/Style Photo</h3>
          <div
            class="border-2 border-dashed rounded-xl p-4 text-center transition-all duration-200 cursor-pointer"
            :class="designPreview ? 'border-primary/50' : 'border-white/10 hover:border-white/20'"
            @click="!designPreview && document.getElementById('designInput')?.click()"
          >
            <input id="designInput" type="file" accept="image/*" class="hidden" @change="onDesignPhoto" />
            <div v-if="designPreview" class="relative">
              <img :src="designPreview" alt="Design preview" class="max-h-32 mx-auto rounded-lg" />
              <button
                @click.stop="removeDesign"
                class="absolute top-1 right-1 w-6 h-6 rounded-full bg-red-500/80 text-white flex items-center justify-center text-xs hover:bg-red-500"
              >✕</button>
            </div>
            <div v-else class="py-4">
              <p class="text-xs text-slate-400">Tap to upload reference photo</p>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-card border border-white/5 rounded-xl p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-accent">Body Measurements</h3>
          <span class="text-xs text-slate-500">in {{ unit }}</span>
        </div>

        <div class="mb-4">
          <button
            @click="upperOpen = !upperOpen"
            class="flex items-center justify-between w-full py-2.5 px-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer"
          >
            <span class="font-medium text-white">Upper Body</span>
            <svg
              class="w-4 h-4 text-slate-400 transition-transform duration-200"
              :class="upperOpen ? 'rotate-180' : ''"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div v-if="upperOpen" class="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
            <div v-for="(val, key) in upper" :key="key">
              <label class="block text-xs text-slate-400 mb-1 capitalize">{{ key.replace(/_/g, ' ') }}</label>
              <input
                v-model="upper[key]"
                type="number"
                step="0.1"
                placeholder="0.0"
                class="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-primary"
              />
            </div>
          </div>
        </div>

        <div>
          <button
            @click="lowerOpen = !lowerOpen"
            class="flex items-center justify-between w-full py-2.5 px-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer"
          >
            <span class="font-medium text-white">Lower Body</span>
            <svg
              class="w-4 h-4 text-slate-400 transition-transform duration-200"
              :class="lowerOpen ? 'rotate-180' : ''"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div v-if="lowerOpen" class="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
            <div v-for="(val, key) in lower" :key="key">
              <label class="block text-xs text-slate-400 mb-1 capitalize">{{ key.replace(/_/g, ' ') }}</label>
              <input
                v-model="lower[key]"
                type="number"
                step="0.1"
                placeholder="0.0"
                class="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-primary"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="text-center pb-8">
        <button
          @click="handleSubmit"
          :disabled="submitting"
          class="inline-flex items-center px-10 py-3.5 rounded-xl font-semibold text-white transition-all duration-200 cursor-pointer"
          :class="!submitting ? 'bg-primary hover:bg-primary-light' : 'bg-slate-800 text-slate-500 cursor-not-allowed'"
        >
          <svg
            v-if="submitting"
            class="animate-spin -ml-1 mr-2 h-5 w-5 text-white"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span v-if="submitting">Submitting...</span>
          <span v-else>Submit Order</span>
        </button>
      </div>
    </div>
  </div>
</template>
