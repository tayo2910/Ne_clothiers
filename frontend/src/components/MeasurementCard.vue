<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: null },
  unit: { type: String, default: 'cm' },
  confidence: { type: String, default: null },
})
</script>

<template>
  <div class="flex items-center justify-between py-2 px-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors">
    <span class="text-sm text-slate-300">{{ label }}</span>
    <div class="flex items-center space-x-2">
      <span v-if="value !== null && value !== ''" class="text-sm font-semibold text-white">
        {{ value }}<span class="text-slate-400 ml-0.5">{{ unit }}</span>
      </span>
      <span v-else class="text-sm text-slate-500 italic">—</span>
      <span
        v-if="confidence"
        class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
        :class="{
          'bg-green-500/20 text-green-400': confidence === 'high',
          'bg-yellow-500/20 text-yellow-400': confidence === 'medium',
          'bg-red-500/20 text-red-400': confidence === 'low',
        }"
      >{{ confidence }}</span>
    </div>
  </div>
</template>
