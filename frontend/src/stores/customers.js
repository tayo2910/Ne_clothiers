import { defineStore } from 'pinia'
import { ref } from 'vue'
import client from '@/api/client'

export const useCustomerStore = defineStore('customers', () => {
  const customers = ref([])
  const currentCustomer = ref(null)
  const loading = ref(false)

  async function fetchCustomers(query = '') {
    loading.value = true
    try {
      const params = query ? { q: query } : {}
      const res = await client.get('/customers', { params })
      customers.value = res.data
    } finally {
      loading.value = false
    }
  }

  async function createCustomer(data) {
    const fd = new FormData()
    fd.append('name', data.name)
    fd.append('phone', data.phone)
    fd.append('email', data.email || '')
    fd.append('outfit_type', data.outfit_type || 'Agbada')
    fd.append('unit', data.unit || 'cm')
    if (data.design_photo) fd.append('design_photo', data.design_photo)

    const upper = data.measurements?.upper || {}
    const lower = data.measurements?.lower || {}
    const flat = { ...upper, ...lower }
    Object.entries(flat).forEach(([key, val]) => {
      if (val !== '' && val !== null && val !== undefined) {
        fd.append(key, String(val))
      }
    })

    const res = await client.post('/customers', fd)
    customers.value.unshift(res.data)
    return res.data
  }

  async function updateCustomer(orderIdOrId, data) {
    const res = await client.put(`/customers/${orderIdOrId}`, data)
    const idx = customers.value.findIndex((c) => (c.id === orderIdOrId) || (c.order_id === orderIdOrId))
    if (idx !== -1) customers.value[idx] = res.data
    return res.data
  }

  async function deleteCustomer(orderIdOrId) {
    await client.delete(`/customers/${orderIdOrId}`)
    customers.value = customers.value.filter((c) => (c.id !== orderIdOrId) && (c.order_id !== orderIdOrId))
  }

  async function lookupByPhone(phone) {
    loading.value = true
    try {
      const res = await client.get(`/customers/lookup/${encodeURIComponent(phone)}`)
      currentCustomer.value = res.data
      return res.data
    } catch {
      currentCustomer.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  return {
    customers,
    currentCustomer,
    loading,
    fetchCustomers,
    createCustomer,
    updateCustomer,
    deleteCustomer,
    lookupByPhone,
  }
})
