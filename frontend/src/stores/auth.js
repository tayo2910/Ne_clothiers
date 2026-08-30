import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import client from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('auth_token') || null)
  const isAdmin = ref(localStorage.getItem('is_admin') === 'true')

  const isAuthenticated = computed(() => !!token.value)

  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    const res = await client.post('/auth/login', formData)
    token.value = res.data.access_token
    isAdmin.value = true
    localStorage.setItem('auth_token', res.data.access_token)
    localStorage.setItem('is_admin', 'true')
  }

  function logout() {
    token.value = null
    isAdmin.value = false
    localStorage.removeItem('auth_token')
    localStorage.removeItem('is_admin')
  }

  async function checkAuth() {
    try {
      await client.get('/auth/me')
      isAdmin.value = true
      localStorage.setItem('is_admin', 'true')
    } catch {
      logout()
    }
  }

  return { token, isAdmin, isAuthenticated, login, logout, checkAuth }
})
