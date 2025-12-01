<template>
  <div class="min-h-screen flex flex-col items-center justify-center bg-slate-50 p-4 text-center">
    <div class="space-y-6 max-w-md">
      <div class="mx-auto w-24 h-24 bg-red-50 rounded-full flex items-center justify-center">
        <ShieldBan class="w-12 h-12 text-red-500" />
      </div>
      
      <div class="space-y-2">
        <h1 class="text-4xl font-bold tracking-tighter sm:text-5xl text-foreground">403</h1>
        <h2 class="text-2xl font-semibold tracking-tight text-foreground">访问受限</h2>
        <p class="text-muted-foreground">
          抱歉，您没有权限访问此页面。如果您认为这是个错误，请联系管理员。
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
import { ShieldBan } from 'lucide-vue-next'
</script>