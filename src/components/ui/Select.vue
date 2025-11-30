<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: [String, Number],
  placeholder: { type: String, default: '请选择...' },
  disabled: Boolean,
  class: String
})

const emit = defineEmits(['update:modelValue'])

const selectClass = computed(() => cn(
  'flex h-10 w-full items-center justify-between rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
  props.class
))
</script>

<template>
  <select
    :value="modelValue"
    :disabled="disabled"
    :class="selectClass"
    @change="emit('update:modelValue', $event.target.value)"
  >
    <option value="" disabled>{{ placeholder }}</option>
    <slot />
  </select>
</template>
