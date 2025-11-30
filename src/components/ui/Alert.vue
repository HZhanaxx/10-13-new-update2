<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  variant: { type: String, default: 'default' },
  class: String
})

const variants = {
  default: 'bg-background border-border text-foreground',
  destructive: 'bg-destructive/10 border-destructive/30 text-destructive',
  success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
  warning: 'bg-amber-50 border-amber-200 text-amber-800'
}

const alertClass = computed(() => cn(
  'relative w-full rounded-lg border p-4',
  variants[props.variant] || variants.default,
  props.class
))
</script>

<template>
  <div :class="alertClass" role="alert"><slot /></div>
</template>
