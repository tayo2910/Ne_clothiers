<script setup>
import NavBar from '@/components/NavBar.vue'
</script>

<template>
  <div class="min-h-screen bg-slate-950 text-slate-200">
    <NavBar />
    <main class="pt-16">
      <router-view />
    </main>
  </div>
</template>
