<script setup>
import { cn } from '@/lib/utils'

defineProps({
  open: Boolean,
  title: String,
  class: String
})

const emit = defineEmits(['close'])
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center">
      <!-- Backdrop -->
      <div class="fixed inset-0 bg-black/50 backdrop-blur-sm" @click="emit('close')" />
      
      <!-- Dialog Content -->
      <div :class="cn('relative z-50 w-full max-w-lg rounded-xl bg-background p-6 shadow-lg animate-fade-up', $props.class)">
        <div v-if="title" class="mb-4">
          <h2 class="text-lg font-semibold">{{ title }}</h2>
        </div>
        <slot />
        <button
          class="absolute right-4 top-4 rounded-sm opacity-70 hover:opacity-100 transition-opacity"
          @click="emit('close')"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  </Teleport>
</template>
