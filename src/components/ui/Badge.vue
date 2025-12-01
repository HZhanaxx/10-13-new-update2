<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  variant: { type: String, default: 'default' },
  class: String
})

const variants = {
  default: 'bg-primary text-primary-foreground hover:bg-primary/80',
  secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
  destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/80',
  outline: 'border border-input bg-background hover:bg-accent',
  success: 'bg-emerald-500/15 text-emerald-600 border border-emerald-500/20'
}

const badgeClass = computed(() => cn(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors',
  variants[props.variant] || variants.default,
  props.class
))
</script>

<template>
  <div :class="badgeClass"><slot /></div>
</template>
