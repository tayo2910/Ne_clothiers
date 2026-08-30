<script setup>
defineProps({
  status: { type: String, required: true },
})
</script>

<template>
  <span
    class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
    :class="{
      'bg-yellow-500/20 text-yellow-400': status === 'Pending',
      'bg-blue-500/20 text-blue-400': status === 'In Progress',
      'bg-green-500/20 text-green-400': status === 'Ready',
      'bg-slate-500/20 text-slate-400': status === 'Delivered',
    }"
  >
    <span
      class="w-1.5 h-1.5 rounded-full mr-1.5"
      :class="{
        'bg-yellow-400': status === 'Pending',
        'bg-blue-400': status === 'In Progress',
        'bg-green-400': status === 'Ready',
        'bg-slate-400': status === 'Delivered',
      }"
    ></span>
    {{ status }}
  </span>
</template>
