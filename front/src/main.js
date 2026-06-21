/**
 * main.js - Vue 3 应用入口
 *
 * 创建 Vue 应用实例，注册路由，挂载到 #app 根元素。
 * 由 Vite 在 index.html 中加载执行。
 */
import './assets/base.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(router)

app.mount('#app')
