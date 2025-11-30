<script setup>
import { cn } from '@/lib/utils'
defineProps({ src: String, alt: String, fallback: String, class: String })
</script>

<template>
  <div :class="cn('relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full', $props.class)">
    <img v-if="src" :src="src" :alt="alt" class="aspect-square h-full w-full object-cover" />
    <div v-else class="flex h-full w-full items-center justify-center rounded-full bg-muted text-sm font-medium">
      {{ fallback || '?' }}
    </div>
  </div>
</template>
