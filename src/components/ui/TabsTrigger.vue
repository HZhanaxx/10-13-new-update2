<script setup>
import { inject, computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({ value: String, class: String })
const { activeTab, setActiveTab } = inject('tabs')

const isActive = computed(() => activeTab.value === props.value)
</script>

<template>
  <button
    :class="cn(
      'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
      isActive ? 'bg-background text-foreground shadow-sm' : 'hover:bg-background/50',
      $props.class
    )"
    @click="setActiveTab(value)"
  >
    <slot />
  </button>
</template>
