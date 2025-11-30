<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: Boolean,
  disabled: Boolean,
  class: String
})

const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <input
    type="checkbox"
    :checked="modelValue"
    :disabled="disabled"
    :class="cn('h-4 w-4 rounded border border-primary text-primary focus:ring-primary', $props.class)"
    @change="emit('update:modelValue', $event.target.checked)"
  />
</template>
