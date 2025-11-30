<script setup>
import { inject, computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({ value: String, class: String })
const { activeTab } = inject('tabs')

const isActive = computed(() => activeTab.value === props.value)
</script>

<template>
  <div v-if="isActive" :class="cn('mt-2 ring-offset-background focus-visible:outline-none', $props.class)">
    <slot />
  </div>
</template>
