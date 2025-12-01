<script setup>
import { cn } from '@/lib/utils'
defineProps({ for: String, class: String, required: Boolean })
</script>

<template>
  <label :for="$props.for" :class="cn('text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70', $props.class)">
    <slot />
    <span v-if="required" class="text-destructive ml-1">*</span>
  </label>
</template>
