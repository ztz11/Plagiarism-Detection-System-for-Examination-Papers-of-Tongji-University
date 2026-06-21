import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login',
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
      component: () => import('../views/newtask.vue'),
    },
    {
      path: '/history',
      name: 'history',
      component: () => import('../views/history.vue'),
    },
    {
      path: '/question-bank',
      name: 'question-bank',
      component: () => import('../views/questionbank.vue'),
    },
    {
      path: '/devide',
      name: 'devide',
      component: () => import('../views/devide.vue')
    },
    {
      path: '/edit-exam',
      name: 'EditExam',
      component: () => import('@/views/edit_exam.vue')
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/setting.vue'),
    },
    {
      path: '/remote-papers',
      name: 'RemotePapers',
      component: () => import('@/views/remotePapers.vue'),
    },
    {
      path: '/report',
      name: 'Report',
      component: () => import('@/views/report.vue')
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('@/views/profile.vue')
    },
  ],
})

export default router
