const { contextBridge, ipcRenderer } = require('electron');

// 原有独立 API（保持不变）
contextBridge.exposeInMainWorld('courseAPI', {
  search: (keyword) => ipcRenderer.invoke('course:search', keyword),
  add: (data) => ipcRenderer.invoke('course:add', data),
  listAll: () => ipcRenderer.invoke('course:listAll')
});

contextBridge.exposeInMainWorld('projectAPI', {
  getByName: (name) => ipcRenderer.invoke('project:getByName', name),
  save: (data) => ipcRenderer.invoke('project:save', data),
  list: () => ipcRenderer.invoke('project:list'),
  delete: (name) => ipcRenderer.invoke('project:delete', name),
  update: (oldName, data) => ipcRenderer.invoke('project:update', oldName, data)
});

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

// 扩展 electronAPI
contextBridge.exposeInMainWorld('electronAPI', {
  // 通用调用方式
  invoke: (channel, ...args) => ipcRenderer.invoke(channel, ...args),

  // 结构化模块
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

  // 用户管理模块
  user: {
    list: () => ipcRenderer.invoke('user:list'),
    getById: (id) => ipcRenderer.invoke('user:getById', id),
    create: (userData) => ipcRenderer.invoke('user:create', userData),
    update: (id, updates) => ipcRenderer.invoke('user:update', id, updates),
    delete: (id) => ipcRenderer.invoke('user:delete', id),
    authenticate: (employeeId, password) => ipcRenderer.invoke('user:authenticate', employeeId, password)
  },

  // 远程题库维护（新增 fetchQuestions 方法）
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
