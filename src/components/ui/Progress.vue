<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  value: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  class: String,
  showLabel: Boolean
})

const percentage = computed(() => Math.min(100, Math.max(0, (props.value / props.max) * 100)))
</script>

<template>
  <div class="w-full">
    <div :class="cn('relative h-2.5 w-full overflow-hidden rounded-full bg-secondary', $props.class)">
      <div
        class="h-full bg-gradient-to-r from-primary to-accent transition-all duration-500 ease-out rounded-full"
        :style="{ width: `${percentage}%` }"
      />
    </div>
    <p v-if="showLabel" class="text-xs text-muted-foreground mt-1.5">{{ Math.round(percentage) }}% 完成</p>
  </div>
</template>
