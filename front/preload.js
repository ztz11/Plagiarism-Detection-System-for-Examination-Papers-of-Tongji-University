/**
 * preload.js - Electron 预加载脚本
 *
 * 通过 contextBridge 安全地向渲染进程暴露 IPC 通信接口。
 * 所有与主进程（main.js）的通信均通过此处的 API 进行，
 * 渲染进程不可直接访问 Node.js 或 Electron API。
 *
 * 暴露的全局 API：
 * - courseAPI:    学科管理（搜索、添加、列表）
 * - projectAPI:   项目管理（增删改查）
 * - documentAPI:  文档管理（保存、关联、详情）
 * - electronAPI:  综合 API（设置、API配置、报告、相似度、格式校验、用户、远程题库）
 */

const { contextBridge, ipcRenderer } = require('electron');

// ==================== 学科 API ====================
contextBridge.exposeInMainWorld('courseAPI', {
  search: (keyword) => ipcRenderer.invoke('course:search', keyword),
  add: (data) => ipcRenderer.invoke('course:add', data),
  listAll: () => ipcRenderer.invoke('course:listAll')
});

// ==================== 项目 API ====================
contextBridge.exposeInMainWorld('projectAPI', {
  getByName: (name) => ipcRenderer.invoke('project:getByName', name),
  save: (data) => ipcRenderer.invoke('project:save', data),
  list: () => ipcRenderer.invoke('project:list'),
  delete: (name) => ipcRenderer.invoke('project:delete', name),
  update: (oldName, data) => ipcRenderer.invoke('project:update', oldName, data)
});

// ==================== 文档 API ====================
contextBridge.exposeInMainWorld('documentAPI', {
  save: (data) => ipcRenderer.invoke('document:save', data),
  listByProject: (projectName) => ipcRenderer.invoke('document:listByProject', projectName),
  listAll: () => ipcRenderer.invoke('document:listAll'),
  associate: (projectName, docId) => ipcRenderer.invoke('document:associate', projectName, docId),
  disassociate: (projectName, docId) => ipcRenderer.invoke('document:disassociate', projectName, docId),
  delete: (docId) => ipcRenderer.invoke('document:delete', docId),
  getDetail: (docId) => ipcRenderer.invoke('document:getDetail', docId),
  getProjectsByDocId: (docId) => ipcRenderer.invoke('document:getProjectsByDocId', docId),
  update: (docId, data) => ipcRenderer.invoke('document:update', docId, data)
});

// ==================== 综合 Electron API ====================
contextBridge.exposeInMainWorld('electronAPI', {
  // 通用 IPC 调用（可直接指定 channel）
  invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args),

  // ---- 结构化子模块 ----
  settings: {
    get: () => ipcRenderer.invoke('settings:get'),
    update: (key, value) => ipcRenderer.invoke('settings:update', { key, value })
  },
  apiConfig: {
    list: () => ipcRenderer.invoke('apiconfig:list'),
    add: (config) => ipcRenderer.invoke('apiconfig:add', config),
    update: (id, data) => ipcRenderer.invoke('apiconfig:update', id, data),
    delete: (id) => ipcRenderer.invoke('apiconfig:delete', id)
  },
  report: {
    saveOrUpdate: (projectName, reportData) => ipcRenderer.invoke('report:saveOrUpdate', projectName, reportData),
    getFull: (projectName) => ipcRenderer.invoke('report:getFull', projectName),
    delete: (projectName) => ipcRenderer.invoke('report:delete', projectName)
  },
  similarity: {
    add: (projectName, data) => ipcRenderer.invoke('similarity:add', projectName, data),
    listByProject: (projectName) => ipcRenderer.invoke('similarity:listByProject', projectName),
    delete: (resultId) => ipcRenderer.invoke('similarity:delete', resultId),
    deleteByProject: (projectName) => ipcRenderer.invoke('similarity:deleteByProject', projectName)
  },
  formatCheck: {
    saveBatch: (docId, checks) => ipcRenderer.invoke('formatcheck:saveBatch', docId, checks),
    getByDocId: (docId) => ipcRenderer.invoke('formatcheck:getByDocId', docId)
  },

  // ---- 用户管理模块 ----
  user: {
    list: () => ipcRenderer.invoke('user:list'),
    getById: (id) => ipcRenderer.invoke('user:getById', id),
    create: (userData) => ipcRenderer.invoke('user:create', userData),
    update: (id, updates) => ipcRenderer.invoke('user:update', id, updates),
    delete: (id) => ipcRenderer.invoke('user:delete', id),
    authenticate: (employeeId, password) => ipcRenderer.invoke('user:authenticate', employeeId, password)
  },

  // ---- 远程题库模块（支持 MongoDB 试卷抓取）----
  remoteBanks: {
    list: () => ipcRenderer.invoke('remoteBanks:list'),
    add: (data) => ipcRenderer.invoke('remoteBanks:add', data),
    update: (id, data) => ipcRenderer.invoke('remoteBanks:update', id, data),
    delete: (id) => ipcRenderer.invoke('remoteBanks:delete', id),
    test: (data) => ipcRenderer.invoke('remoteBanks:test', data),
    fetchPapers: (connection, query) => ipcRenderer.invoke('remoteBanks:fetchPapers', connection, query),
    fetchQuestions: (connection, paperId) => ipcRenderer.invoke('remoteBanks:fetchQuestions', connection, paperId)
  }
});
