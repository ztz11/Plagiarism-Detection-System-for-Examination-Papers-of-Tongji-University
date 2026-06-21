<template>
  <div class="min-h-screen w-full bg-gray-50 flex overflow-hidden">
    <!-- 侧边栏 -->
    <aside 
      :class="[
        'fixed inset-y-0 left-0 bg-white shadow-lg z-40 transition-all duration-300 ease-in-out flex flex-col',
        isCollapsed ? 'w-16' : 'w-64'
      ]"
    >
      <div class="p-4 border-b border-gray-200 flex items-center h-16 shrink-0" :class="isCollapsed ? 'justify-center' : 'justify-between'">
        <div class="flex items-center overflow-hidden" v-show="!isCollapsed">
          <img src="../assets/images/logo.png" alt=" " class="h-8 w-8 flex-shrink-0">
          <span class="ml-2 font-bold text-blue-800 whitespace-nowrap">命题校验系统</span>
        </div>
        <button 
          @click="toggleSidebar" 
          class="p-2 rounded-md hover:bg-blue-50 focus:outline-none transition-colors duration-200 text-gray-600 hover:text-blue-600"
          :title="isCollapsed ? '展开菜单' : '收起菜单'"
        >
          <svg v-if="isCollapsed" xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      <nav class="mt-4 px-2 overflow-y-auto flex-1">
        <ul class="space-y-1">
          <li v-for="item in menuItems" :key="item.id">
            <a 
              href="#"
              @click.prevent="navigateTo(item.id)"
              :title="isCollapsed ? item.name : ''"
              :class="[
                'flex items-center rounded-md hover:bg-blue-50 text-gray-700 hover:text-blue-800 transition-colors duration-200',
                isCollapsed ? 'justify-center p-2' : 'p-2 px-3',
                { 'bg-blue-100 text-blue-800': isActive(item.id) }
              ]"
            >
              <component :is="item.icon" class="h-5 w-5 flex-shrink-0" :class="isCollapsed ? '' : 'mr-3'" />
              <span v-show="!isCollapsed" class="whitespace-nowrap">{{ item.name }}</span>
            </a>
          </li>
        </ul>
      </nav>
    </aside>

    <!-- 右侧主区域 -->
    <div 
      class="flex-1 flex flex-col transition-all duration-300 ease-in-out"
      :class="isCollapsed ? 'ml-16' : 'ml-64'"
    >
      <!-- 头部：始终固定在顶部 -->
      <header class="bg-white border-b border-gray-200 shadow-sm z-30 h-16 flex items-center justify-between px-6 sticky top-0">
        <div class="text-2xl font-bold text-blue-800 shrink-0">
          试卷智能校验系统
        </div>
        <div class="flex items-center space-x-4">
          <span class="text-gray-600 text-sm">欢迎您</span>
          <a @click.prevent="goToProfile" class="font-medium text-blue-600 hover:text-blue-800 cursor-pointer transition-colors">
            {{ currentUser.fullName || currentUser.employeeId }}
          </a>
          <button @click="logout" class="px-3 py-1 bg-red-100 text-red-700 rounded-md hover:bg-red-200 text-sm transition-colors">
            退出登录
          </button>
        </div>
      </header>

      <!-- 主要内容 -->
      <main class="flex-1 bg-white overflow-auto p-6 md:p-8 flex flex-col min-w-0">
        <h1 class="text-2xl font-bold text-blue-800 mb-6 shrink-0">
          {{ greeting }}，{{ currentUser.fullName || currentUser.employeeId }}！欢迎使用试卷智能校验系统
        </h1>
        
        <!-- 功能卡片网格 -->
        <div class="w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-8">
          <div 
            @click="navigateTo('question-bank')"
            class="bg-green-50 p-6 rounded-xl border border-green-100 flex flex-col min-h-[120px] cursor-pointer hover:bg-green-100 transition-colors duration-200"
          >
            <div class="text-green-800 font-semibold mb-2 text-lg">试卷管理</div>
            <p class="text-sm text-gray-600">集中维护试题资源</p>
          </div>
          <div 
            @click="navigateTo('history')"
            class="bg-purple-50 p-6 rounded-xl border border-purple-100 flex flex-col min-h-[120px] cursor-pointer hover:bg-purple-100 transition-colors duration-200"
          >
            <div class="text-purple-800 font-semibold mb-2 text-lg">历史追溯</div>
            <p class="text-sm text-gray-600">完整记录校验任务</p>
          </div>
          <div 
            @click="navigateTo('settings')"
            class="bg-orange-50 p-6 rounded-xl border border-orange-100 flex flex-col min-h-[120px] cursor-pointer hover:bg-orange-100 transition-colors duration-200"
          >
            <div class="text-orange-800 font-semibold mb-2 text-lg">系统设置</div>
            <p class="text-sm text-gray-600">管理个人偏好与账户</p>
          </div>
        </div>

        <div class="mt-10">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold text-gray-800">最近项目</h2>
            <span class="text-sm text-gray-500">按创建时间排序</span>
          </div>
          <div class="grid gap-4 sm:grid-cols-1 md:grid-cols-3">
            <div v-if="loadingRecent" class="col-span-full rounded-xl border border-gray-200 bg-gray-50 p-6 text-gray-500">加载中...</div>
            <div v-else-if="recentProjects.length === 0" class="col-span-full rounded-xl border border-gray-200 bg-gray-50 p-6 text-gray-500">暂无最近项目</div>
            <button
              v-else
              v-for="project in recentProjects"
              :key="project.name"
              @click="navigateToHistory(project.name)"
              class="text-left rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:bg-blue-50"
            >
              <div class="text-lg font-semibold text-gray-800 mb-2">{{ project.name }}</div>
              <div class="text-sm text-gray-500">创建时间：{{ formatTime(project.createTime) }}</div>
            </button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'

// ---------- 侧边栏控制 ----------
const isCollapsed = ref(true)
const toggleSidebar = () => isCollapsed.value = !isCollapsed.value

// ---------- 用户信息 ----------
const currentUser = ref({ fullName: '', employeeId: '' })
const router = useRouter()

// 最近项目
interface RecentProject {
  name: string
  createTime: string
  [key: string]: any
}
const recentProjects = ref<RecentProject[]>([])
const loadingRecent = ref(true)

const formatTime = (value: string) => {
  if (!value) return '未知时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '未知时间'
  const pad = (num: number) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const loadRecentProjects = async () => {
  loadingRecent.value = true
  try {
    const list = await (window as any).projectAPI.list() as Array<Partial<RecentProject>>
    recentProjects.value = list
      .map(p => ({ ...p, createTime: p.createTime || '' } as RecentProject))
      .sort((a, b) => new Date(b.createTime).getTime() - new Date(a.createTime).getTime())
      .slice(0, 3)
  } catch (err) {
    console.error('加载最近项目失败', err)
    recentProjects.value = []
  } finally {
    loadingRecent.value = false
  }
}

const navigateToHistory = (projectName: string) => {
  router.push({ path: '/history', query: { projectName } }).catch(err => {
    if (err.name !== 'NavigationDuplicated') console.error(err)
  })
}

// 跳转到个人信息页面
const goToProfile = () => {
  router.push('/profile')
}

// 退出登录
const logout = () => {
  localStorage.removeItem('currentUser')
  router.push('/login')
}

// ---------- 动态问候语 ----------
const getGreetingByTime = (): string => {
  const hour = new Date().getHours()
  if (hour >= 6 && hour < 11) return '早上好'
  if (hour >= 11 && hour < 13) return '中午好'
  return '晚上好'
}
const greeting = ref(getGreetingByTime())

// ---------- 菜单配置 ----------
const menuItems = [
  { 
    id: 'home', 
    name: '主页', 
    icon: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', class: 'w-5 h-5' }, [
      h('path', { 
        'stroke-linecap': 'round', 
        'stroke-linejoin': 'round', 
        'stroke-width': '2', 
        d: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' 
      })
    ])
  },
  { 
    id: 'history', 
    name: '历史项目', 
    icon: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', class: 'w-5 h-5' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' })
    ])
  },
  { 
    id: 'question-bank', 
    name: '试卷管理', 
    icon: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', class: 'w-5 h-5' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253' })
    ])
  },
  {
    id: 'settings',
    name: '设置',
    icon: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', class: 'w-5 h-5' }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }),
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' })
    ])
  }
]

const routeMap = {
  home: { name: 'Menu', path: '/menu' },
  history: { name: 'history', path: '/history' },
  'question-bank': { name: 'question-bank', path: '/question-bank' },
  settings: { name: 'Settings', path: '/settings' }
}

const navigateTo = (page: string) => {
  const target = routeMap[page as keyof typeof routeMap]
  if (!target) return
  if (target.name) {
    router.push({ name: target.name }).catch(err => {
      if (err.name !== 'NavigationDuplicated') console.error(err)
    })
  } else if (target.path) {
    router.push(target.path).catch(err => {
      if (err.name !== 'NavigationDuplicated') console.error(err)
    })
  }
}

const isActive = (id: string): boolean => {
  const currentRoute = router.currentRoute.value
  const target = routeMap[id as keyof typeof routeMap]
  if (!target) return false
  if (id === 'home') return currentRoute.path === '/' || currentRoute.name === 'Menu'
  return target.name ? currentRoute.name === target.name : currentRoute.path === target.path
}

// 生命周期：检查登录状态，加载用户信息
onMounted(async () => {
  const storedUser = localStorage.getItem('currentUser')
  if (!storedUser) {
    router.push('/login')
    return
  }
  try {
    const user = JSON.parse(storedUser)
    currentUser.value = user
  } catch (e) {
    router.push('/login')
    return
  }

  await loadRecentProjects()
})
</script>

<style scoped>
.transition-all {
  transition-property: all;
}
</style>