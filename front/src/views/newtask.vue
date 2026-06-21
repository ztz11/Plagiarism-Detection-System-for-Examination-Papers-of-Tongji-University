<template>
  <div class="min-h-screen w-full bg-gray-50 flex overflow-hidden">
    <div class="flex-1 flex flex-col transition-all duration-300 ease-in-out">

      <!-- 头部 -->
      <header class="bg-white border-b border-gray-200 shadow-sm z-30 h-16 flex items-center justify-between px-6 sticky top-0">
        <div class="flex items-center gap-3">
          <button
            @click="handleBack"
            class="px-3 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm"
          >
            返回
          </button>
          <div class="text-2xl font-bold text-blue-800 shrink-0">
            试卷智能校验系统
          </div>
        </div>
        <div class="flex items-center space-x-4">
          <span class="text-gray-600 text-sm">欢迎</span>
          <a @click.prevent="goToProfile" class="font-medium text-blue-600 hover:text-blue-800 cursor-pointer transition-colors">
            {{ currentUser.fullName || currentUser.employeeId }}
          </a>
          <button @click="logout" class="px-3 py-1 bg-red-100 text-red-700 rounded-md hover:bg-red-200 text-sm transition-colors">
            退出登录
          </button>
        </div>
      </header>

      <main class="flex-1 bg-white overflow-auto p-6 md:p-8 flex flex-col min-w-0">
        <h1 class="text-2xl font-bold text-blue-800 mb-6">新建项目</h1>

        <div class="max-w-3xl w-full bg-gray-50 rounded-xl shadow-sm p-6 md:p-8 border border-gray-100">
          <form @submit.prevent="handleSubmit" class="space-y-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">项目名称</label>
              <input
                v-model="projectName"
                @blur="validateProjectName"
                type="text"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="请输入项目名称"
                required
              />
              <p v-if="projectNameError" class="text-xs text-red-500 mt-1">{{ projectNameError }}</p>
            </div>

            <div class="relative">
              <label class="block text-sm font-medium text-gray-700 mb-1">学科</label>
              <input
                v-model="subjectInput"
                type="text"
                @input="onSubjectInput"
                @focus="onSubjectFocus"
                @blur="onSubjectBlur"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="输入学科名称或代码进行搜索"
                autocomplete="off"
                required
              />
              <p v-if="subjectInputError" class="text-xs text-red-500 mt-1">{{ subjectInputError }}</p>
              <ul
                v-if="showSuggestions && filteredSubjects.length > 0"
                class="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-auto"
              >
                <li
                  v-for="(subject, index) in filteredSubjects"
                  :key="subject.code"
                  @mousedown.prevent="selectSubject(subject)"
                  @mouseenter="highlightedIndex = index"
                  :class="[
                    'px-4 py-2 cursor-pointer transition-colors',
                    highlightedIndex === index ? 'bg-blue-100 text-blue-800' : 'hover:bg-gray-100'
                  ]"
                >
                  <span class="font-mono text-gray-500 mr-2">{{ subject.code }}</span>
                  <span>{{ subject.name }}</span>
                </li>
              </ul>
              <div v-if="isLoadingSubjects" class="absolute z-50 w-full mt-1 bg-white border p-4 text-gray-500 shadow-lg">
                正在从数据库查询...
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">试卷总分</label>
              <input
                v-model.number="totalScore"
                type="number"
                step="0.5"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                placeholder="请输入试卷总分（数字）"
                required
              />
              <p v-if="totalScoreError" class="text-xs text-red-500 mt-1">{{ totalScoreError }}</p>
            </div>

            <div v-if="selectedSubject" class="bg-blue-50 rounded-lg p-3 text-sm flex items-center">
              <span class="font-medium text-gray-700 mr-2">已选学科：</span>
              <span class="font-mono text-blue-800 mr-2">{{ selectedSubject.code }}</span>
              <span class="text-gray-600">{{ selectedSubject.name }}</span>
            </div>

            <div class="flex flex-col sm:flex-row gap-4 items-center">
              <button
                type="submit"
                :disabled="isSubmitting"
                class="w-full sm:w-auto px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50"
              >
                {{ isSubmitting ? '保存中...' : '生成项目记录' }}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>

    <!-- 自定义 Vue 原生确认对话框 -->
    <div v-if="dialogVisible" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
      <div class="bg-white rounded-xl p-6 w-80 shadow-2xl border border-gray-200">
        <h3 class="text-lg font-bold mb-2">{{ dialogTitle }}</h3>
        <p class="text-sm text-gray-700 mb-6 whitespace-pre-wrap">{{ dialogMessage }}</p>
        <div class="flex justify-end gap-3">
          <button v-if="dialogType === 'confirm'" @click="handleDialogCancel" class="px-4 py-2 text-sm rounded-md bg-gray-200 hover:bg-gray-300">取消</button>
          <button @click="handleDialogConfirm" class="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700">
            {{ dialogType === 'confirm' ? '确认' : '确定' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

interface Subject {
  code: string
  name: string
}

// ---------- 用户信息 ----------
const currentUser = ref({ fullName: '', employeeId: '' })
const router = useRouter()
const route = useRoute()

const goToProfile = () => {
  router.push('/profile')
}

const logout = () => {
  localStorage.removeItem('currentUser')
  router.push('/login')
}

// ---------- Vue 原生对话框状态 ----------
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
const dialogType = ref<'alert' | 'confirm'>('alert')
let dialogResolve: ((value: boolean) => void) | null = null

const showConfirm = (message: string): Promise<boolean> => {
  return new Promise((resolve) => {
    dialogTitle.value = '确认'
    dialogMessage.value = message
    dialogType.value = 'confirm'
    dialogVisible.value = true
    dialogResolve = resolve
  })
}

const showAlert = (message: string): Promise<boolean> => {
  return new Promise((resolve) => {
    dialogTitle.value = '提示'
    dialogMessage.value = message
    dialogType.value = 'alert'
    dialogVisible.value = true
    dialogResolve = resolve
  })
}

const handleDialogConfirm = () => {
  dialogVisible.value = false
  dialogResolve?.(true)
}

const handleDialogCancel = () => {
  dialogVisible.value = false
  dialogResolve?.(false)
}

// ---------- 表单 & API 逻辑 ----------
const projectName = ref('')
const subjectInput = ref('')
const selectedSubject = ref<Subject | null>(null)
const filteredSubjects = ref<Subject[]>([])
const showSuggestions = ref(false)
const highlightedIndex = ref(-1)
const isLoadingSubjects = ref(false)
const isSubmitting = ref(false)
const totalScore = ref<number | null>(null)
const totalScoreError = ref('')
const projectNameError = ref('')
const subjectInputError = ref('')

const isFormDirty = computed(() => {
  return projectName.value.trim() !== '' || subjectInput.value.trim() !== '' || totalScore.value !== null
})

const handleBack = async () => {
  if (!isFormDirty.value) {
    router.push('/history')
    return
  }
  const ok = await showConfirm('返回将丢失未保存的输入，是否继续？')
  if (ok) {
    router.push('/history')
  }
}

const validTotalScore = computed(() => {
  const val = totalScore.value
  if (val === null || val === undefined) return false
  const num = parseFloat(String(val))
  return !isNaN(num) && num >= 0 && num <= 300
})

const extractSubjectCode = (input: string) => {
  const trimmed = input.trim()
  if (!trimmed) return ''
  const match = trimmed.match(/^([A-Za-z0-9_-]+)/)
  return match ? match[1] : trimmed
}

const validateProjectName = async () => {
  projectNameError.value = ''
  const name = projectName.value.trim()
  if (!name) {
    projectNameError.value = '项目名称不能为空'
    return false
  }
  try {
    const list: any[] = await (window as any).projectAPI.list()
    if (list.some((item) => item.name === name)) {
      projectNameError.value = '项目名称已存在，请更换名称'
      return false
    }
    return true
  } catch (e) {
    console.warn('项目名称校验失败', e)
    return true
  }
}

const validateSubjectCode = async () => {
  subjectInputError.value = ''
  const code = extractSubjectCode(subjectInput.value)
  if (!code) {
    subjectInputError.value = '请填写学科代码或名称'
    selectedSubject.value = null
    return false
  }
  if (selectedSubject.value && selectedSubject.value.code === code) {
    return true
  }
  try {
    const results: Subject[] = await (window as any).courseAPI.search(code)
    const match = results.find((item) => item.code === code)
    if (!match) {
      subjectInputError.value = '学科代码错误，请选择有效学科'
      selectedSubject.value = null
      return false
    }
    selectSubject(match)
    subjectInputError.value = ''
    return true
  } catch (e) {
    console.error('学科校验失败', e)
    subjectInputError.value = '学科校验发生错误，请重试'
    selectedSubject.value = null
    return false
  }
}

const validateTotalScore = () => {
  totalScoreError.value = ''
  if (totalScore.value === null || totalScore.value === undefined) {
    totalScoreError.value = '试卷总分不能为空'
    return false
  }
  const num = parseFloat(String(totalScore.value))
  if (isNaN(num)) {
    totalScoreError.value = '试卷总分必须为数字'
    return false
  }
  if (num < 0 || num > 300) {
    totalScoreError.value = '试卷总分必须在 0 到 300 之间'
    return false
  }
  totalScore.value = num
  return true
}

const onSubjectInput = async () => {
  subjectInputError.value = ''
  const query = subjectInput.value.trim()
  if (!query) { 
    filteredSubjects.value = []
    showSuggestions.value = false
    selectedSubject.value = null
    return 
  }
  isLoadingSubjects.value = true
  try {
    if ((window as any).courseAPI) {
      filteredSubjects.value = await (window as any).courseAPI.search(query)
      showSuggestions.value = true
      highlightedIndex.value = filteredSubjects.value.length > 0 ? 0 : -1
    }
  } catch (e) { 
    console.error('搜索失败:', e) 
  } finally { 
    isLoadingSubjects.value = false 
  }
  selectedSubject.value = null
}

const onSubjectFocus = () => { if (subjectInput.value) onSubjectInput() }
const onSubjectBlur = async () => {
  setTimeout(() => { showSuggestions.value = false }, 200)
  await validateSubjectCode()
}
const selectSubject = (subject: Subject) => {
  selectedSubject.value = subject
  subjectInput.value = `${subject.code} - ${subject.name}`
  showSuggestions.value = false
  subjectInputError.value = ''
}

onMounted(async () => {
  // 检查登录状态
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

  // 从路由参数恢复项目名称和学科
  const { projectName: qProject, subjectCode: qSubject } = route.query
  if (qProject) {
    projectName.value = String(qProject)
  }
  if (qSubject) {
    const code = String(qSubject)
    subjectInput.value = code
    try {
      if ((window as any).courseAPI) {
        const results = await (window as any).courseAPI.search(code)
        const match = results && results.length > 0 ? results.find((item: Subject) => item.code === code) : null
        if (match) selectSubject(match)
        else selectedSubject.value = null
      }
    } catch (e) {
      console.warn('恢复学科失败:', e)
    }
  }
})

const handleSubmit = async () => {
  const isProjectNameValid = await validateProjectName()
  const isSubjectValid = await validateSubjectCode()
  const isScoreValid = validateTotalScore()

  if (!isProjectNameValid) {
    await showAlert(projectNameError.value || '项目名称重复，请修改')
    return
  }
  if (!isSubjectValid) {
    await showAlert(subjectInputError.value || '学科输入不正确，请重新选择')
    return
  }
  if (!isScoreValid) {
    await showAlert(totalScoreError.value || '试卷总分必须在 0 到 300 之间')
    return
  }

  isSubmitting.value = true
  const currentProjectName = projectName.value.trim()
  const currentSubjectCode = selectedSubject.value!.code
  const score = parseFloat(String(totalScore.value))

  try {
    const result = await (window as any).projectAPI.save({
      projectName: currentProjectName,
      content: [currentProjectName, new Date().toLocaleString(), currentUser.value.fullName || currentUser.value.employeeId, currentSubjectCode].join('\n'),
      subjectCode: currentSubjectCode,
      userName: currentUser.value.fullName || currentUser.value.employeeId,
      totalScore: score
    })

    if (result.success) {
      const confirmAdd = await showConfirm(`项目「${currentProjectName}」新建成功！\n是否立即上传并划分试卷？`)
      if (confirmAdd) {
        router.push({ path: '/devide', query: { projectName: currentProjectName, subjectCode: currentSubjectCode, from: '/new-task' } })
      } else {
        router.push('/history')
      }
      return
    }

    if (result.error && result.error.includes('已存在')) {
      const goToExist = await showConfirm(`提示：项目「${currentProjectName}」已存在。\n是否直接进入该项目的划分界面？`)
      if (goToExist) {
        router.push({ path: '/devide', query: { projectName: currentProjectName, subjectCode: currentSubjectCode, from: '/new-task' } })
      } else {
        router.push('/history')
      }
      return
    }

    await showAlert(`保存失败：${result.error || '未知错误'}`)
  } catch (e: any) {
    await showAlert(e?.message || '操作失败，请稍后重试')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.transition-all { transition-property: all; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }
</style>