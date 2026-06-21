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
          <img src="../assets/images/logo.png" alt="logo" class="h-8 w-8 flex-shrink-0">
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
      <!-- 头部 -->
      <header class="bg-white border-b border-gray-200 shadow-sm z-30 h-16 flex items-center justify-between px-6 sticky top-0">
        <div class="text-2xl font-bold text-blue-800 shrink-0">试卷智能校验系统</div>
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

      <!-- 设置页面主体 -->
      <main class="flex-1 bg-white overflow-auto p-6 md:p-8 flex flex-col min-w-0">
        <h2 class="text-2xl font-bold text-blue-800 mb-6">系统设置</h2>

        <!-- 1. API 配置管理 -->
        <section class="mb-8">
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-lg font-semibold text-gray-800">API 配置管理</h3>
            <button @click="openApiDialog()" class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm">添加 API</button>
          </div>

          <div class="mb-4 flex items-center space-x-3">
            <label class="text-sm font-medium text-gray-700">当前使用的 API：</label>
            <select
              v-model="activeApiId"
              @change="onActiveApiChange"
              class="border border-gray-300 rounded-md px-3 py-1.5 text-sm bg-white focus:ring-2 focus:ring-blue-500"
            >
              <option :value="null">未选择</option>
              <option v-for="api in apiConfigs" :key="api.id" :value="api.id">{{ api.name }} ({{ api.model }})</option>
            </select>
          </div>

          <div class="flex items-center gap-3 mb-4 flex-wrap">
            <input
              v-model="apiSearch"
              type="text"
              placeholder="搜索 API 名称/端点/模型..."
              class="px-3 py-1.5 border border-gray-300 rounded-md text-sm w-64 focus:ring-2 focus:ring-blue-500"
              autocomplete="off"
            />
            <div class="flex items-center gap-2">
              <label class="text-xs text-gray-600">排序：</label>
              <select v-model="apiSortBy" class="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:border-blue-500">
                <option value="name">名称</option>
                <option value="model">模型</option>
                <option value="endpoint">端点</option>
              </select>
              <button
                @click="apiSortOrder = apiSortOrder === 'asc' ? 'desc' : 'asc'"
                class="p-1 text-gray-600 hover:text-blue-600 transition-colors"
                :title="apiSortOrder === 'asc' ? '升序' : '降序'"
              >
                <svg v-if="apiSortOrder === 'asc'" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>

          <!-- API 表格 -->
          <div :style="apiConfigs.length > 5 ? { maxHeight: '300px', overflowY: 'auto' } : {}">
            <table class="min-w-full divide-y divide-gray-200 border rounded-lg">
              <thead class="bg-gray-50 sticky top-0">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">端点</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">模型</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">API Key</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">本地 API</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white">
                <tr v-for="api in filteredApiConfigs" :key="api.id">
                  <td class="px-4 py-2 text-sm text-gray-700">{{ api.name }}</td>
                  <td class="px-4 py-2 text-sm text-gray-700">{{ api.endpoint }}</td>
                  <td class="px-4 py-2 text-sm text-gray-700">{{ api.model }}</td>
                  <td class="px-4 py-2 text-sm text-gray-700 font-mono">{{ maskString(api.api_key) }}</td>
                  <td class="px-4 py-2 text-sm text-gray-700">{{ api.is_local ? '是' : '否' }}</td>
                  <td class="px-4 py-2 text-center space-x-2">
                    <button @click="openApiDialog(api)" class="text-blue-600 hover:text-blue-800 text-sm">编辑</button>
                    <button
                      @click="deleteApi(api.id)"
                      :disabled="isNlpApiName(api.name)"
                      :class="isNlpApiName(api.name) ? 'text-gray-400 cursor-not-allowed' : 'text-red-600 hover:text-red-800'"
                      class="text-sm"
                    >删除</button>
                  </td>
                </tr>
                <tr v-if="filteredApiConfigs.length === 0">
                  <td colspan="6" class="px-4 py-4 text-center text-gray-500 text-sm">暂无匹配的 API 配置</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 1.5 远程题库维护 -->
        <section class="mb-8">
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-lg font-semibold text-gray-800">远程题库维护</h3>
            <button @click="openRemoteDialog()" class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm">添加远程题库</button>
          </div>

          <div class="mb-4 flex items-center space-x-3">
            <input v-model="remoteSearch" type="text" placeholder="搜索名称/地址..." class="px-3 py-1.5 border border-gray-300 rounded-md text-sm w-64 focus:ring-2 focus:ring-blue-500" />
          </div>

          <div :style="remoteBanks.length > 5 ? { maxHeight: '300px', overflowY: 'auto' } : {}">
            <table class="min-w-full divide-y divide-gray-200 border rounded-lg">
              <thead class="bg-gray-50 sticky top-0">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">名称</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">端点</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">端口</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">状态</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white">
                <tr v-for="bank in filteredRemoteBanks" :key="bank.id">
                  <td class="px-4 py-2 text-sm text-gray-700">{{ bank.name }}</td>
                  <td class="px-4 py-2 text-sm text-gray-700 font-mono">{{ bank.endpoint }}</td>
                  <td class="px-4 py-2 text-sm text-gray-700">{{ bank.port }}</td>
                  <td class="px-4 py-2 text-sm text-gray-700">{{ bank.enabled ? '启用' : '禁用' }}</td>
                  <td class="px-4 py-2 text-center space-x-2">
                    <button @click="openRemoteDialog(bank)" class="text-blue-600 hover:text-blue-800 text-sm">编辑</button>
                    <button @click="deleteRemoteBank(bank.id)" class="text-red-600 hover:text-red-800 text-sm">删除</button>
                    <button @click="testRemoteBank(bank)" class="text-green-600 hover:text-green-800 text-sm">测试</button>
                  </td>
                </tr>
                <tr v-if="filteredRemoteBanks.length === 0">
                  <td colspan="5" class="px-4 py-4 text-center text-gray-500 text-sm">暂无远程题库</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- 远程题库编辑对话框 -->
          <div v-if="showRemoteDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
            <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
              <h4 class="text-lg font-semibold mb-4">{{ editingRemote ? '编辑远程题库' : '添加远程题库' }}</h4>
              <div class="space-y-3">
                <div><label class="block text-sm font-medium text-gray-700">名称 *</label><input v-model="remoteForm.name" type="text" class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm" placeholder="显示名称" /></div>
                <div><label class="block text-sm font-medium text-gray-700">端点 *</label><input v-model="remoteForm.endpoint" type="text" class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm" placeholder="例如：https://api.example.com 或 example.com" /></div>
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <label class="block text-sm font-medium text-gray-700">端口</label>
                    <input v-model.number="remoteForm.port" type="number" class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm" />
                  </div>
                  <div class="flex items-center"><label class="inline-flex items-center text-sm"><input type="checkbox" v-model="remoteForm.enabled" class="mr-2" /> <span>启用</span></label></div>
                </div>
              </div>
              <div class="mt-5 flex justify-end space-x-3">
                <button @click="closeRemoteDialog" class="px-4 py-2 text-sm text-gray-600 border rounded hover:bg-gray-50">取消</button>
                <button @click="saveRemoteBank" class="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">保存</button>
              </div>
            </div>
          </div>
        </section>

        <!-- 2. 学科维护 -->
        <section class="mb-8">
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-lg font-semibold text-gray-800">学科维护</h3>
            <button @click="openCourseDialog()" class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm">添加学科</button>
          </div>

          <div class="flex items-center gap-3 mb-4 flex-wrap">
            <input
              v-model="courseSearch"
              type="text"
              placeholder="搜索学科代码或名称..."
              class="px-3 py-1.5 border border-gray-300 rounded-md text-sm w-64 focus:ring-2 focus:ring-blue-500"
              autocomplete="off"
            />
            <div class="flex items-center gap-2">
              <label class="text-xs text-gray-600">排序：</label>
              <select v-model="courseSortBy" class="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:border-blue-500">
                <option value="code">代码</option>
                <option value="name">名称</option>
              </select>
              <button
                @click="courseSortOrder = courseSortOrder === 'asc' ? 'desc' : 'asc'"
                class="p-1 text-gray-600 hover:text-blue-600 transition-colors"
                :title="courseSortOrder === 'asc' ? '升序' : '降序'"
              >
                <svg v-if="courseSortOrder === 'asc'" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>

          <!-- 学科表格 -->
          <div :style="courses.length > 5 ? { maxHeight: '300px', overflowY: 'auto' } : {}">
            <table class="min-w-full divide-y divide-gray-200 border rounded-lg">
              <thead class="bg-gray-50 sticky top-0">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">学科代码</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">学科名称</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white">
                <tr v-for="course in filteredCourses" :key="course.code">
                  <td class="px-4 py-2 text-sm font-mono text-gray-700">{{ course.code }}</td>
                  <td class="px-4 py-2 text-sm text-gray-700">{{ course.name }}</td>
                  <td class="px-4 py-2 text-center space-x-2">
                    <button @click="openCourseDialog(course)" class="text-blue-600 hover:text-blue-800 text-sm">编辑</button>
                    <button @click="deleteCourse(course.code)" class="text-red-600 hover:text-red-800 text-sm">删除</button>
                  </td>
                </tr>
                <tr v-if="filteredCourses.length === 0">
                  <td colspan="3" class="px-4 py-4 text-center text-gray-500 text-sm">暂无匹配的学科</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 3. 学院管理 -->
        <section class="mb-8">
          <div class="flex justify-between items-center mb-3">
            <h3 class="text-lg font-semibold text-gray-800">学院管理</h3>
            <button @click="openCollegeDialog()" class="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm">添加学院</button>
          </div>

          <div class="flex items-center gap-3 mb-4 flex-wrap">
            <input
              v-model="collegeSearch"
              type="text"
              placeholder="搜索学院名称..."
              class="px-3 py-1.5 border border-gray-300 rounded-md text-sm w-64 focus:ring-2 focus:ring-blue-500"
              autocomplete="off"
            />
            <div class="flex items-center gap-2">
              <label class="text-xs text-gray-600">排序：</label>
              <select v-model="collegeSortBy" class="text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:border-blue-500">
                <option value="name">名称</option>
              </select>
              <button
                @click="collegeSortOrder = collegeSortOrder === 'asc' ? 'desc' : 'asc'"
                class="p-1 text-gray-600 hover:text-blue-600 transition-colors"
                :title="collegeSortOrder === 'asc' ? '升序' : '降序'"
              >
                <svg v-if="collegeSortOrder === 'asc'" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>

          <!-- 学院表格 -->
          <div :style="colleges.length > 5 ? { maxHeight: '300px', overflowY: 'auto' } : {}">
            <table class="min-w-full divide-y divide-gray-200 border rounded-lg">
              <thead class="bg-gray-50 sticky top-0">
                <tr>
                  <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">学院名称</th>
                  <th class="px-4 py-2 text-center text-xs font-medium text-gray-500 uppercase">操作</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 bg-white">
                <tr v-for="college in filteredColleges" :key="college.id">
                  <td class="px-4 py-2 text-sm text-gray-700">{{ college.name }}</td>
                  <td class="px-4 py-2 text-center space-x-2">
                    <button @click="openCollegeDialog(college)" class="text-blue-600 hover:text-blue-800 text-sm">编辑</button>
                    <button @click="deleteCollege(college.id)" class="text-red-600 hover:text-red-800 text-sm">删除</button>
                  </td>
                </tr>
                <tr v-if="filteredColleges.length === 0">
                  <td colspan="2" class="px-4 py-4 text-center text-gray-500 text-sm">暂无匹配的学院</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- 4. AI 使用默认值 -->
        <section class="mb-8">
          <h3 class="text-lg font-semibold text-gray-800 mb-3">AI 使用默认值</h3>
          <div class="flex flex-col space-y-3">
            <label class="flex items-center justify-between">
              <span class="text-gray-700">启用 AI 切分</span>
              <div
                @click="toggleAiSplit"
                :class="['relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 cursor-pointer', aiSplitEnabled ? 'bg-blue-600' : 'bg-gray-300']"
              >
                <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200', aiSplitEnabled ? 'translate-x-6' : 'translate-x-1']" />
              </div>
            </label>
            <label class="flex items-center justify-between">
              <span class="text-gray-700">启用 AI 报告生成</span>
              <div
                @click="toggleAiReport"
                :class="['relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 cursor-pointer', aiReportEnabled ? 'bg-blue-600' : 'bg-gray-300']"
              >
                <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200', aiReportEnabled ? 'translate-x-6' : 'translate-x-1']" />
              </div>
            </label>
          </div>
        </section>

        <!-- 5. AI 切分提示词 -->
        <section class="mb-8">
          <h3 class="text-lg font-semibold text-gray-800 mb-3">AI 切分提示词</h3>
          <textarea v-model="splitPrompt" @blur="saveSetting('split_prompt', splitPrompt)" rows="6" class="w-full border border-gray-300 rounded-lg p-3 text-sm font-mono bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:outline-none" placeholder="请输入提示词模板..."></textarea>
        </section>

        <!-- 6. 重复度阈值 -->
        <section class="mb-8">
          <h3 class="text-lg font-semibold text-gray-800 mb-3">查重敏感度 (重复度阈值)</h3>
          <div class="flex items-center space-x-4">
            <input type="range" min="0" max="100" v-model.number="similarityThreshold" @change="saveSetting('similarity_threshold', similarityThreshold)" class="w-64 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600" />
            <span class="text-sm font-medium text-gray-700 w-12">{{ similarityThreshold }}%</span>
          </div>
        </section>

        <!-- 7. 格式校验项目 -->
        <section>
          <h3 class="text-lg font-semibold text-gray-800 mb-3">格式校验项目</h3>
          <div class="flex flex-col space-y-2">
            <div v-for="item in formatCheckItems" :key="item.code" class="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-2 border">
              <span class="text-sm text-gray-700">{{ item.name }}</span>
              <div
                @click="toggleFormatCheck(item.code)"
                :class="['relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 cursor-pointer', formatChecks[item.code] ? 'bg-blue-600' : 'bg-gray-300']"
              >
                <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200', formatChecks[item.code] ? 'translate-x-6' : 'translate-x-1']" />
              </div>
            </div>
          </div>
        </section>

        <!-- 自定义对话框 -->
        <div v-if="dialogVisible" class="fixed inset-0 z-[100] flex items-center justify-center bg-black bg-opacity-30">
          <div class="bg-white rounded-xl p-6 w-80 shadow-2xl border border-gray-200">
            <h3 class="text-lg font-bold mb-2">{{ dialogTitle }}</h3>
            <p class="text-sm text-gray-700 mb-6">{{ dialogMessage }}</p>
            <div class="flex justify-end gap-3">
              <button v-if="dialogType === 'confirm'" @click="handleDialogCancel" class="px-4 py-2 text-sm rounded-md bg-gray-200 hover:bg-gray-300">取消</button>
              <button @click="handleDialogConfirm" class="px-4 py-2 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700">{{ dialogType === 'alert' ? '确定' : '确认' }}</button>
            </div>
          </div>
        </div>

        <!-- API 编辑对话框 -->
        <div v-if="showApiDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
          <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h4 class="text-lg font-semibold mb-4">{{ editingApi ? '编辑 API' : '添加 API' }}</h4>
            <div class="space-y-3">
              <div>
                <label class="block text-sm font-medium text-gray-700">名称 *</label>
                <input
                  v-model="apiForm.name"
                  :disabled="isEditingNlpApi"
                  type="text"
                  class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm"
                  placeholder="请输入 API 名称"
                />
                <p v-if="isEditingNlpApi" class="mt-1 text-xs text-gray-500">NLP 名称的配置不可修改名称，仅可修改其它字段。</p>
              </div>
              <div><label class="block text-sm font-medium text-gray-700">Endpoint *</label><input v-model="apiForm.endpoint" type="text" class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm" placeholder="请输入 API 端点地址" /></div>
              <div><label class="block text-sm font-medium text-gray-700">模型 *</label><input v-model="apiForm.model" type="text" class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm" placeholder="请输入模型名称" /></div>
              <div>
                <label class="block text-sm font-medium text-gray-700">API Key *</label>
                <input
                  v-model="apiForm.api_key"
                  type="password"
                  class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm"
                  :placeholder="editingApi ? '●●●●●●●● (留空则不修改)' : '请输入 API Key'"
                />
              </div>
              <div class="flex items-center">
                <label class="inline-flex items-center text-sm">
                  <input type="checkbox" v-model="apiForm.is_local" class="mr-2" />
                  <span>本地 API（例如直接访问本机服务或本地模型）</span>
                </label>
              </div>
            </div>
            <div class="mt-5 flex justify-end space-x-3">
              <button @click="closeApiDialog" class="px-4 py-2 text-sm text-gray-600 border rounded hover:bg-gray-50">取消</button>
              <button @click="saveApi" class="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">保存</button>
            </div>
          </div>
        </div>

        <!-- 学科编辑对话框 -->
        <div v-if="showCourseDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
          <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h4 class="text-lg font-semibold mb-4">{{ editingCourse ? '编辑学科' : '添加学科' }}</h4>
            <div class="space-y-3">
              <div>
                <label class="block text-sm font-medium text-gray-700">学科代码</label>
                <input v-model="courseForm.code" type="text" class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm" placeholder="请输入学科代码" :disabled="editingCourse !== null" />
              </div>
              <div><label class="block text-sm font-medium text-gray-700">学科名称</label><input v-model="courseForm.name" type="text" class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm" placeholder="请输入学科名称" /></div>
            </div>
            <div class="mt-5 flex justify-end space-x-3">
              <button @click="closeCourseDialog" class="px-4 py-2 text-sm text-gray-600 border rounded hover:bg-gray-50">取消</button>
              <button @click="saveCourse" class="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">保存</button>
            </div>
          </div>
        </div>

        <!-- 学院编辑对话框 -->
        <div v-if="showCollegeDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30">
          <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
            <h4 class="text-lg font-semibold mb-4">{{ editingCollege ? '编辑学院' : '添加学院' }}</h4>
            <div class="space-y-3">
              <div><label class="block text-sm font-medium text-gray-700">学院名称</label><input v-model="collegeForm.name" type="text" class="mt-1 block w-full border border-gray-300 rounded-md p-2 text-sm" placeholder="请输入学院名称" /></div>
            </div>
            <div class="mt-5 flex justify-end space-x-3">
              <button @click="closeCollegeDialog" class="px-4 py-2 text-sm text-gray-600 border rounded hover:bg-gray-50">取消</button>
              <button @click="saveCollege" class="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700">保存</button>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
/**
 * setting.vue - 系统设置页面
 *
 * 管理以下配置模块：
 * 1. API 配置管理（LLM 服务的增删改查、当前激活选择）
 * 2. 远程题库维护（MongoDB 连接的增删改测）
 * 3. 学科维护（学科代码/名称的 CRUD）
 * 4. 学院管理（学院名称的 CRUD）
 * 5. AI 默认值（切分/报告功能的默认开关）
 * 6. AI 切分提示词（自定义 prompt 模板）
 * 7. 重复度阈值（敏感度滑块 0-100%）
 * 8. 格式校验项目（9 项开关配置）
 */
import { ref, reactive, computed, onMounted, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'

// ==================== 侧边栏控制 ====================
const isCollapsed = ref(true)
const toggleSidebar = () => isCollapsed.value = !isCollapsed.value

// ==================== 用户信息 ====================
const currentUser = ref({ fullName: '', employeeId: '' })
const router = useRouter()
const route = useRoute()

const goToProfile = () => { router.push('/profile') }
const logout = () => { localStorage.removeItem('currentUser'); router.push('/login') }

// ==================== 菜单配置 ====================
const menuItems = [
  { id: 'home', name: '主页', icon: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', class: 'w-5 h-5' }, [ h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' }) ]) },
  { id: 'history', name: '历史项目', icon: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', class: 'w-5 h-5' }, [ h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' }) ]) },
  { id: 'question-bank', name: '试卷管理', icon: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', class: 'w-5 h-5' }, [ h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253' }) ]) },
  { id: 'settings', name: '设置', icon: () => h('svg', { fill: 'none', viewBox: '0 0 24 24', stroke: 'currentColor', class: 'w-5 h-5' }, [ h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }), h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z' }) ]) }
]

const routeMap = {
  home: { name: 'Menu', path: '/menu' },
  'new-task': { name: 'newtask', path: '/new-task' },
  history: { name: 'history', path: '/history' },
  'question-bank': { name: 'question-bank', path: '/question-bank' },
  settings: { name: 'Settings', path: '/settings' }
}
const navigateTo = (page) => {
  const target = routeMap[page]
  if (!target) return
  if (target.name) {
    router.push({ name: target.name }).catch(err => { if (err.name !== 'NavigationDuplicated') console.error(err) })
  } else if (target.path) {
    router.push(target.path).catch(err => { if (err.name !== 'NavigationDuplicated') console.error(err) })
  }
}
const isActive = (id) => {
  const currentRoute = route
  const target = routeMap[id]
  if (!target) return false
  if (id === 'home') return currentRoute.path === '/' || currentRoute.name === 'Menu'
  return target.name ? currentRoute.name === target.name : currentRoute.path === target.path
}

const electronAPI = window.electronAPI

// ==================== API 配置管理 ====================
const apiConfigs = ref([])
const apiSearch = ref('')
const apiSortBy = ref('name')
const apiSortOrder = ref('asc')
const filteredApiConfigs = computed(() => {
  const kw = apiSearch.value.trim().toLowerCase()
  let list = apiConfigs.value
  if (kw) list = list.filter(api => api.name.toLowerCase().includes(kw) || api.endpoint.toLowerCase().includes(kw) || api.model.toLowerCase().includes(kw))
  return [...list].sort((a, b) => {
    let valA, valB
    if (apiSortBy.value === 'name') { valA = a.name.toLowerCase(); valB = b.name.toLowerCase() }
    else if (apiSortBy.value === 'model') { valA = a.model.toLowerCase(); valB = b.model.toLowerCase() }
    else { valA = a.endpoint.toLowerCase(); valB = b.endpoint.toLowerCase() }
    if (valA < valB) return apiSortOrder.value === 'asc' ? -1 : 1
    if (valA > valB) return apiSortOrder.value === 'asc' ? 1 : -1
    return 0
  })
})
const activeApiId = ref(null)
const showApiDialog = ref(false)
const editingApi = ref(null)
const apiForm = reactive({ name: '', endpoint: '', model: '', api_key: '', is_local: false })

// NLP 内置 API 的特殊处理（不允许删除/重命名）
const isNlpApiName = (name) => String(name || '').trim().toLowerCase() === 'nlp'
const isEditingNlpApi = computed(() => editingApi.value && isNlpApiName(editingApi.value.name))
const hasNlpApi = () => apiConfigs.value.some(api => isNlpApiName(api.name))

// ==================== 远程题库维护 ====================
const remoteBanks = ref([])
const remoteSearch = ref('')
const filteredRemoteBanks = computed(() => {
  const kw = remoteSearch.value.trim().toLowerCase()
  let list = remoteBanks.value || []
  if (kw) list = list.filter(r => r.name.toLowerCase().includes(kw) || (r.endpoint || '').toLowerCase().includes(kw))
  return list
})
const showRemoteDialog = ref(false)
const editingRemote = ref(null)
const remoteForm = reactive({ id: null, name: '', endpoint: 'http://127.0.0.1', port: 80, enabled: true, timeout: 5000 })

function openRemoteDialog(bank = null) {
  editingRemote.value = bank
  if (bank) {
    remoteForm.id = bank.id
    remoteForm.name = bank.name
    remoteForm.endpoint = bank.endpoint || (bank.protocol && bank.address ? `${bank.protocol}://${bank.address}` : 'http://127.0.0.1')
    remoteForm.port = bank.port || 80
    remoteForm.enabled = bank.enabled !== false
  } else {
    remoteForm.id = null
    remoteForm.name = ''
    remoteForm.endpoint = 'http://127.0.0.1'
    remoteForm.port = 80
    remoteForm.enabled = true
  }
  showRemoteDialog.value = true
}
function closeRemoteDialog() { showRemoteDialog.value = false; editingRemote.value = null }
async function saveRemoteBank() {
  if (!remoteForm.name.trim()) { await showAlert('名称不能为空'); return }
  if (!remoteForm.endpoint.trim()) { await showAlert('端点不能为空'); return }
  try {
    if (remoteForm.id) {
      const data = { name: remoteForm.name.trim(), endpoint: remoteForm.endpoint.trim(), port: Number(remoteForm.port), enabled: !!remoteForm.enabled }
      await electronAPI.invoke('remoteBanks:update', remoteForm.id, data)
    } else {
      await electronAPI.invoke('remoteBanks:add', { name: remoteForm.name.trim(), endpoint: remoteForm.endpoint.trim(), port: Number(remoteForm.port), enabled: !!remoteForm.enabled })
    }
    const list = await electronAPI.invoke('remoteBanks:list')
    remoteBanks.value = list || []
    closeRemoteDialog()
  } catch (e) { await showAlert('保存失败：' + e.message) }
}
async function deleteRemoteBank(id) {
  const ok = await showConfirm('确定要删除该远程题库吗？')
  if (!ok) return
  try {
    await electronAPI.invoke('remoteBanks:delete', id)
    const list = await electronAPI.invoke('remoteBanks:list')
    remoteBanks.value = list || []
  } catch (e) { await showAlert('删除失败：' + e.message) }
}
async function testRemoteBank(bank) {
  try {
    const payload = {
      endpoint: bank && bank.endpoint ? bank.endpoint : undefined,
      port: bank && bank.port ? Number(bank.port) : undefined,
      timeout: bank && bank.timeout ? Number(bank.timeout) : undefined
    }
    const res = await electronAPI.invoke('remoteBanks:test', payload)
    if (res && res.success) {
      await showAlert('连接成功 (HTTP ' + (res.statusCode || '') + ')')
    } else {
      await showAlert('连接失败：' + (res.error || ('HTTP ' + (res.statusCode || ''))))
    }
  } catch (e) { await showAlert('测试失败：' + e.message) }
}

// ==================== 学科维护 ====================
const courses = ref([])
const courseSearch = ref('')
const courseSortBy = ref('code')
const courseSortOrder = ref('asc')
const filteredCourses = computed(() => {
  const kw = courseSearch.value.trim().toLowerCase()
  let list = courses.value
  if (kw) list = list.filter(c => c.code.toLowerCase().includes(kw) || c.name.toLowerCase().includes(kw))
  return [...list].sort((a, b) => {
    let valA, valB
    if (courseSortBy.value === 'code') { valA = a.code.toLowerCase(); valB = b.code.toLowerCase() }
    else { valA = a.name.toLowerCase(); valB = b.name.toLowerCase() }
    if (valA < valB) return courseSortOrder.value === 'asc' ? -1 : 1
    if (valA > valB) return courseSortOrder.value === 'asc' ? 1 : -1
    return 0
  })
})
const showCourseDialog = ref(false)
const editingCourse = ref(null)
const courseForm = reactive({ code: '', name: '' })

// ==================== 学院管理 ====================
const colleges = ref([])
const collegeSearch = ref('')
const collegeSortBy = ref('name')
const collegeSortOrder = ref('asc')
const filteredColleges = computed(() => {
  const kw = collegeSearch.value.trim().toLowerCase()
  let list = colleges.value
  if (kw) list = list.filter(c => c.name.toLowerCase().includes(kw))
  return [...list].sort((a, b) => {
    let valA = a.name.toLowerCase(), valB = b.name.toLowerCase()
    if (valA < valB) return collegeSortOrder.value === 'asc' ? -1 : 1
    if (valA > valB) return collegeSortOrder.value === 'asc' ? 1 : -1
    return 0
  })
})
const showCollegeDialog = ref(false)
const editingCollege = ref(null)
const collegeForm = reactive({ name: '' })

// ==================== AI 设置 ====================
const aiSplitEnabled = ref(false)
const aiReportEnabled = ref(false)
const splitPrompt = ref('')
const similarityThreshold = ref(50)

// ==================== 格式校验项目 ====================
const formatCheckItems = [
  { code: 'SUBJECT_NAME_CORRECT_FILLED', name: '科目名称是否正确填写', default: true },
  { code: 'SUBJECT_CODE_CORRECT_FILLED', name: '科目代码是否正确填写', default: true },
  { code: 'SUBJECT_NAME_AND_CODE_NOT_MATCH', name: '科目名称与代码是否匹配', default: true },
  { code: 'HEADER_SUBJECT_CODE_CORRECT_CONSISTENT', name: '每页的页眉科目代码是否正确填写且与首页一致', default: true },
  { code: 'PAGE_NUM_CORRECT_FILLED', name: '当前页脚的页数/总页码是否正确填写（如：第x页，共x页）', default: false },
  { code: 'ALL_SECTIONS_MARKED_POINTS', name: '所有章节均标记分值', default: true },
  { code: 'TOTAL_SCORE_IN_PREDETERMINED_RANGE', name: '总分在预设范围内', default: true },
  { code: 'SEQ_CORRECT_FILLED', name: '章节/题目的序号是否正确填写', default: true },
  { code: 'OPTIONS_NO_DUPLICATE', name: '对于所有选择题，选项编号和选项内容均无重复', default: true }
]
const formatChecks = reactive({})
formatCheckItems.forEach(item => { formatChecks[item.code] = item.default })

function maskString(str) {
  if (!str) return ''
  if (str.length <= 8) return '****'
  return str.substring(0, 4) + '****' + str.substring(str.length - 4)
}

// 自定义对话框
const dialogVisible = ref(false)
const dialogTitle = ref('')
const dialogMessage = ref('')
const dialogType = ref('alert')
let dialogResolve = null
const showAlert = (msg) => new Promise(resolve => { dialogTitle.value = '提示'; dialogMessage.value = msg; dialogType.value = 'alert'; dialogVisible.value = true; dialogResolve = resolve })
const showConfirm = (msg) => new Promise(resolve => { dialogTitle.value = '确认'; dialogMessage.value = msg; dialogType.value = 'confirm'; dialogVisible.value = true; dialogResolve = resolve })
const handleDialogConfirm = () => { dialogVisible.value = false; dialogResolve?.(true) }
const handleDialogCancel = () => { dialogVisible.value = false; dialogResolve?.(false) }

// 加载数据
async function loadSettings() {
  try {
    const settings = await electronAPI.invoke('settings:get')
    if (settings) {
      aiSplitEnabled.value = settings.ai_split_enabled ?? false
      aiReportEnabled.value = settings.ai_report_enabled ?? false
      splitPrompt.value = settings.split_prompt ?? ''
      similarityThreshold.value = settings.similarity_threshold ?? 50
      activeApiId.value = settings.active_api_id ?? null
      if (settings.format_checks) {
        const existingCodes = new Set(formatCheckItems.map(i => i.code))
        Object.keys(settings.format_checks).forEach(code => {
          if (existingCodes.has(code)) formatChecks[code] = settings.format_checks[code]
        })
      }
    }
    const apis = await electronAPI.invoke('apiconfig:list')
    apiConfigs.value = apis || []
    if (activeApiId.value && !apiConfigs.value.some(a => a.id === activeApiId.value)) {
      activeApiId.value = null
      await saveSetting('active_api_id', null)
    }
    try {
      const rbs = await electronAPI.invoke('remoteBanks:list')
      remoteBanks.value = rbs || []
    } catch (e) { console.warn('加载远程题库失败', e) }
    const allCourses = await electronAPI.invoke('course:listAll')
    courses.value = allCourses || []
    const allColleges = await electronAPI.invoke('college:listAll')
    colleges.value = allColleges || []
  } catch (e) { console.error('加载设置失败', e) }
}

async function saveSetting(key, value) {
  try { await electronAPI.invoke('settings:update', { key, value }) } catch (e) { console.error('保存设置失败', e) }
}

function toggleAiSplit() { aiSplitEnabled.value = !aiSplitEnabled.value; saveSetting('ai_split_enabled', aiSplitEnabled.value) }
function toggleAiReport() { aiReportEnabled.value = !aiReportEnabled.value; saveSetting('ai_report_enabled', aiReportEnabled.value) }
function toggleFormatCheck(code) { formatChecks[code] = !formatChecks[code]; saveSetting('format_checks', { ...formatChecks }) }
function onActiveApiChange() { saveSetting('active_api_id', activeApiId.value) }

// API 增删改
function openApiDialog(api = null) {
  editingApi.value = api
  if (api) {
    apiForm.name = isNlpApiName(api.name) ? 'NLP' : api.name
    apiForm.endpoint = api.endpoint
    apiForm.model = api.model
    apiForm.api_key = ''
    apiForm.is_local = api.is_local ?? false
  } else {
    apiForm.name = ''
    apiForm.endpoint = ''
    apiForm.model = ''
    apiForm.api_key = ''
    apiForm.is_local = false
  }
  showApiDialog.value = true
}
function closeApiDialog() { showApiDialog.value = false; editingApi.value = null }
async function saveApi() {
  if (!apiForm.name.trim()) { await showAlert('名称不能为空'); return }
  if (!apiForm.endpoint.trim()) { await showAlert('Endpoint 不能为空'); return }
  if (!apiForm.model.trim()) { await showAlert('模型不能为空'); return }
  if (editingApi.value) {
    const keyValue = apiForm.api_key.trim()
    if (apiForm.api_key !== '' && keyValue === '') { await showAlert('API Key 不能为空'); return }
    if (isEditingNlpApi.value) {
      apiForm.name = 'NLP'
    } else if (isNlpApiName(apiForm.name)) {
      await showAlert('不能将 API 名称修改为 NLP'); return
    }
  } else {
    if (!apiForm.api_key.trim()) { await showAlert('API Key 不能为空'); return }
    if (isNlpApiName(apiForm.name) && hasNlpApi()) { await showAlert('当前已有 NLP 名称的 API，不允许新增另一个'); return }
  }
  try {
    if (editingApi.value) {
      const data = { name: apiForm.name.trim(), endpoint: apiForm.endpoint.trim(), model: apiForm.model.trim() }
      const newKey = apiForm.api_key.trim()
      if (newKey !== '') data.api_key = newKey
      data.is_local = !!apiForm.is_local
      await electronAPI.invoke('apiconfig:update', editingApi.value.id, data)
    } else {
      await electronAPI.invoke('apiconfig:add', { name: apiForm.name.trim(), endpoint: apiForm.endpoint.trim(), model: apiForm.model.trim(), api_key: apiForm.api_key.trim(), is_local: !!apiForm.is_local })
    }
    const apis = await electronAPI.invoke('apiconfig:list')
    apiConfigs.value = apis || []
    if (activeApiId.value && !apiConfigs.value.some(a => a.id === activeApiId.value)) { activeApiId.value = null; await saveSetting('active_api_id', null) }
    closeApiDialog()
  } catch (e) { await showAlert('保存失败：' + e.message) }
}
async function deleteApi(id) {
  const api = apiConfigs.value.find(item => item.id === id)
  if (api && isNlpApiName(api.name)) {
    await showAlert('NLP 名称的 API 不允许删除');
    return
  }
  const ok = await showConfirm('确定要删除该 API 配置吗？')
  if (!ok) return
  try {
    await electronAPI.invoke('apiconfig:delete', id)
    const apis = await electronAPI.invoke('apiconfig:list')
    apiConfigs.value = apis || []
    if (activeApiId.value === id) { activeApiId.value = null; await saveSetting('active_api_id', null) }
  } catch (e) { await showAlert('删除失败：' + e.message) }
}

// 学科增删改
function openCourseDialog(course = null) {
  editingCourse.value = course
  if (course) { courseForm.code = course.code; courseForm.name = course.name }
  else { courseForm.code = ''; courseForm.name = '' }
  showCourseDialog.value = true
}
function closeCourseDialog() { showCourseDialog.value = false; editingCourse.value = null }
async function saveCourse() {
  const code = courseForm.code.trim()
  const name = courseForm.name.trim()
  if (!code || !name) { await showAlert('学科代码和名称不能为空'); return }
  try {
    if (editingCourse.value) {
      await electronAPI.invoke('course:update', editingCourse.value.code, code, name)
    } else {
      await electronAPI.invoke('course:add', { code, name })
    }
    const all = await electronAPI.invoke('course:listAll')
    courses.value = all || []
    closeCourseDialog()
  } catch (e) { await showAlert('保存失败：' + e.message) }
}
async function deleteCourse(code) {
  const ok = await showConfirm(`确定要删除学科“${code}”吗？`)
  if (!ok) return
  try {
    await electronAPI.invoke('course:delete', code)
    const all = await electronAPI.invoke('course:listAll')
    courses.value = all || []
  } catch (e) { await showAlert('删除失败：' + e.message) }
}

// 学院增删改
function openCollegeDialog(college = null) {
  editingCollege.value = college
  collegeForm.name = college ? college.name : ''
  showCollegeDialog.value = true
}
function closeCollegeDialog() { showCollegeDialog.value = false; editingCollege.value = null }
async function saveCollege() {
  const name = collegeForm.name.trim()
  if (!name) { await showAlert('学院名称不能为空'); return }
  try {
    if (editingCollege.value) {
      await electronAPI.invoke('college:update', editingCollege.value.id, name)
    } else {
      await electronAPI.invoke('college:add', name)
    }
    const all = await electronAPI.invoke('college:listAll')
    colleges.value = all || []
    closeCollegeDialog()
  } catch (e) { await showAlert('保存失败：' + e.message) }
}
async function deleteCollege(id) {
  const college = colleges.value.find(c => c.id === id)
  const ok = await showConfirm(`确定要删除学院“${college?.name}”吗？`)
  if (!ok) return
  try {
    await electronAPI.invoke('college:delete', id)
    const all = await electronAPI.invoke('college:listAll')
    colleges.value = all || []
  } catch (e) { await showAlert('删除失败：' + e.message) }
}

// 生命周期
onMounted(async () => {
  const storedUser = localStorage.getItem('currentUser')
  if (!storedUser) { router.push('/login'); return }
  try {
    const user = JSON.parse(storedUser)
    currentUser.value = user
  } catch (e) { router.push('/login'); return }
  await loadSettings()
})
</script>

<style scoped>
.transition-all { transition-property: all; }
.section-table-container::-webkit-scrollbar { width: 6px; }
.section-table-container::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }
</style>