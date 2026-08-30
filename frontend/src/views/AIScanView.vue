<script setup>
import { ref, computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useScanStore } from '@/stores/scan'
import MeasurementCard from '@/components/MeasurementCard.vue'

const router = useRouter()
const scanStore = useScanStore()

const frontImage = ref(null)
const backImage = ref(null)
const frontPreview = ref(null)
const backPreview = ref(null)
const heightValue = ref('')
const heightUnit = ref('cm')
const tapeMeasurements = reactive({
  chest: '',
  shoulder: '',
  waist: '',
  hips: '',
})
const dragOver = ref(false)

function onFrontFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) {
    frontImage.value = file
    const reader = new FileReader()
    reader.onload = (ev) => { frontPreview.value = ev.target.result }
    reader.readAsDataURL(file)
  }
}

function onBackFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) {
    backImage.value = file
    const reader = new FileReader()
    reader.onload = (ev) => { backPreview.value = ev.target.result }
    reader.readAsDataURL(file)
  }
}

function onDrop(e) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) {
    frontImage.value = file
    const reader = new FileReader()
    reader.onload = (ev) => { frontPreview.value = ev.target.result }
    reader.readAsDataURL(file)
  }
}

function removeFront() {
  frontImage.value = null
  frontPreview.value = null
}

function removeBack() {
  backImage.value = null
  backPreview.value = null
}

const canScan = computed(() => !!frontImage.value)

const upperMeasurements = computed(() => {
  const m = scanStore.measurements
  return [
    { label: 'Chest', key: 'chest', value: m.chest },
    { label: 'Stomach', key: 'stomach', value: m.stomach },
    { label: 'Shoulder', key: 'shoulder', value: m.shoulder },
    { label: 'Sleeve Length', key: 'sleeve_length', value: m.sleeve_length },
    { label: 'Neck', key: 'neck', value: m.neck },
    { label: 'Round Sleeve', key: 'round_sleeve', value: m.round_sleeve },
    { label: 'Top Length', key: 'top_length', value: m.top_length },
  ]
})

const lowerMeasurements = computed(() => {
  const m = scanStore.measurements
  return [
    { label: 'Trouser Length', key: 'trouser_length', value: m.trouser_length },
    { label: 'Trouser Waist', key: 'trouser_waist', value: m.trouser_waist },
    { label: 'Hips', key: 'hips', value: m.hips },
    { label: 'Laps', key: 'laps', value: m.laps },
    { label: 'Knee', key: 'knee', value: m.knee },
    { label: 'Ankle', key: 'ankle', value: m.ankle },
  ]
})

const confidenceLevel = computed(() => {
  const c = scanStore.confidence
  if (!c) return null
  if (c >= 80) return { label: 'High', class: 'bg-green-500/20 text-green-400 border-green-500/30' }
  if (c >= 50) return { label: 'Medium', class: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' }
  return { label: 'Low', class: 'bg-red-500/20 text-red-400 border-red-500/30' }
})

const hasResults = computed(() =>
  scanStore.measurements && Object.keys(scanStore.measurements).length > 0
)

async function handleScan() {
  if (!canScan.value) return
  const fd = new FormData()
  fd.append('front_photo', frontImage.value)
  if (backImage.value) fd.append('back_photo', backImage.value)
  if (heightValue.value) {
    fd.append('height', heightValue.value)
    fd.append('height_unit', heightUnit.value)
  }
  if (tapeMeasurements.chest) fd.append('tape_chest', tapeMeasurements.chest)
  if (tapeMeasurements.shoulder) fd.append('tape_shoulder', tapeMeasurements.shoulder)
  if (tapeMeasurements.waist) fd.append('tape_waist', tapeMeasurements.waist)
  if (tapeMeasurements.hips) fd.append('tape_hips', tapeMeasurements.hips)
  await scanStore.scanPhoto(fd)
}

function continueToMeasurement() {
  router.push({ path: '/measurement', query: { fromScan: 'true' } })
}

function clearAll() {
  scanStore.reset()
  frontImage.value = null
  backImage.value = null
  frontPreview.value = null
  backPreview.value = null
  heightValue.value = ''
  heightUnit.value = 'cm'
  tapeMeasurements.chest = ''
  tapeMeasurements.shoulder = ''
  tapeMeasurements.waist = ''
  tapeMeasurements.hips = ''
}
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <div class="text-center mb-8">
      <h1 class="text-3xl font-bold text-white">AI Body Scan</h1>
      <p class="text-slate-400 mt-2">Upload a photo to get AI-powered body measurements</p>
    </div>

    <div v-if="!hasResults" class="bg-card border border-white/5 rounded-xl p-6 mb-8">
      <h3 class="text-lg font-semibold text-accent mb-3">Photo Tips</h3>
      <ul class="space-y-2 text-sm text-slate-400">
        <li class="flex items-start space-x-2">
          <span class="text-primary-light mt-0.5">•</span>
          <span>Stand against a plain, light-colored wall in well-lit conditions</span>
        </li>
        <li class="flex items-start space-x-2">
          <span class="text-primary-light mt-0.5">•</span>
          <span>Wear tight-fitting clothing for accurate measurements</span>
        </li>
        <li class="flex items-start space-x-2">
          <span class="text-primary-light mt-0.5">•</span>
          <span>Keep arms slightly away from the body</span>
        </li>
        <li class="flex items-start space-x-2">
          <span class="text-primary-light mt-0.5">•</span>
          <span>Ensure the full body is visible in the frame</span>
        </li>
        <li class="flex items-start space-x-2">
          <span class="text-primary-light mt-0.5">•</span>
          <span>For best results, provide both front and back photos</span>
        </li>
      </ul>
    </div>

    <div class="grid md:grid-cols-2 gap-6 mb-8">
      <div
        class="relative border-2 border-dashed rounded-xl p-6 text-center transition-all duration-200 cursor-pointer"
        :class="
          dragOver
            ? 'border-primary bg-primary/5'
            : frontPreview
              ? 'border-primary/50 bg-card'
              : 'border-white/10 bg-card hover:border-white/20'
        "
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop.prevent="onDrop"
        @click="!frontPreview && document.getElementById('frontInput')?.click()"
      >
        <input id="frontInput" type="file" accept="image/*" class="hidden" @change="onFrontFileSelect" />
        <div v-if="frontPreview" class="relative">
          <img :src="frontPreview" alt="Front preview" class="max-h-64 mx-auto rounded-lg object-contain" />
          <button
            @click.stop="removeFront"
            class="absolute top-2 right-2 w-8 h-8 rounded-full bg-red-500/80 text-white flex items-center justify-center text-sm hover:bg-red-500 transition-colors"
          >✕</button>
          <p class="text-xs text-slate-400 mt-2">Front Photo ✓</p>
        </div>
        <div v-else>
          <div class="w-16 h-16 mx-auto mb-3 rounded-full bg-primary/10 flex items-center justify-center">
            <svg class="w-8 h-8 text-primary-light" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <p class="text-sm font-medium text-slate-300">Front Photo</p>
          <p class="text-xs text-slate-500 mt-1">Click, drag & drop, or tap to upload</p>
        </div>
      </div>

      <div
        class="border-2 border-dashed rounded-xl p-6 text-center transition-all duration-200 cursor-pointer"
        :class="backPreview ? 'border-primary/50 bg-card' : 'border-white/10 bg-card hover:border-white/20'"
        @click="!backPreview && document.getElementById('backInput')?.click()"
      >
        <input id="backInput" type="file" accept="image/*" class="hidden" @change="onBackFileSelect" />
        <div v-if="backPreview" class="relative">
          <img :src="backPreview" alt="Back preview" class="max-h-64 mx-auto rounded-lg object-contain" />
          <button
            @click.stop="removeBack"
            class="absolute top-2 right-2 w-8 h-8 rounded-full bg-red-500/80 text-white flex items-center justify-center text-sm hover:bg-red-500 transition-colors"
          >✕</button>
          <p class="text-xs text-slate-400 mt-2">Back Photo ✓</p>
        </div>
        <div v-else>
          <div class="w-16 h-16 mx-auto mb-3 rounded-full bg-slate-800 flex items-center justify-center">
            <svg class="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
          <p class="text-sm font-medium text-slate-400">Back Photo (optional)</p>
          <p class="text-xs text-slate-600 mt-1">Click to upload</p>
        </div>
      </div>
    </div>

    <div class="bg-card border border-white/5 rounded-xl p-6 mb-8">
      <h3 class="text-lg font-semibold text-accent mb-4">Additional Inputs</h3>
      <div class="grid md:grid-cols-2 gap-6">
        <div>
          <label class="block text-sm font-medium text-slate-300 mb-2">Height</label>
          <div class="flex space-x-2">
            <input
              v-model="heightValue"
              type="number"
              step="0.1"
              placeholder="e.g. 175"
              class="flex-1 bg-slate-800 border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-primary transition-colors"
            />
            <select
              v-model="heightUnit"
              class="bg-slate-800 border border-white/10 rounded-lg px-3 py-2.5 text-white focus:outline-none focus:border-primary"
            >
              <option value="cm">cm</option>
              <option value="inches">inches</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-300 mb-2">Tape Measurements (optional)</label>
          <div class="grid grid-cols-2 gap-2">
            <input v-model="tapeMeasurements.chest" type="number" step="0.1" placeholder="Chest" class="bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-primary" />
            <input v-model="tapeMeasurements.shoulder" type="number" step="0.1" placeholder="Shoulder" class="bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-primary" />
            <input v-model="tapeMeasurements.waist" type="number" step="0.1" placeholder="Waist" class="bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-primary" />
            <input v-model="tapeMeasurements.hips" type="number" step="0.1" placeholder="Hips" class="bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-primary" />
          </div>
        </div>
      </div>
    </div>

    <div class="text-center mb-8">
      <button
        @click="handleScan"
        :disabled="!canScan || scanStore.loading"
        class="inline-flex items-center px-8 py-3 rounded-xl font-semibold text-white transition-all duration-200 cursor-pointer"
        :class="canScan && !scanStore.loading ? 'bg-primary hover:bg-primary-light' : 'bg-slate-800 text-slate-500 cursor-not-allowed'"
      >
        <svg
          v-if="scanStore.loading"
          class="animate-spin -ml-1 mr-2 h-5 w-5 text-white"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span v-if="scanStore.loading">Scanning...</span>
        <span v-else>Scan &amp; Estimate</span>
      </button>
    </div>

    <div v-if="hasResults" class="space-y-6">
      <div v-if="scanStore.annotatedImage" class="bg-card border border-white/5 rounded-xl p-6">
        <h3 class="text-lg font-semibold text-accent mb-4">Annotated Image</h3>
        <img :src="scanStore.annotatedImage" alt="Annotated scan result" class="max-h-96 mx-auto rounded-lg" />
      </div>

      <div v-if="confidenceLevel" class="flex items-center justify-center">
        <span class="px-4 py-1.5 rounded-full text-sm font-medium border" :class="confidenceLevel.class">
          Confidence: {{ confidenceLevel.label }} ({{ scanStore.confidence }}%)
        </span>
      </div>

      <div class="grid md:grid-cols-2 gap-6">
        <div class="bg-card border border-white/5 rounded-xl p-6">
          <h3 class="text-lg font-semibold text-accent mb-4">Upper Body</h3>
          <div class="space-y-1">
            <MeasurementCard v-for="m in upperMeasurements" :key="m.key" :label="m.label" :value="m.value" unit="cm" />
          </div>
        </div>
        <div class="bg-card border border-white/5 rounded-xl p-6">
          <h3 class="text-lg font-semibold text-accent mb-4">Lower Body</h3>
          <div class="space-y-1">
            <MeasurementCard v-for="m in lowerMeasurements" :key="m.key" :label="m.label" :value="m.value" unit="cm" />
          </div>
        </div>
      </div>

      <div v-if="scanStore.notes" class="bg-card border border-white/5 rounded-xl p-6">
        <h3 class="text-sm font-semibold text-slate-400 mb-2">Notes</h3>
        <p class="text-sm text-slate-300">{{ scanStore.notes }}</p>
      </div>

      <div class="flex flex-col sm:flex-row items-center justify-center gap-4 pb-8">
        <button
          @click="continueToMeasurement"
          class="px-8 py-3 rounded-xl font-semibold bg-primary hover:bg-primary-light text-white transition-all duration-200 cursor-pointer"
        >
          Continue to New Measurement
        </button>
        <button
          @click="clearAll"
          class="px-8 py-3 rounded-xl font-semibold border border-white/10 text-slate-300 hover:bg-white/5 transition-all duration-200 cursor-pointer"
        >
          Clear &amp; Rescan
        </button>
      </div>
    </div>
  </div>
</template>
