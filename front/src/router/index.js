/**
 * Vue Router 路由配置
 *
 * 所有页面均使用懒加载（动态 import），按需加载减少首屏体积。
 * 默认路由 / 重定向到 /login 登录页。
 */
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login',     // 默认跳转登录页
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/login.vue'),
    },
    {
      path: '/menu',
      name: 'Menu',
      component: () => import('../views/menu.vue'),
    },
    {
      path: '/new-task',
      name: 'newtask',
      component: () => import('../views/newtask.vue'),    // 新建查重项目
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/history.vue'),    // 历史项目列表
    },
    {
      path: '/question-bank',
      name: 'question-bank',
      component: () => import('../views/questionbank.vue'), // 题库管理
    },
    {
      path: '/devide',
      name: 'devide',
      component: () => import('../views/devide.vue')       // 试卷上传与切分
    },
    {
      path: '/edit-exam',
      name: 'EditExam',
      component: () => import('@/views/edit_exam.vue')     // 试卷划分编辑
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/setting.vue'),      // 系统设置
    },
    {
      path: '/remote-papers',
      name: 'RemotePapers',
      component: () => import('@/views/remotePapers.vue'), // 远程题库抓取
    },
    {
      path: '/report',
      name: 'Report',
      component: () => import('@/views/report.vue')        // 查重报告查看
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('@/views/profile.vue')       // 用户个人信息
    },
  ],
})

export default router
