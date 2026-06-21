<template>
  <div class="p-6 bg-gray-50 min-h-screen">
    <div class="max-w-6xl mx-auto">
      <!-- 标题�?+ 返回按钮 -->
      <div class="flex items-center gap-3 mb-6">
        <button @click="goBack" class="px-3 py-1.5 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors flex items-center gap-1">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          返回
        </button>
        <h1 class="text-2xl font-bold text-gray-800">个人中心</h1>
      </div>

      <!-- 当前用户信息卡片 -->
      <div class="bg-white rounded-lg shadow p-6 mb-8">
        <h2 class="text-xl font-semibold mb-4">我的信息</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div><span class="font-medium">工号：</span>{{ currentUser.employeeId }}</div>
          <div><span class="font-medium">用户名：</span>
            <input v-model="editForm.fullName" type="text" class="border rounded px-2 py-1 w-48" />
          </div>
          <div><span class="font-medium">部门：</span>
            <input v-model="editForm.department" type="text" class="border rounded px-2 py-1 w-48" />
          </div>
          <div><span class="font-medium">账号类型：</span>{{ roleText(currentUser.role) }}</div>
        </div>
        <div class="mt-4 flex gap-3">
          <button @click="updateProfile" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">保存修改</button>
          <button @click="showChangePwd = true" class="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300">修改密码</button>
          <button @click="logout" class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">退出登录</button>
        </div>
      </div>

      <!-- 修改密码对话�?-->
      <div v-if="showChangePwd" class="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg p-6 w-96">
          <h3 class="text-lg font-bold mb-4">修改密码</h3>
          <div class="mb-3">
            <label>原密码</label>
            <input v-model="pwdForm.oldPassword" type="password" class="w-full border rounded px-2 py-1" />
          </div>
          <div class="mb-3">
            <label>新密码</label>
            <input v-model="pwdForm.newPassword" type="password" class="w-full border rounded px-2 py-1" />
          </div>
          <div class="mb-4">
            <label>确认新密码</label>
            <input v-model="pwdForm.confirmPassword" type="password" class="w-full border rounded px-2 py-1" />
          </div>
          <div class="flex justify-end gap-3">
            <button @click="showChangePwd = false" class="px-4 py-2 bg-gray-200 rounded">取消</button>
            <button @click="changePassword" class="px-4 py-2 bg-blue-600 text-white rounded">确定</button>
          </div>
        </div>
      </div>

      <!-- 管理员及以上功能：用户管�?-->
      <div v-if="currentUser.role <= 2" class="bg-white rounded-lg shadow p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-semibold">账户管理</h2>
          <div class="flex gap-2">
            <button @click="exportUsers" class="px-3 py-1 bg-blue-600 text-white rounded text-sm">📎 导出用户</button>
            <button @click="showCreateUser = true" class="px-3 py-1 bg-green-600 text-white rounded text-sm">+ 新增用户</button>
          </div>
        </div>

        <!-- 用户表格 -->
        <div class="overflow-x-auto">
          <table class="w-full border-collapse">
            <thead>
              <tr class="bg-gray-100">
                <th class="border p-2 text-left">工号</th>
                <th class="border p-2 text-left">用户</th>
                <th class="border p-2 text-left">部门</th>
                <th class="border p-2 text-left">账号类型</th>
                <th class="border p-2 text-left">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in filteredUserList" :key="user.id">
                <td class="border p-2">{{ user.employeeId }}</td>
                <td class="border p-2">{{ user.fullName }}</td>
                <td class="border p-2">{{ user.department }}</td>
                <td class="border p-2">
                  <select v-if="currentUser.role === 1 && user.id !== currentUser.id" v-model="user.role" @change="updateRole(user)" class="border rounded px-1 py-0.5 text-sm">
                    <option :value="2">管理员</option>
                    <option :value="3">普通用户</option>
                  </select>
                  <span v-else>{{ roleText(user.role) }}</span>
                </td>
                <td class="border p-2 space-x-2">
                  <button v-if="canResetPassword(user)" @click="openResetPwdDialog(user.id)" class="text-blue-600 text-sm">修改密码</button>
                  <button v-if="canDeleteUser(user)" @click="deleteUser(user.id)" class="text-red-600 text-sm">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 新建用户对话�?-->
      <div v-if="showCreateUser" class="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg p-6 w-96">
          <h3 class="text-lg font-bold mb-4">新建用户</h3>
          <div class="mb-3">
            <label>工号 *</label>
            <input v-model="newUserForm.employeeId" type="text" class="w-full border rounded px-2 py-1" />
          </div>
          <div class="mb-3">
            <label>用户：</label>
            <input v-model="newUserForm.fullName" type="text" class="w-full border rounded px-2 py-1" />
          </div>
          <div class="mb-3">
            <label>部门</label>
            <input v-model="newUserForm.department" type="text" class="w-full border rounded px-2 py-1" />
          </div>
          <div class="mb-4">
            <label>初始密码 *</label>
            <input v-model="newUserForm.password" type="password" class="w-full border rounded px-2 py-1" />
          </div>
          <div class="flex justify-end gap-3">
            <button @click="showCreateUser = false" class="px-4 py-2 bg-gray-200 rounded">取消</button>
            <button @click="createUser" class="px-4 py-2 bg-blue-600 text-white rounded">创建</button>
          </div>
        </div>
      </div>

      <!-- 重置密码对话�?-->
      <div v-if="showResetPwdDialog" class="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
        <div class="bg-white rounded-lg p-6 w-96">
          <h3 class="text-lg font-bold mb-4">重置用户密码</h3>
          <div class="mb-4">
            <label>新密码 *</label>
            <input v-model="resetPwdForm.newPassword" type="password" class="w-full border rounded px-2 py-1" />
          </div>
          <div class="mb-4">
            <label>确认新密码</label>
            <input v-model="resetPwdForm.confirmPassword" type="password" class="w-full border rounded px-2 py-1" />
          </div>
          <div class="flex justify-end gap-3">
            <button @click="closeResetPwdDialog" class="px-4 py-2 bg-gray-200 rounded">取消</button>
            <button @click="confirmResetPassword" class="px-4 py-2 bg-blue-600 text-white rounded">确定</button>
          </div>
        </div>
      </div>

      <!-- 自定义提�?确认对话�?-->
      <div v-if="dialogVisible" class="fixed inset-0 z-[100] flex items-center justify-center bg-black bg-opacity-30">
        <div class="bg-white rounded-xl p-6 w-80 shadow-2xl border border-gray-200">
          <h3 class="text-lg font-bold mb-2">{{ dialogTitle }}</h3>
          <p class="text-sm text-gray-700 mb-6 whitespace-pre-wrap">{{ dialogMessage }}</p>
          <div class="flex justify-end gap-3">
            <button v-if="dialogType === 'confirm'" @click="handleDialogCancel" class="px-4 py-2 text-sm rounded-md bg-gray-200 hover:bg-gray-300">取消</button>
            <button @click="handleDialogConfirm" class="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700">{{ dialogType === 'alert' ? '确定' : '确认' }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const currentUser = ref(JSON.parse(localStorage.getItem('currentUser')) || {})
const userList = ref([])
const showChangePwd = ref(false)
const showCreateUser = ref(false)
const showResetPwdDialog = ref(false)
const resetPwdUserId = ref(null)
const resetPwdForm = reactive({ newPassword: '', confirmPassword: '' })

const editForm = reactive({
  fullName: currentUser.value.fullName || '',
  department: currentUser.value.department || ''
})
const pwdForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })
const newUserForm = reactive({ employeeId: '', fullName: '', department: '', password: '' })

// 自定义对话框逻辑
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
const dialogType = ref('alert')
let dialogResolve = null

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

const handleDialogConfirm = () => {
  dialogVisible.value = false
  dialogResolve?.(true)
}

const handleDialogCancel = () => {
  dialogVisible.value = false
  dialogResolve?.(false)
}

const roleText = (role) => {
  if (role === 1) return '超级管理员'
  if (role === 2) return '管理员'
  return '普通用户'
}

// 过滤用户列表
const filteredUserList = computed(() => {
  if (currentUser.value.role === 1) {
    return userList.value.filter(u => u.id !== currentUser.value.id && u.role !== 1)
  } else if (currentUser.value.role === 2) {
    return userList.value.filter(u => u.role === 3)
  }
  return []
})

// 权限判断
const canResetPassword = (user) => {
  if (currentUser.value.id === user.id) return false
  if (currentUser.value.role === 1) return true
  if (currentUser.value.role === 2 && user.role === 3) return true
  return false
}

const canDeleteUser = (user) => {
  if (currentUser.value.id === user.id) return false
  if (currentUser.value.role === 1) return true
  if (currentUser.value.role === 2 && user.role === 3) return true
  return false
}

const loadUsers = async () => {
  if (currentUser.value.role > 2) return
  try {
    const all = await window.electronAPI.user.list()
    userList.value = all
  } catch (err) {
    console.error(err)
  }
}

const updateProfile = async () => {
  try {
    await window.electronAPI.user.update(currentUser.value.id, {
      fullName: editForm.fullName,
      department: editForm.department
    })
    currentUser.value.fullName = editForm.fullName
    currentUser.value.department = editForm.department
    localStorage.setItem('currentUser', JSON.stringify(currentUser.value))
    await showAlert('信息更新成功')
  } catch (err) {
    await showAlert('更新失败: ' + err.message)
  }
}

const changePassword = async () => {
  if (pwdForm.newPassword !== pwdForm.confirmPassword) {
    await showAlert('两次输入的新密码不一致')
    return
  }
  const auth = await window.electronAPI.user.authenticate(currentUser.value.employeeId, pwdForm.oldPassword)
  if (!auth) {
    await showAlert('原密码错误')
    return
  }
  try {
    await window.electronAPI.user.update(currentUser.value.id, { password: pwdForm.newPassword })
    await showAlert('密码修改成功，请重新登录')
    localStorage.removeItem('currentUser')
    router.push('/login')
  } catch (err) {
    await showAlert('修改失败: ' + err.message)
  }
}

const createUser = async () => {
  if (!newUserForm.employeeId || !newUserForm.password) {
    await showAlert('工号和初始密码不能为空')
    return
  }
  try {
    await window.electronAPI.user.create({
      employeeId: newUserForm.employeeId,
      password: newUserForm.password,
      fullName: newUserForm.fullName,
      department: newUserForm.department,
      role: 3
    })
    await showAlert('用户创建成功')
    showCreateUser.value = false
    loadUsers()
    Object.assign(newUserForm, { employeeId: '', fullName: '', department: '', password: '' })
  } catch (err) {
    await showAlert('创建失败: ' + err.message)
  }
}

const openResetPwdDialog = (userId) => {
  resetPwdUserId.value = userId
  resetPwdForm.newPassword = ''
  resetPwdForm.confirmPassword = ''
  showResetPwdDialog.value = true
}

const closeResetPwdDialog = () => {
  showResetPwdDialog.value = false
  resetPwdUserId.value = null
}

const confirmResetPassword = async () => {
  if (!resetPwdForm.newPassword) {
    await showAlert('新密码不能为空')
    return
  }
  if (resetPwdForm.newPassword !== resetPwdForm.confirmPassword) {
    await showAlert('两次输入的密码不一致')
    return
  }
  try {
    await window.electronAPI.user.update(resetPwdUserId.value, { password: resetPwdForm.newPassword })
    await showAlert('密码已重置')
    closeResetPwdDialog()
  } catch (err) {
    await showAlert('重置失败: ' + err.message)
  }
}

const updateRole = async (user) => {
  if (user.role === 1) {
    await showAlert('不能将用户设为超级管理员')
    user.role = 2
    return
  }
  try {
    await window.electronAPI.user.update(user.id, { role: user.role })
    await showAlert('账号类型已更改')
    loadUsers()
  } catch (err) {
    await showAlert('修改失败: ' + err.message)
    loadUsers()
  }
}

const deleteUser = async (userId) => {
  const ok = await showConfirm('确定删除该用户吗？')
  if (!ok) return
  try {
    await window.electronAPI.user.delete(userId)
    await showAlert('删除成功')
    loadUsers()
  } catch (err) {
    await showAlert('删除失败: ' + err.message)
  }
}

// 导出用户�?CSV
const exportUsers = async () => {
  const usersToExport = filteredUserList.value
  if (!usersToExport.length) {
    await showAlert('没有可导出的用户数据')
    return
  }

  const headers = ['工号', '姓名', '部门', '账号类型']
  const rows = usersToExport.map(user => [
    user.employeeId,
    user.fullName || '',
    user.department || '',
    roleText(user.role)
  ])

  const escapeCSV = (cell) => {
    if (cell === undefined || cell === null) return ''
    const str = String(cell)
    if (str.includes(',') || str.includes('"') || str.includes('\n')) {
      return '"' + str.replace(/"/g, '""') + '"'
    }
    return str
  }

  const csvLines = []
  csvLines.push(headers.map(escapeCSV).join(','))
  rows.forEach(row => {
    csvLines.push(row.map(escapeCSV).join(','))
  })
  const csvContent = csvLines.join('\n')

  // 打开保存对话�?
  const { canceled, filePath } = await window.electronAPI.invoke('dialog:showSaveDialog', {
    title: '导出用户列表',
    defaultPath: `用户列表_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`,
    filters: [
      { name: 'CSV 文件', extensions: ['csv'] },
        { name: '所有文件', extensions: ['*'] }
    ]
  })

  if (canceled || !filePath) return

  try {
    const bom = '\uFEFF'
    await window.electronAPI.invoke('fs:writeFile', filePath, bom + csvContent)
    await showAlert(`导出成功！\n文件保存至：${filePath}`)
  } catch (err) {
    await showAlert(`导出失败：${err.message}`)
  }
}

const goBack = () => {
  router.back()
}

const logout = () => {
  localStorage.removeItem('currentUser')
  router.push('/login')
}

onMounted(() => {
  if (!currentUser.value.id) {
    router.push('/login')
    return
  }
  loadUsers()
})
</script>
