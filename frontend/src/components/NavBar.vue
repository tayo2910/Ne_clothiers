<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import logo from '@/assets/ne.png'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const mobileOpen = ref(false)

const navLinks = [
  { path: '/scan', label: 'AI Scan' },
  { path: '/measurement', label: 'New Measurement' },
  { path: '/tracking', label: 'Order Tracking' },
  { path: '/admin', label: 'Admin' },
]

function isActive(path) {
  return route.path === path || (path !== '/' && route.path.startsWith(path))
}

function handleLogout() {
  auth.logout()
  router.push('/scan')
}

function closeMobile() {
  mobileOpen.value = false
}
</script>

<template>
  <nav class="fixed top-0 left-0 right-0 z-50 bg-slate-950/80 backdrop-blur-lg border-b border-white/5">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <router-link to="/scan" class="flex items-center space-x-2" @click="closeMobile">
          <img :src="logo" alt="NE Clothiers logo" class="w-8 h-8 rounded-lg object-contain" />
          <span class="text-lg font-bold tracking-wider text-white hidden sm:block">NE CLOTHIERS</span>
        </router-link>

        <div class="hidden md:flex items-center space-x-1">
          <router-link
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200"
            :class="isActive(link.path) ? 'bg-primary/20 text-primary-light' : 'text-slate-400 hover:text-white hover:bg-white/5'"
          >
            {{ link.label }}
          </router-link>
          <button
            v-if="auth.isAuthenticated"
            @click="handleLogout"
            class="ml-4 px-4 py-2 rounded-lg text-sm font-medium text-red-400 hover:bg-red-500/10 transition-all duration-200"
          >
            Logout
          </button>
        </div>

        <button
          class="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5"
          @click="mobileOpen = !mobileOpen"
        >
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path v-if="!mobileOpen" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <div v-if="mobileOpen" class="md:hidden border-t border-white/5">
      <div class="px-4 py-3 space-y-1">
        <router-link
          v-for="link in navLinks"
          :key="link.path"
          :to="link.path"
          @click="closeMobile"
          class="block px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200"
          :class="isActive(link.path) ? 'bg-primary/20 text-primary-light' : 'text-slate-400 hover:text-white hover:bg-white/5'"
        >
          {{ link.label }}
        </router-link>
        <button
          v-if="auth.isAuthenticated"
          @click="handleLogout"
          class="w-full text-left px-4 py-3 rounded-lg text-sm font-medium text-red-400 hover:bg-red-500/10 transition-all duration-200"
        >
          Logout
        </button>
      </div>
    </div>
  </nav>
</template>
