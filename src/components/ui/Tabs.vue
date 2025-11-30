<script setup>
import { provide, ref } from 'vue'

const props = defineProps({
  defaultValue: String,
  modelValue: String
})

const emit = defineEmits(['update:modelValue'])

const activeTab = ref(props.modelValue || props.defaultValue)

provide('tabs', {
  activeTab,
  setActiveTab: (value) => {
    activeTab.value = value
    emit('update:modelValue', value)
  }
})
</script>

<template>
  <div class="w-full"><slot /></div>
</template>
