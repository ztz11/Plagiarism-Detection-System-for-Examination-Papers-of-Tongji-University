<template>
  <div>
    <router-view v-slot="{ Component }">
      <component :is="Component" />
    </router-view>
  </div>
</template>

<script setup>
/**
 * App.vue - Vue 应用根组件
 *
 * 仅作为 router-view 的容器，所有页面通过 Vue Router 渲染。
 * 启动时自动将根路径 / 重定向到 /login。
 */
import { useRouter } from 'vue-router';

const router = useRouter();

// 应用启动时自动跳转到登录页
if (router.currentRoute.value.path === '/') {
    router.push('/login');
}
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
