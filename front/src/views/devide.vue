<template>
  <div class="h-screen flex flex-col font-sans bg-gray-50">
    <header class="h-16 bg-white border-b px-6 flex items-center justify-between sticky top-0 z-50 shadow-sm">
      <div class="flex items-center space-x-4">
        <button @click="handleBack" class="flex items-center text-gray-500 hover:text-blue-600 font-medium transition-colors">
          <svg class="w-5 h-5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" /></svg>
          返回前序页面
        </button>
        <h1 class="text-lg font-bold text-blue-900">试卷切分</h1>
      </div>
    </header>

    <main class="flex-1 p-6 max-w-7xl mx-auto w-full flex flex-col items-center justify-center">
      <div class="w-full max-w-md bg-white p-6 rounded-lg shadow-md space-y-5">
        <!-- 学科代码 -->
        <div class="relative">
          <label class="block text-sm font-medium text-gray-700 mb-1">学科代码</label>
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
          <p v-if="subjectCodeError" class="text-xs text-red-500 mt-1">{{ subjectCodeError }}</p>
        </div>

        <!-- 试卷年份（带校验）-->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">试卷年份</label>
          <input
            v-model="examYear"
            type="text"
            @input="validateExamYear"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
            placeholder="例如：2025"
          />
          <p v-if="examYearError" class="text-xs text-red-500 mt-1">{{ examYearError }}</p>
        </div>

        <!-- 试卷学院 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">试卷学院</label>
          <div class="relative">
            <input
              v-model="examCollege"
              type="text"
              @input="onCollegeInput"
              @focus="onCollegeFocus"
              @blur="onCollegeBlur"
              class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
              placeholder="例如：信息科学与技术学院"
              autocomplete="off"
            />
            <ul v-if="showCollegeSuggestions && filteredCollegeSuggestions.length > 0" class="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-auto">
              <li v-for="(col, idx) in filteredCollegeSuggestions" :key="col.id" @mousedown.prevent="selectCollege(col)" :class="['px-3 py-2 text-sm cursor-pointer hover:bg-blue-50', highlightCollegeIdx === idx ? 'bg-blue-100' : '']">{{ col.name }}</li>
            </ul>
          </div>
        </div>

        <!-- AI 切分开关 -->
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-gray-700">启用 AI 自动切分</span>
          <div
            @click="toggleAiSplit"
            :class="['relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 cursor-pointer', aiSplitEnabled ? 'bg-blue-600' : 'bg-gray-300']"
          >
            <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200', aiSplitEnabled ? 'translate-x-6' : 'translate-x-1']" />
          </div>
        </div>

        <!-- AI 格式校验开关 -->
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-gray-700">启用 AI 格式校验</span>
          <div
            @click="toggleAiFormatCheck"
            :class="['relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 cursor-pointer', aiFormatCheckEnabled ? 'bg-blue-600' : 'bg-gray-300']"
          >
            <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200', aiFormatCheckEnabled ? 'translate-x-6' : 'translate-x-1']" />
          </div>
        </div>

        <!-- 试卷上传 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">上传试卷（仅支持 .docx 格式）</label>
          <input
            type="file"
            accept=".docx"
            @change="handleFileUpload"
            class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
          />
        </div>

        <!-- 提交按钮（增加年份校验禁用条件） -->
        <button
          @click="submitFile"
          :disabled="!selectedFile || isSubmitting || !selectedSubject || isDuplicateName || !!examYearError"
          class="w-full px-6 py-2 bg-gradient-to-r from-blue-500 to-blue-700 hover:from-blue-600 hover:to-blue-800 text-white font-medium rounded-lg shadow-lg transition-all disabled:opacity-50"
        >
          {{ isSubmitting ? '处理中...' : '提交试卷' }}
        </button>
      </div>

      <!-- 加载弹窗 -->
      <div v-if="loadingDialogVisible" class="fixed inset-0 z-[200] flex items-center justify-center bg-black bg-opacity-50">
        <div class="bg-white rounded-xl p-6 w-80 shadow-2xl border border-gray-200 flex flex-col items-center">
          <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mb-4"></div>
          <p class="text-gray-700 text-center">{{ loadingMessage }}</p>
        </div>
      </div>

      <!-- Vue 原生对话�?-->
      <div v-if="dialogVisible" class="fixed inset-0 z-[100] flex items-center justify-center bg-black bg-opacity-30">
        <div class="bg-white rounded-xl p-6 w-80 shadow-2xl border border-gray-200">
          <h3 class="text-lg font-bold mb-2">{{ dialogTitle }}</h3>
          <p class="text-sm text-gray-700 mb-6 whitespace-pre-wrap">{{ dialogMessage }}</p>
          <div class="flex justify-end gap-3">
            <button v-if="dialogType === 'confirm'" @click="handleDialogCancel" class="px-4 py-2 text-sm rounded-md bg-gray-200 hover:bg-gray-300">取消</button>
            <button @click="handleDialogConfirm" class="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700">
              {{ dialogType === 'alert' ? '确定' : '确认' }}
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()

// 学科相关
const subjectInput = ref('')
const selectedSubject = ref(null)
const filteredSubjects = ref([])
const showSuggestions = ref(false)
const highlightedIndex = ref(-1)
const isLoadingSubjects = ref(false)
const subjectCodeError = ref('')

// 学院补全
const allColleges = ref([])
const filteredCollegeSuggestions = ref([])
const showCollegeSuggestions = ref(false)
const highlightCollegeIdx = ref(-1)
let collegeTimer = null

// 新增字段
const examYear = ref('')
const examCollege = ref('')
const examYearError = ref('')  // 年份校验错误信息

// 文件相关
const selectedFile = ref(null)
const isSubmitting = ref(false)
const previousPage = ref(route.query.from || '/menu')
const projectNameFromQuery = ref(route.query.projectName || '')
const isDuplicateName = ref(false)

// AI 相关
const aiSplitEnabled = ref(false)
const aiFormatCheckEnabled = ref(true)
const splitPrompt = ref('')
const formatChecksEnabled = ref({})

// 加载弹窗控制
const loadingDialogVisible = ref(false)
const loadingMessage = ref('')

// 对话框相关
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
const dialogType = ref('alert')
let dialogResolve = null

let settingsData = null
let apiConfigs = []

const electronAPI = window.electronAPI

// ================== 原生对话框封装==================
const showAlert = (message) => {
  return new Promise((resolve) => {
    dialogTitle.value = '提示'
    dialogMessage.value = message
    dialogType.value = 'alert'
    dialogVisible.value = true
    dialogResolve = resolve
  })
}

const showConfirm = (message) => {
  return new Promise((resolve) => {
    dialogTitle.value = '确认'
    dialogMessage.value = message
    dialogType.value = 'confirm'
    dialogVisible.value = true
    dialogResolve = resolve
  })
}

const showSuccessDialog = (message) => {
  return new Promise((resolve) => {
    dialogTitle.value = '成功'
    dialogMessage.value = message
    dialogType.value = 'alert'
    dialogVisible.value = true
    dialogResolve = resolve
  })
}

const handleDialogConfirm = () => { dialogVisible.value = false; dialogResolve?.(true) }
const handleDialogCancel = () => { dialogVisible.value = false; dialogResolve?.(false) }

// 保存设置
async function saveSetting(key, value) {
  try {
    await electronAPI.invoke('settings:update', { key, value })
  } catch (e) {
    console.error('保存设置失败', e)
  }
}

const toggleAiSplit = async () => {
  aiSplitEnabled.value = !aiSplitEnabled.value
  await saveSetting('ai_split_enabled', aiSplitEnabled.value)
}

const toggleAiFormatCheck = async () => {
  const newValue = !aiFormatCheckEnabled.value
  if (!newValue) {
      const confirmed = await showConfirm(
        '如果不启用 AI 格式校验，分析报告中试卷将不会包含格式校验信息。关闭后如果你需要格式校验信息，请前往试卷页面重新进行格式校验\n\n确定要关闭吗？'
    )
    if (!confirmed) return
  }
  aiFormatCheckEnabled.value = newValue
  await saveSetting('ai_format_check_enabled', aiFormatCheckEnabled.value)
}

// ---------- 试卷年份校验 ----------
const validateExamYear = () => {
  const year = examYear.value.trim()
  if (year === '') {
    examYearError.value = ''
    return true
  }
  // 必须为四位数字
  const yearRegex = /^\d{4}$/
  if (!yearRegex.test(year)) {
      examYearError.value = '年份必须为四位数字（例如：2025）'
    return false
  }
  const yearNum = parseInt(year, 10)
  // 合理范围：1900 - 2100（可根据需要调整）
  if (yearNum < 1900 || yearNum > 2100) {
    examYearError.value = '年份应在 1900 - 2100 之间'
    return false
  }
  examYearError.value = ''
  return true
}

// 监听年份输入实时校验
watch(examYear, () => {
  validateExamYear()
})

// ---------- 学科搜索逻辑 ----------
const onSubjectInput = async () => {
  const query = subjectInput.value.trim()
  if (!query) {
    filteredSubjects.value = []
    showSuggestions.value = false
    subjectCodeError.value = ''
    selectedSubject.value = null
    return
  }
  isLoadingSubjects.value = true
  try {
    if (window.courseAPI) {
      const results = await window.courseAPI.search(query)
      filteredSubjects.value = results
      showSuggestions.value = results.length > 0
      const exactMatch = results.find(s => s.code === query)
      if (exactMatch) {
        selectedSubject.value = exactMatch
        subjectCodeError.value = ''
      } else {
          subjectCodeError.value = results.length ? '' : '学科代码不存在'
        selectedSubject.value = null
      }
      highlightedIndex.value = -1
    }
  } catch (e) {
    console.error('搜索失败:', e)
  } finally {
    isLoadingSubjects.value = false
  }
}

const onSubjectFocus = () => { if (subjectInput.value) onSubjectInput() }
const onSubjectBlur = () => { setTimeout(() => { showSuggestions.value = false }, 200) }
const selectSubject = (subject) => {
  selectedSubject.value = subject
  subjectInput.value = `${subject.code} - ${subject.name}`
  showSuggestions.value = false
  subjectCodeError.value = ''
}

// ---------- 学院输入补全 ----------
const onCollegeInput = () => {
  if (collegeTimer) clearTimeout(collegeTimer)
  const kw = examCollege.value.trim()
  if (!kw) {
    filteredCollegeSuggestions.value = []
    showCollegeSuggestions.value = false
    return
  }
  collegeTimer = setTimeout(() => {
    filteredCollegeSuggestions.value = allColleges.value.filter(c => c.name.includes(kw))
    showCollegeSuggestions.value = filteredCollegeSuggestions.value.length > 0
    highlightCollegeIdx.value = -1
  }, 180)
}

const selectCollege = (col) => {
  examCollege.value = col.name
  showCollegeSuggestions.value = false
  filteredCollegeSuggestions.value = []
}

const onCollegeFocus = () => { if (examCollege.value) onCollegeInput() }
const onCollegeBlur = () => { setTimeout(() => { validateCollegeInput() }, 200) }

const validateCollegeInput = async () => {
  const input = examCollege.value.trim()
  if (!input) {
    filteredCollegeSuggestions.value = []
    showCollegeSuggestions.value = false
    return
  }
  const valid = allColleges.value.some(c => c.name === input)
  if (!valid) {
    examCollege.value = ''
    filteredCollegeSuggestions.value = []
    showCollegeSuggestions.value = false
      await showAlert('学院不存在，已清空输入')
  } else {
    // ensure selected suggestion exists (not storing selectedCollege here)
    showCollegeSuggestions.value = false
  }
}

const presetSubject = async (code) => {
  if (!code) return
  subjectInput.value = code
  try {
    if (window.courseAPI) {
      const results = await window.courseAPI.search(code)
      if (results && results.length > 0) {
        selectSubject(results[0])
      } else {
        selectedSubject.value = null
        subjectCodeError.value = '学科代码不存在'
      }
    }
  } catch (e) {
    console.warn('预填充学科失败', e)
  }
}

onMounted(async () => {
  try {
    if (electronAPI && typeof electronAPI.invoke === 'function') {
      const settings = await electronAPI.invoke('settings:get')
      settingsData = settings
      aiSplitEnabled.value = settings?.ai_split_enabled ?? false
      aiFormatCheckEnabled.value = settings?.ai_format_check_enabled ?? true
      splitPrompt.value = settings?.split_prompt ?? ''
      if (settings?.format_checks) {
        formatChecksEnabled.value = { ...settings.format_checks }
      } else {
        formatChecksEnabled.value = {
          SUBJECT_NAME_CORRECT_FILLED: true,
          SUBJECT_CODE_CORRECT_FILLED: true,
          SUBJECT_NAME_AND_CODE_NOT_MATCH: true,
          HEADER_SUBJECT_CODE_CORRECT_CONSISTENT: true,
          PAGE_NUM_CORRECT_FILLED: false,
          ALL_SECTIONS_MARKED_POINTS: true,
          TOTAL_SCORE_IN_PREDETERMINED_RANGE: true,
          SEQ_CORRECT_FILLED: true,
          OPTIONS_NO_DUPLICATE: true
        }
      }
    }
  } catch (e) {
    console.error('加载设置失败', e)
  }

  const querySubject = route.query.subjectCode
  if (querySubject) {
    await presetSubject(querySubject)
  } else if (projectNameFromQuery.value) {
    try {
      const project = await window.projectAPI.getByName(projectNameFromQuery.value)
      if (project && project.subjectCode) {
        await presetSubject(project.subjectCode)
      }
    } catch (e) {
      console.warn('无法获取项目学科', e)
    }
  }

  // 从路由参数预填年份和学院
  if (route.query.examYear) examYear.value = route.query.examYear
  if (route.query.examCollege) examCollege.value = route.query.examCollege
  // 初始校验
  validateExamYear()
  // 预加载学院列表用于补全
  try {
    if (electronAPI && typeof electronAPI.invoke === 'function') {
      allColleges.value = await electronAPI.invoke('college:listAll')
    }
  } catch (e) {
    console.warn('加载学院列表失败', e)
    allColleges.value = []
  }
})

// ================== 文件选择处理 ==================
const handleFileUpload = async (event) => {
  const file = event.target.files[0]

    if (!file || file.type !== 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
    await showAlert('仅支持 .docx 试卷')
    selectedFile.value = null
    isDuplicateName.value = false
    return
  }

  try {
    if (window.documentAPI && typeof window.documentAPI.listAll === 'function') {
      const allDocs = await window.documentAPI.listAll()
      const existingNames = allDocs.map(d => d.name)
      if (existingNames.includes(file.name)) {
        selectedFile.value = file
        isDuplicateName.value = true
        await showAlert('试卷名与已有试卷重复，请更换试卷后重试')
        return
      }
    }
  } catch (e) {
    console.warn('检查文件名重复失败，已跳过', e)
  }

  isDuplicateName.value = false
  selectedFile.value = file
}

// ================== 后端配置 ==================
async function configureBackendApi(baseUrl, modelName, apiKey) {
  const formData = new FormData()
  formData.append('base_url', baseUrl)
  formData.append('model_name', modelName)
  formData.append('api_key', apiKey)

  const response = await axios.post('http://127.0.0.1:8000/set-config', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000
  })
  if (response.data.status !== 'success') {
    throw new Error(response.data.message || '配置后端失败')
  }
}

async function getActiveApiConfig() {
  if (!electronAPI || typeof electronAPI.invoke !== 'function') {
    throw new Error('电子 API 未就绪')
  }
  if (!settingsData) {
    try { settingsData = await electronAPI.invoke('settings:get') } catch (e) { /* ignore */ }
  }
  const activeApiId = settingsData?.active_api_id
  if (!activeApiId) {
    throw new Error('请先在设置页面选择一个当前使用的 API')
  }
  let list = []
  try {
    list = await electronAPI.invoke('apiconfig:list')
    apiConfigs = list || []
  } catch (e) {
    throw new Error('获取 API 配置失败: ' + (e.message || '未知错误'))
  }
  const activeApi = apiConfigs.find(api => api.id === activeApiId)
  if (!activeApi) {
    throw new Error('当前选择的 API 配置不存在，请重新设置')
  }
  const baseUrl = activeApi.endpoint?.trim() || 'https://dashscope.aliyuncs.com/compatible-mode/v1'
  const modelName = activeApi.model?.trim() || 'qwen-max'
  const apiKey = activeApi.api_key?.trim()
  if (!apiKey) {
    throw new Error('当前 API 配置未填写密钥，请先完善')
  }
  const is_local = !!activeApi.is_local
  return { baseUrl, modelName, apiKey, is_local }
}

// ================== 核心提交 ==================
const submitFile = async () => {
  if (!selectedFile.value) {
    await showAlert('请先选择试卷')
    return
  }
  if (!selectedSubject.value) {
    await showAlert('请先选择有效的学科代码')
    return
  }
  if (examYearError.value) {
    await showAlert(`试卷年份填写有误：${examYearError.value}`)
    return
  }
  if (isSubmitting.value) return

  isSubmitting.value = true
  loadingDialogVisible.value = true

  if (!window.documentAPI || typeof window.documentAPI.save !== 'function') {
    await showAlert('系统错误：数据库 API 未就绪，请联系管理员')
    isSubmitting.value = false
    loadingDialogVisible.value = false
    return
  }

  const shouldDoFormatCheck = aiFormatCheckEnabled.value
  const useAI = aiSplitEnabled.value

  try {
    // 1. 本地文件备份
    loadingMessage.value = '正在将试卷保存到本地...'
    let backupPath = null
    try {
      const backupRes = await electronAPI.invoke('file:backup', selectedFile.value.path)
      if (!backupRes.success) {
        throw new Error(backupRes.error || '备份失败，未知原因')
      }
      backupPath = backupRes.backupPath
    } catch (e) {
      throw new Error('本地备份失败: ' + (e.message || '未知错误'))
    }

    // 2. 配置后端
    if (shouldDoFormatCheck || useAI) {
      loadingMessage.value = '正在配置后端服务...'
      const apiConfig = await getActiveApiConfig()
      await configureBackendApi(apiConfig.baseUrl, apiConfig.modelName, apiConfig.apiKey)
    }

    if (useAI && !splitPrompt.value.trim()) {
      throw new Error('启用 AI 切分需要填写提示词，请先在设置页面配置')
    }

    // 3. 格式校验
    let formatCheckResults = null
    if (shouldDoFormatCheck) {
      loadingMessage.value = '正在执行格式校验...'
      const enabledChecks = {}
      for (const [code, enabled] of Object.entries(formatChecksEnabled.value)) {
        if (enabled) enabledChecks[code] = true
      }
      const formData = new FormData()
      formData.append('file', selectedFile.value)
      formData.append('format_checks', JSON.stringify(enabledChecks))

      // ========== 新增：传递期望总分（项目总分�?==========
      // 仅当总分校验开启且存在项目名称时获取项目总分
      if (enabledChecks.TOTAL_SCORE_IN_PREDETERMINED_RANGE && projectNameFromQuery.value) {
        try {
          const project = await window.projectAPI.getByName(projectNameFromQuery.value)
          if (project && project.totalScore != null && !isNaN(project.totalScore)) {
            formData.append('expected_total_score', project.totalScore.toString())
            console.log(`传递期望总分: ${project.totalScore}`)
          } else {
            console.warn('项目总分未设置或无效，总分校验将无法通过')
          }
        } catch (e) {
          console.error('获取项目总分失败', e)
        }
      }
      // 传递是否为本地 API 标识
      try {
        const active = await getActiveApiConfig()
        // 后端�?validate-format 接口中期望参数名�?is_local_api
        formData.append('is_local_api', active.is_local ? 'true' : 'false')
      } catch (e) {
        // ignore
      }

      const response = await axios.post('http://127.0.0.1:8000/validate-format', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      })
      if (response.data && response.data.results) {
        formatCheckResults = response.data.results
        const passedCount = formatCheckResults.filter(r => r.passed).length
        loadingMessage.value = `格式校验完成：通过 ${passedCount} 项`
      }
    }

    // 4. 切分
    loadingMessage.value = useAI ? '正在执行 AI 切分...' : '正在执行基础切分...'
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    // 根据是否为本�?API 决定 api_type
    try {
      const active = await getActiveApiConfig()
      if (useAI) {
        formData.append('api_type', active.is_local ? 'local' : 'online')
      } else {
        formData.append('api_type', 'none')
      }
    } catch (e) {
      formData.append('api_type', useAI ? 'online' : 'none')
    }
    formData.append('prompt', useAI ? splitPrompt.value : '')

    const response = await axios.post('http://127.0.0.1:8000/analyze-exam', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000
    })
    if (response.data.status !== 'success') {
      throw new Error(response.data.message || '切分失败')
    }

    const rawData = response.data.data
    let blocks = rawData.blocks || []
    if (blocks.length > 0 && typeof blocks[0] === 'string') {
      blocks = blocks.map((text, idx) => ({ id: idx + 1, text }))
    } else if (blocks.length > 0 && typeof blocks[0] === 'object') {
      const maxExistingId = Math.max(0, ...blocks.filter(b => b.id != null).map(b => b.id))
      let nextId = maxExistingId + 1
      blocks = blocks.map(b => {
        if (b.id == null) return { ...b, id: nextId++ }
        return b
      })
    }
    const questions = (rawData.questions || []).map(q => ({
      title: q.title || '',
      indices: q.indices || []
    }))
    const validBlockIds = new Set(blocks.map(b => b.id))
    questions.forEach(q => {
      q.indices = q.indices.filter(id => validBlockIds.has(id))
    })

    // 5. 保存文档（传入备份路径、年份、学院）
    loadingMessage.value = '正在保存文档...'
    const saveResult = await window.documentAPI.save({
      projectName: projectNameFromQuery.value || '',
      fileName: selectedFile.value.name,
      blocks,
      questions,
      subjectCode: selectedSubject.value.code,
      localFilePath: backupPath,
      examYear: examYear.value || null,
      examCollege: examCollege.value || null
    })
    if (!saveResult || !saveResult.success || !saveResult.docId) {
      throw new Error('保存文档失败')
    }
    const docId = saveResult.docId

    // 关联项目
    if (projectNameFromQuery.value) {
      try {
        await window.documentAPI.associate(projectNameFromQuery.value, docId)
      } catch (e) {
        console.warn('关联项目失败（可能已经关联）:', e)
      }
    }

    // 保存格式校验结果
    if (formatCheckResults && formatCheckResults.length > 0) {
      try {
        await electronAPI.invoke('formatcheck:saveBatch', docId, formatCheckResults)
      } catch (e) {
        console.error('保存格式校验结果失败', e)
      }
    }

    loadingDialogVisible.value = false

    let successMsg = '处理成功，即将跳转编辑页。'
    if (formatCheckResults && formatCheckResults.length > 0) {
      const passed = formatCheckResults.filter(r => r.passed).length
      const total = formatCheckResults.length
      const failedItems = formatCheckResults.filter(r => !r.passed).map(r => r.name)
      successMsg = `处理成功，即将跳转编辑页。\n\n格式校验结果：通过 ${passed} 项，未通过 ${total - passed} 项。`
      if (failedItems.length > 0) {
        successMsg += `\n未通过项：${failedItems.join('、')}`
      }
    } else if (!shouldDoFormatCheck) {
      successMsg = '处理成功，即将跳转编辑页。（未进行格式校验）'
    }

    await showSuccessDialog(successMsg)
    router.push({
      path: '/edit-exam',
      query: {
        docId: saveResult.docId,
        source: 'devide',
        returnUrl: previousPage.value,
        projectName: projectNameFromQuery.value
      }
    })
  } catch (error) {
    loadingDialogVisible.value = false

    let msg = error.message || '未知错误'
    if (error.response?.data?.detail) {
      const detail = error.response.data.detail
      if (Array.isArray(detail)) {
        msg = detail.length > 0 ? detail[0].msg : '请求参数错误'
      } else if (typeof detail === 'string') {
        msg = detail
      } else {
        msg = '服务器返回了异常信息'
      }
    } else if (error.message) {
      if (error.message.includes('Network Error')) {
        msg = '无法连接后端服务，请确认服务已启动'
      } else if (error.message.includes('timeout')) {
        msg = '请求超时，请稍后重试（建议检查网络或文件大小）'
      }
    }

    await showAlert(`处理失败：${msg}`)
  } finally {
    isSubmitting.value = false
    loadingDialogVisible.value = false
  }
}

const handleBack = () => {
  router.back()
}
</script>

<style scoped>
input[type="file"] {
  cursor: pointer;
}
button {
  transition: transform 0.2s;
}
button:hover {
  transform: scale(1.05);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
