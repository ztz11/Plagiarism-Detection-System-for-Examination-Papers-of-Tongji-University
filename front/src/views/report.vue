<template>
  <div class="min-h-screen w-full bg-gray-50 flex overflow-hidden">
    <div class="flex-1 flex flex-col w-full">
      <main class="flex-1 bg-white flex flex-col h-full min-w-0 overflow-hidden">
        <!-- 标题区域 -->
        <div class="p-6 md:p-8 pb-2 flex-shrink-0">
          <div>
            <h2 class="text-2xl font-bold text-blue-800">相似度报告 - {{ projectName }}</h2>
            <p class="text-gray-600 mt-1">阈值：{{ report?.threshold ?? '0' }}%，{{ summaryText }}</p>

            <!-- 格式校验结果区块 -->
            <div v-if="formatCheckLoading" class="mt-4 text-gray-500">加载格式校验结果...</div>
            <div v-else-if="formatCheckResults.length > 0" class="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <h3 class="text-md font-semibold text-gray-800 mb-2">主试卷格式校验结果</h3>
              <div class="space-y-3">
                <div v-for="item in formatCheckResults" :key="item.code" class="text-sm">
                  <div class="flex justify-between items-center">
                    <span class="text-gray-700">{{ item.name }}</span>
                    <span :class="item.passed ? 'text-green-600' : 'text-red-600'">
                      {{ item.passed ? '已通过' : '未通过' }}
                    </span>
                  </div>
                  <div v-if="item.reason" class="text-xs text-gray-500 mt-1">{{ item.reason }}</div>
                </div>
                <div v-if="formatCheckResults.some(r => !r.passed)" class="text-xs text-red-500 mt-2">
                  请根据未通过项修改试卷格式。
                </div>
              </div>
            </div>
            <div v-else-if="mainDocId" class="mt-4 text-gray-500 text-sm">该主试卷尚未进行格式校验。</div>
          </div>
        </div>

        <!-- 分组展示重复度结果 -->
        <div class="flex-1 overflow-auto px-6 md:px-8 min-h-0">
          <div v-if="loading" class="text-center text-gray-400 my-8">正在加载报告...</div>
          <div v-else-if="groupedResults.length === 0" class="text-center text-gray-400 my-8">未发现高度相似的题目</div>
          <div v-else class="space-y-8">
            <div v-for="group in groupedResults" :key="group.subDocName" class="border rounded-lg overflow-hidden">
              <div class="bg-gray-100 px-4 py-2 border-b">
                <div class="font-medium text-gray-800">对比对象：{{ mainFileName }} vs {{ group.subDocName }}</div>
                <div class="text-sm text-gray-600">重复题目数量：{{ group.items.length }}</div>
              </div>
              <div class="overflow-x-auto">
                <table class="w-full divide-y divide-gray-200">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">主试卷题号</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase min-w-[150px]">主试卷题目</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">副试卷题号</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase min-w-[150px]">副试卷题目</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap min-w-[80px]">相似度</th>
                      <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase min-w-[180px]">原因</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-200 bg-white">
                    <tr v-for="item in group.items" :key="item.id" class="hover:bg-gray-50">
                      <td class="px-4 py-2 text-sm text-gray-700">{{ item.mainOrder }}</td>
                      <td class="px-4 py-2 text-sm text-gray-700">
                        <div class="max-h-16 overflow-y-auto break-words" :title="item.mainTitle">{{ item.mainTitle }}</div>
                      </td>
                      <td class="px-4 py-2 text-sm text-gray-700">{{ item.subOrder }}</td>
                      <td class="px-4 py-2 text-sm text-gray-700">
                        <div class="max-h-16 overflow-y-auto break-words" :title="item.subTitle">{{ item.subTitle }}</div>
                      </td>
                      <td class="px-4 py-2 text-sm font-semibold text-red-600 whitespace-nowrap">{{ item.similarity }}%</td>
                      <td class="px-4 py-2 text-sm text-gray-600">
                        <div class="max-h-16 overflow-y-auto break-words" :title="item.reason">{{ item.reason }}</div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部按钮 -->
        <div class="p-6 md:p-8 pt-2 flex-shrink-0 flex justify-end gap-3">
          <button 
            @click="saveReport" 
            :disabled="exporting"
            :class="[
              'px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700',
              exporting ? 'opacity-50 cursor-not-allowed' : ''
            ]"
          >
            {{ exporting ? '导出中...' : '导出 Word 报告' }}
          </button>
          <button @click="goBack" class="px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 text-gray-800">返回</button>
        </div>
      </main>
    </div>

    <!-- 导出中遮罩层（只覆盖内容区域，不覆盖弹出对话框） -->
    <div v-if="exporting" class="fixed inset-0 z-[200] flex items-center justify-center bg-black bg-opacity-50">
      <div class="bg-white rounded-lg p-6 flex flex-col items-center shadow-xl">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-3"></div>
        <p class="text-gray-800 font-medium">正在导出中，请稍候...</p>
      </div>
    </div>

    <!-- 自定义对话框（提示） -->
    <div v-if="dialogVisible" class="fixed inset-0 z-[300] flex items-center justify-center bg-black bg-opacity-30">
      <div class="bg-white rounded-xl p-6 w-80 shadow-2xl border border-gray-200">
        <h3 class="text-lg font-bold mb-2">{{ dialogTitle }}</h3>
        <p class="text-sm text-gray-700 mb-6 whitespace-pre-wrap">{{ dialogMessage }}</p>
        <div class="flex justify-end gap-3">
          <button @click="handleDialogConfirm" class="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const projectName = ref(route.query.project || '')
const mainDocId = ref(route.query.mainDocId ? parseInt(route.query.mainDocId) : null)

// 导出中状态
const exporting = ref(false)

// 主文档详细信息
const mainDocDetail = ref(null)
const formatCheckResults = ref([])
const formatCheckLoading = ref(false)

const loading = ref(true)
const report = ref(null)
const results = ref([])        // 存储各题目的原始结果
const groupedResults = ref([])
const mainFileName = ref('')

const summaryText = computed(() => {
  if (!report.value) return ''
  return `共发现 ${results.value.length} 对高度相似题目`
})

// 生成 Word 报告（调用后端接口）
const saveReport = async () => {
  // 防止重复点击
  if (exporting.value) return
  
  try {
    exporting.value = true

    // 1. 弹出保存对话框（要求 .docx 扩展名）
    const result = await window.electronAPI.invoke('dialog:showSaveDialog', {
      title: '保存 Word 报告',
      defaultPath: `${projectName.value}_报告.docx`,
      filters: [{ name: 'Word 文档', extensions: ['docx'] }]
    })
    if (result.canceled || !result.filePath) {
      // 用户取消，关闭遮罩层并返回
      exporting.value = false
      return
    }

    // 2. 准备请求数据
    if (!mainDocDetail.value || !mainDocDetail.value.localFilePath) {
      throw new Error('主试卷本地路径不存在，请确认试卷已正确上传')
    }
    const docxFilePath = mainDocDetail.value.localFilePath

    const formatChecks = formatCheckResults.value.map(item => ({
      item: item.name,
      passed: item.passed,
      reason: item.reason || ''
    }))

    const duplicateResults = []
    for (const group of groupedResults.value) {
      for (const item of group.items) {
        if (!item.mainIndices || item.mainIndices.length === 0) {
          console.warn(`题目 ${item.mainOrder} 没有 indices，跳过`)
          continue
        }
        duplicateResults.push({
          block_ids: item.mainIndices,
          similarity: item.similarity,
          duplicate_location: `${group.subDocName} ${item.subOrder}题`,
          reason: item.reason
        })
      }
    }

    let backendUrl = 'http://127.0.0.1:8000'
    try {
      const settings = await window.electronAPI.invoke('settings:get')
      if (settings && settings.backend_url) {
        backendUrl = settings.backend_url
      }
    } catch (e) {
      console.warn('获取后端地址失败，使用默认地址', e)
    }

    // 3. 调用后端接口
    const response = await fetch(`${backendUrl}/generate-report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        docx_file_path: docxFilePath,
        format_checks: formatChecks,
        duplicate_results: duplicateResults,
        save_path: result.filePath
      })
    })

    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`后端返回错误 (${response.status}): ${errorText}`)
    }

    const respData = await response.json()
    if (respData.status === 'success') {
      // 成功：关闭遮罩层，显示提示，打开文件
      exporting.value = false
      await showAlert(`Word 报告已生成并保存至：${respData.save_path}`)
      await window.electronAPI.invoke('file:open', respData.save_path)
    } else {
      throw new Error(respData.message || '生成报告失败')
    }
  } catch (err) {
    console.error('保存 Word 报告失败', err)
    // 出错：关闭遮罩层，显示错误提示
    exporting.value = false
    await showAlert('保存报告失败：' + err.message)
  } finally {
    // 最终确保遮罩层关闭（如果还未关闭）
    exporting.value = false
  }
}

// 对话框相关
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
let dialogResolve = null
const showAlert = (message) => {
  return new Promise((resolve) => {
    dialogTitle.value = '提示'
    dialogMessage.value = message
    dialogVisible.value = true
    dialogResolve = resolve
  })
}
const handleDialogConfirm = () => {
  dialogVisible.value = false
  dialogResolve?.(true)
}

const goBack = () => {
  router.push('/history')
}

onMounted(async () => {
  try {
    if (mainDocId.value) {
      const mainDoc = await window.documentAPI.getDetail(mainDocId.value)
      mainDocDetail.value = mainDoc
      mainFileName.value = mainDoc.name || '主试卷'
    } else {
      mainFileName.value = '主试卷'
    }

    const full = await window.electronAPI.report.getFull(projectName.value)
    if (full) {
      report.value = full.report
      let simResults = full.similarityResults || []
      const thresholdValue = report.value?.threshold ? parseFloat(report.value.threshold) : 0
      simResults = simResults.filter(sim => sim.similarity > thresholdValue)

      const allDocs = await window.documentAPI.listByProject(projectName.value)
      const docQuestionMap = {}
      const docNameMap = {}
      for (const doc of allDocs) {
        const detail = await window.documentAPI.getDetail(doc.id)
        docQuestionMap[doc.id] = detail.questions || []
        docNameMap[doc.id] = doc.name
      }

      const processed = []
      for (const sim of simResults) {
        let mainQ = null, subQ = null
        let subDocId = null
        for (const [docId, questions] of Object.entries(docQuestionMap)) {
          const q1 = questions.find(q => q.id === sim.question1Id)
          const q2 = questions.find(q => q.id === sim.question2Id)
          if (q1) mainQ = q1
          if (q2) { subQ = q2; subDocId = Number(docId) }
          if (mainQ && subQ) break
        }
        if (mainQ && subQ) {
          processed.push({
            id: sim.id,
            mainOrder: mainQ.order + 1,
            mainTitle: mainQ.title || '题目',
            mainIndices: mainQ.indices || [],
            subDocName: docNameMap[subDocId] || '未知',
            subOrder: subQ.order + 1,
            subTitle: subQ.title || '题目',
            similarity: sim.similarity,
            reason: sim.reason
          })
        }
      }
      results.value = processed

      const groupMap = new Map()
      for (const item of processed) {
        const subName = item.subDocName
        if (!groupMap.has(subName)) {
          groupMap.set(subName, [])
        }
        groupMap.get(subName).push(item)
      }
      groupedResults.value = Array.from(groupMap.entries()).map(([subDocName, items]) => ({
        subDocName,
        items
      }))
    }

    if (mainDocId.value) {
      formatCheckLoading.value = true
      try {
        const checkResults = await window.electronAPI.formatCheck.getByDocId(mainDocId.value)
        formatCheckResults.value = checkResults || []
      } catch (e) {
        console.error('获取格式校验结果失败', e)
      } finally {
        formatCheckLoading.value = false
      }
    }
  } catch (e) {
    console.error('加载报告失败', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.transition-all { transition-property: all; }
.max-h-16::-webkit-scrollbar {
  height: 4px;
  width: 4px;
}
.max-h-16::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 2px;
}
.max-h-16::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 2px;
}
.max-h-16::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
.overflow-x-auto {
  overflow-x: auto;
}
.flex-1.overflow-auto {
  min-height: 0;
}
table {
  table-layout: auto;
  width: 100%;
}
td, th {
  white-space: normal;
  word-break: break-word;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
