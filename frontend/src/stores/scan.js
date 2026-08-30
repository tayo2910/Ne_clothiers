import { defineStore } from 'pinia'
import { ref } from 'vue'
import client from '@/api/client'

export const useScanStore = defineStore('scan', () => {
  const measurements = ref({})
  const annotatedImage = ref(null)
  const confidence = ref(null)
  const notes = ref('')
  const loading = ref(false)

  async function scanPhoto(formData) {
    loading.value = true
    try {
      const res = await client.post('/scan', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      measurements.value = res.data.measurements || {}
      annotatedImage.value = res.data.annotated_image || null
      confidence.value = res.data.confidence || null
      notes.value = res.data.notes || ''
    } finally {
      loading.value = false
    }
  }

  function reset() {
    measurements.value = {}
    annotatedImage.value = null
    confidence.value = null
    notes.value = ''
    loading.value = false
  }

  return { measurements, annotatedImage, confidence, notes, loading, scanPhoto, reset }
})
