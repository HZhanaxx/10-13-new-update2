<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: String,
  placeholder: String,
  disabled: Boolean,
  rows: { type: Number, default: 4 },
  class: String
})

const emit = defineEmits(['update:modelValue'])

const textareaClass = computed(() => cn(
  'flex min-h-[80px] w-full rounded-lg border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors resize-none',
  props.class
))
</script>

<template>
  <textarea
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :rows="rows"
    :class="textareaClass"
    @input="emit('update:modelValue', $event.target.value)"
  />
</template>
