<script setup>
defineProps({
  currentStatus: { type: String, required: true },
})

const steps = ['Pending', 'In Progress', 'Ready', 'Delivered']
</script>

<template>
  <div class="flex items-center w-full">
    <div
      v-for="(step, idx) in steps"
      :key="step"
      class="flex items-center flex-1 last:flex-none"
    >
      <div class="flex flex-col items-center">
        <div
          class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300"
          :class="steps.indexOf(currentStatus) >= idx ? 'bg-primary text-white' : 'bg-white/10 text-slate-500'"
        >
          {{ idx + 1 }}
        </div>
        <span
          class="text-[10px] mt-1 whitespace-nowrap"
          :class="steps.indexOf(currentStatus) >= idx ? 'text-primary-light' : 'text-slate-500'"
        >{{ step }}</span>
      </div>
      <div
        v-if="idx < steps.length - 1"
        class="flex-1 h-0.5 mx-2 rounded"
        :class="steps.indexOf(currentStatus) > idx ? 'bg-primary' : 'bg-white/10'"
      ></div>
    </div>
  </div>
</template>
