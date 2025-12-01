<template>
  <div class="min-h-screen flex flex-col items-center justify-center bg-slate-50 p-4 text-center">
    <div class="space-y-6 max-w-md">
      <div class="mx-auto w-24 h-24 bg-slate-100 rounded-full flex items-center justify-center">
        <Ghost class="w-12 h-12 text-slate-400" />
      </div>
      
      <div class="space-y-2">
        <h1 class="text-4xl font-bold tracking-tighter sm:text-5xl">404</h1>
        <h2 class="text-2xl font-semibold tracking-tight">页面未找到</h2>
        <p class="text-muted-foreground">
          抱歉，您访问的页面不存在或已被移除。
        </p>
      </div>

      <div class="flex gap-4 justify-center pt-4">
        <Button variant="outline" @click="$router.go(-1)">
          返回上一页
        </Button>
        <Button @click="$router.push('/dashboard')">
          回到首页
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Button } from '@/components/ui'
import { Ghost } from 'lucide-vue-next'
</script>