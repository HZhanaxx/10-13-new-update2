<script setup>
import { cn } from '@/lib/utils'
defineProps({ orientation: { type: String, default: 'horizontal' }, class: String })
</script>

<template>
  <div :class="cn(
    'shrink-0 bg-border',
    orientation === 'horizontal' ? 'h-[1px] w-full' : 'h-full w-[1px]',
    $props.class
  )" />
</template>
