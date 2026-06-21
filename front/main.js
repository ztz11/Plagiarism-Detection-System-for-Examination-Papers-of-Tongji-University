const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs').promises;

// ===================== 本地文件存储管理器 =====================
class FileStorageManager {
  constructor(baseDir) {
    // 备份目录：应用根目录下的 data 文件夹
    this.backupDir = path.join(baseDir, 'data');
  }

  /**
   * 将源文件复制到备份目录（自动添加时间戳前缀避免重名）
   * @param {string} sourcePath - 源文件完整路径
   * @returns {Promise<string>} 备份后的文件完整路径
   */
  async saveFile(sourcePath) {
    if (!sourcePath) {
      throw new Error('源文件路径不能为空');
    }

    // 检查源文件是否存在且可访问
    try {
      await fs.access(sourcePath);
    } catch {
      throw new Error(`源文件不存在或不可访问: ${sourcePath}`);
    }

    // 确保备份目录存在
    await fs.mkdir(this.backupDir, { recursive: true });

    const fileName = path.basename(sourcePath);
    const timestamp = Date.now();
    const destFileName = `${timestamp}_${fileName}`;
    const destPath = path.join(this.backupDir, destFileName);

    // 再次检查目标文件是否已存在（理论上时间戳保证唯一，仅作防御）
    try {
      await fs.access(destPath);
      throw new Error(`备份文件已存在（时间戳冲突，极罕见）: ${destFileName}`);
    } catch (err) {
      if (err.code !== 'ENOENT') throw err;
    }

    // 复制文件
    await fs.copyFile(sourcePath, destPath);
    console.log(`文件已备份到: ${destPath}`);
    return destPath;
  }

  /**
   * 删除指定的备份文件（带路径安全校验）
   * @param {string} filePath - 要删除的备份文件完整路径
   */
  async deleteFile(filePath) {
    if (!filePath) {
      throw new Error('文件路径不能为空');
    }

    // 检查文件是否存在，不存在则直接返回（幂等操作）
    try {
      await fs.access(filePath);
    } catch {
      console.warn(`备份文件不存在，无需删除: ${filePath}`);
      return;
    }

    // 安全检查：确保要删除的文件位于备份目录内，防止误删其他文件
    const normalizedPath = path.normalize(filePath);
    const normalizedBackupDir = path.normalize(this.backupDir);
    if (!normalizedPath.startsWith(normalizedBackupDir + path.sep)) {
      throw new Error(`安全限制：不允许删除备份目录以外的文件: ${filePath}`);
    }

    await fs.unlink(filePath);
    console.log(`已删除备份文件: ${filePath}`);
  }

  getBackupDir() {
    return this.backupDir;
  }
}

// --- 1. 课程管理器 (CourseManager) ---
class CourseManager {
  constructor(dbInstance) { this.db = dbInstance; }

  async listAll() {
    await this.db.read();
    return this.db.data.courses || [];
  }

  async search(keyword) {
    await this.db.read();
    const k = keyword.toLowerCase();
    return this.db.data.courses.filter(c =>
      c.code.toLowerCase().includes(k) || c.name.toLowerCase().includes(k)
    );
  }

  async add(code, name) {
    await this.db.read();
    if (this.db.data.courses.some(c => c.code === code)) {
      throw new Error('课程代码已存在');
    }
    if (this.db.data.courses.some(c => c.name === name)) {
      throw new Error('课程名称已存在');
    }
    this.db.data.courses.push({ code, name });
    await this.db.write();
    return { success: true };
  }

  async update(oldCode, newCode, newName) {
    await this.db.read();
    const index = this.db.data.courses.findIndex(c => c.code === oldCode);
    if (index === -1) throw new Error('课程不存在');
    if (newCode !== oldCode && this.db.data.courses.some(c => c.code === newCode)) {
      throw new Error('新课程代码已存在');
    }
    if (this.db.data.courses.some(c => c.name === newName && c.code !== oldCode)) {
      throw new Error('新课程名称已存在');
    }
    this.db.data.courses[index].code = newCode;
    this.db.data.courses[index].name = newName;
    await this.db.write();
    return { success: true };
  }

  async delete(code) {
    await this.db.read();
    const index = this.db.data.courses.findIndex(c => c.code === code);
    if (index === -1) throw new Error('课程不存在');
    this.db.data.courses.splice(index, 1);
    await this.db.write();
    return { success: true };
  }
}

// --- 2. 项目管理器 (ProjectManager) ---
class ProjectManager {
  constructor(dbInstance) { this.db = dbInstance; }

  async getByName(name) {
    await this.db.read();
    return this.db.data.projects.find(p => p.name === name) || null;
  }

  async saveToDb({ projectName, content, subjectCode, userName, totalScore }) {
    await this.db.read();
    if (this.db.data.projects.some(p => p.name === projectName)) throw new Error('数据库中已存在同名项目');
    const score = Number(totalScore);
    if (isNaN(score) || score === null || score === undefined) {
      throw new Error('试卷总分必须为有效数字');
    }
    this.db.data.projects.push({
      name: projectName, content, subjectCode, creator: userName,
      createTime: new Date().toISOString(), status: 0,
      mainDocId: null,
      totalScore: score
    });
    await this.db.write();
    return { success: true };
  }

  async list() { await this.db.read(); return this.db.data.projects || []; }

  async deleteByName(name) {
    await this.db.read();
    const index = this.db.data.projects.findIndex(p => p.name === name);
    if (index === -1) throw new Error('项目不存在');
    this.db.data.projects.splice(index, 1);
    this.db.data.documentProjects = (this.db.data.documentProjects || []).filter(r => r.projectName !== name);
    if (this.db.data.reports) {
      this.db.data.reports = this.db.data.reports.filter(r => r.projectName !== name);
    }
    if (this.db.data.similarityResults) {
      this.db.data.similarityResults = this.db.data.similarityResults.filter(s => s.projectName !== name);
    }
    await this.db.write();
    return { success: true };
  }

  async updateByName(oldName, { projectName, subjectCode, content, mainDocId, totalScore }) {
    await this.db.read();
    const project = this.db.data.projects.find(p => p.name === oldName);
    if (!project) throw new Error('项目不存在');
    if (projectName) project.name = projectName;
    if (subjectCode) project.subjectCode = subjectCode;
    if (content !== undefined) project.content = content;
    if (mainDocId !== undefined) project.mainDocId = mainDocId;
    if (totalScore !== undefined) {
      const score = Number(totalScore);
      if (isNaN(score)) throw new Error('试卷总分必须为有效数字');
      project.totalScore = score;
    }
    if (projectName && oldName !== projectName) {
      this.db.data.documentProjects = (this.db.data.documentProjects || []).map(r => {
        if (r.projectName === oldName) r.projectName = projectName;
        return r;
      });
      if (this.db.data.reports) {
        this.db.data.reports.forEach(r => { if (r.projectName === oldName) r.projectName = projectName; });
      }
      if (this.db.data.similarityResults) {
        this.db.data.similarityResults.forEach(s => { if (s.projectName === oldName) s.projectName = projectName; });
      }
    }
    await this.db.write();
    return { success: true };
  }
}

// --- 3. 文档与题目管理类 (DocumentManager) ---
class DocumentManager {
  constructor(dbInstance, fileStorage) {
    this.db = dbInstance;
    this.fileStorage = fileStorage;
  }

  async saveDocument({ projectName, fileName, blocks, questions, subjectCode, localFilePath, examYear, examCollege }) {
    await this.db.read();

    // 重名检查
    if (this.db.data.documents.some(doc => doc.name === fileName)) {
      throw new Error('文档名称已存在，请更换名称');
    }

    const docId = Date.now();
    const newDoc = {
      id: docId,
      name: fileName,
      createTime: new Date().toISOString(),
      status: 1,
      blocks: blocks,
      subjectCode: subjectCode || '',
      parsed: false,
      localFilePath: localFilePath || null,
      examYear: examYear || null,
      examCollege: examCollege || null
    };
    this.db.data.documents.push(newDoc);

    const newQuestions = questions.map((q, index) => ({
      id: Date.now() + index + 1,
      docId: docId,
      title: q.title,
      indices: q.indices,
      order: index,
      tag1: q.tag1 ?? '',
      tag2: q.tag2 ?? '',
      tag3: q.tag3 ?? '',
      type: q.type ?? '',
      score: (q.score != null && !isNaN(q.score)) ? Number(q.score) : 0
    }));
    this.db.data.questions.push(...newQuestions);

    if (projectName && projectName.trim() !== '') {
      this.db.data.documentProjects.push({ docId, projectName });
    }

    await this.db.write();
    return { success: true, docId };
  }

  async listByProject(projectName) {
    await this.db.read();
    const rels = (this.db.data.documentProjects || []).filter(r => r.projectName === projectName);
    const docIds = rels.map(r => r.docId);
    return this.db.data.documents
      .filter(doc => docIds.includes(doc.id))
      .map(({ id, name, createTime, status, subjectCode, parsed, examYear, examCollege }) => ({
        id, name, createTime, status,
        subjectCode: subjectCode || '',
        parsed: parsed || false,
        examYear: examYear || null,
        examCollege: examCollege || null
      }));
  }

  async listAllDocuments() {
    await this.db.read();
    return this.db.data.documents.map(d => ({
      id: d.id,
      name: d.name,
      createTime: d.createTime,
      subjectCode: d.subjectCode || '',
      parsed: d.parsed || false,
      localFilePath: d.localFilePath || null,
      examYear: d.examYear || null,
      examCollege: d.examCollege || null
    }));
  }

  async listColleges() {
    await this.db.read();
    return this.db.data.colleges || [];
  }

  async listAvailableYears() {
    await this.db.read();
    const documents = this.db.data.documents || [];
    
    // 1. 提取所有试卷中已存在的有效年份
    const yearSet = new Set();
    let hasNullYear = false;

    documents.forEach(doc => {
      if (doc.examYear !== undefined && doc.examYear !== null && String(doc.examYear).trim() !== '') {
        yearSet.add(String(doc.examYear).trim());
      } else {
        hasNullYear = true; // 存在未设定年份的试卷
      }
    });

    // 2. 将年份转为数组并进行降序排序（如 2026, 2025, 2024...）
    const sortedYears = Array.from(yearSet).sort((a, b) => b.localeCompare(a, undefined, { numeric: true }));

    // 3. 如果数据库里确实有未设定年份的试卷，或者为了让筛选框默认提供该选项，将“未设定”加入到列表中
    // 这里建议始终或者根据需要加上'未设定'
    sortedYears.push('未设定');

    return sortedYears;
  }

  async associateDocument(projectName, docId) {
    await this.db.read();
    const project = this.db.data.projects.find(p => p.name === projectName);
    const doc = this.db.data.documents.find(d => d.id === docId);
    if (!project || !doc) throw new Error('项目或文档不存在');

    const projSubject = project.subjectCode || '';
    const docSubject = doc.subjectCode || '';
    if (projSubject && docSubject && projSubject !== docSubject) {
      throw new Error(`学科代码不匹配（项目：${projSubject}，文档：${docSubject}），无法关联`);
    }

    const exists = (this.db.data.documentProjects || []).some(
      r => r.docId === docId && r.projectName === projectName
    );
    if (exists) throw new Error('该文件已关联到本项目');
    this.db.data.documentProjects.push({ docId, projectName });
    await this.db.write();
    return { success: true };
  }

  async disassociateDocument(projectName, docId) {
    await this.db.read();
    this.db.data.documentProjects = (this.db.data.documentProjects || []).filter(
      r => !(r.docId === docId && r.projectName === projectName)
    );
    await this.db.write();
    return { success: true };
  }

  async deleteDocument(docId) {
    await this.db.read();
    const docIndex = this.db.data.documents.findIndex(d => d.id === docId);
    if (docIndex === -1) throw new Error('文档不存在');

    const doc = this.db.data.documents[docIndex];

    // 级联删除本地备份文件
    if (doc.localFilePath && this.fileStorage) {
      try {
        await this.fileStorage.deleteFile(doc.localFilePath);
      } catch (err) {
        console.error(`删除本地备份文件失败: ${err.message}`);
      }
    }

    this.db.data.documents.splice(docIndex, 1);
    this.db.data.questions = this.db.data.questions.filter(q => q.docId !== docId);
    this.db.data.documentProjects = (this.db.data.documentProjects || []).filter(r => r.docId !== docId);

    for (const project of this.db.data.projects) {
      if (project.mainDocId === docId) {
        project.mainDocId = null;
      }
    }

    await this.db.write();
    return { success: true };
  }

  async getDocumentDetail(docId) {
    await this.db.read();
    const doc = this.db.data.documents.find(d => d.id === docId);
    if (!doc) throw new Error('文档不存在');
    const questions = this.db.data.questions
      .filter(q => q.docId === docId)
      .sort((a, b) => a.order - b.order)
      .map(q => ({
        id: q.id,
        title: q.title,
        indices: q.indices,
        order: q.order,
        tag1: q.tag1 || '',
        tag2: q.tag2 || '',
        tag3: q.tag3 || '',
        type: q.type || '',
        score: (q.score != null && !isNaN(q.score)) ? Number(q.score) : 0
      }));
    return {
      id: doc.id,
      name: doc.name,
      createTime: doc.createTime,
      status: doc.status,
      subjectCode: doc.subjectCode || '',
      parsed: doc.parsed || false,
      blocks: doc.blocks,
      questions,
      localFilePath: doc.localFilePath || null,
      examYear: doc.examYear || null,
      examCollege: doc.examCollege || null
    };
  }

  async updateDocument(docId, data) {
    await this.db.read();
    const doc = this.db.data.documents.find(d => d.id === docId);
    if (!doc) throw new Error('文档不存在');

    if (data.name !== undefined) doc.name = data.name;
    if (data.subjectCode !== undefined) doc.subjectCode = data.subjectCode;
    if (data.examYear !== undefined) doc.examYear = data.examYear;
    if (data.examCollege !== undefined) doc.examCollege = data.examCollege;

    if (data.parsed !== undefined) {
      doc.parsed = data.parsed;
    }

    if (data.blocks !== undefined && data.questions !== undefined) {
      doc.blocks = data.blocks;
      doc.status = 1;
      this.db.data.questions = this.db.data.questions.filter(q => q.docId !== docId);
      const newQuestions = data.questions.map((q, index) => ({
        id: Date.now() + index + 1,
        docId,
        title: q.title,
        indices: q.indices,
        order: index,
        tag1: q.tag1 ?? '',
        tag2: q.tag2 ?? '',
        tag3: q.tag3 ?? '',
        type: q.type ?? '',
        score: (q.score != null && !isNaN(q.score)) ? Number(q.score) : 0
      }));
      this.db.data.questions.push(...newQuestions);
    }

    await this.db.write();
    return { success: true };
  }

  async updateQuestionMeta(questionId, meta) {
    await this.db.read();
    const q = this.db.data.questions.find(q => q.id === questionId);
    if (!q) throw new Error('题目不存在');
    if (meta.tag1 !== undefined) q.tag1 = meta.tag1 ?? '';
    if (meta.tag2 !== undefined) q.tag2 = meta.tag2 ?? '';
    if (meta.tag3 !== undefined) q.tag3 = meta.tag3 ?? '';
    if (meta.type !== undefined) q.type = meta.type ?? '';
    if (meta.score !== undefined) {
      const val = Number(meta.score);
      q.score = isNaN(val) ? 0 : val;
    }
    await this.db.write();
    return { success: true };
  }

  async getProjectsByDocId(docId) {
    await this.db.read();
    const relations = (this.db.data.documentProjects || []).filter(r => r.docId === docId);
    const projectNames = relations.map(r => r.projectName);
    const projects = this.db.data.projects.filter(p => projectNames.includes(p.name));
    const reportsMap = new Map();
    if (this.db.data.reports) {
      for (const r of this.db.data.reports) {
        reportsMap.set(r.projectName, true);
      }
    }
    return projects.map(p => ({
      name: p.name,
      totalScore: p.totalScore,
      hasReport: reportsMap.has(p.name)
    }));
  }
}

// --- 4. 设置与 API 配置管理器 (SettingsManager) ---
class SettingsManager {
  constructor(dbInstance) { this.db = dbInstance; }

  getDefaultSettings() {
    return {
      active_api_id: null,
      ai_split_enabled: false,
      ai_report_enabled: false,
      ai_format_check_enabled: true,
      split_prompt: '',
      similarity_threshold: 50,
      format_checks: {
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
    };
  }

  async getSettings() {
    await this.db.read();
    let settings = this.db.data.settings;
    let changed = false;

    if (!settings) {
      settings = this.getDefaultSettings();
      this.db.data.settings = settings;
      changed = true;
    } else {
      const defaults = this.getDefaultSettings();
      for (const key in defaults) {
        if (settings[key] === undefined) {
          settings[key] = defaults[key];
          changed = true;
        }
      }
    }

    if (changed) {
      await this.db.write();
    }
    return settings;
  }

  async updateSetting(key, value) {
    await this.db.read();
    if (!this.db.data.settings) {
      this.db.data.settings = this.getDefaultSettings();
    }
    this.db.data.settings[key] = value;
    await this.db.write();
    return { success: true };
  }

  async listApiConfigs() {
    await this.db.read();
    return this.db.data.apiConfigs || [];
  }

  async addApiConfig(config) {
    await this.db.read();
    if (!this.db.data.apiConfigs) this.db.data.apiConfigs = [];
    const newId = Date.now();
    const newConfig = { id: newId, ...config };
    // 确保 is_local 字段存在且为布尔值，向后兼容旧配置
    newConfig.is_local = !!newConfig.is_local;
    this.db.data.apiConfigs.push(newConfig);
    await this.db.write();
    return newConfig;
  }

  async updateApiConfig(id, data) {
    await this.db.read();
    const configs = this.db.data.apiConfigs || [];
    const index = configs.findIndex(c => c.id === id);
    if (index === -1) throw new Error('API 配置不存在');
    // 如果包含 is_local，则规范化为布尔值
    if (data && data.hasOwnProperty('is_local')) {
      data.is_local = !!data.is_local;
    }
    Object.assign(configs[index], data);
    await this.db.write();
    return { success: true };
  }

  async deleteApiConfig(id) {
    await this.db.read();
    if (!this.db.data.apiConfigs) this.db.data.apiConfigs = [];
    const index = this.db.data.apiConfigs.findIndex(c => c.id === id);
    if (index === -1) throw new Error('API 配置不存在');
    this.db.data.apiConfigs.splice(index, 1);
    await this.db.write();
    return { success: true };
  }

  // 远程题库维护
  async listRemoteBanks() {
    await this.db.read();
    // 兼容旧数据：合并 protocol+address -> endpoint
    const raw = this.db.data.remoteBanks || [];
    return raw.map(b => {
      if ((b.endpoint === undefined || b.endpoint === null) && b.address) {
        const proto = b.protocol || 'http';
        b.endpoint = `${proto}://${b.address}`;
      }
      return b;
    });
  }

  async addRemoteBank(bank) {
    await this.db.read();
    if (!this.db.data.remoteBanks) this.db.data.remoteBanks = [];
    const newId = Date.now();
    const newBank = Object.assign({ id: newId, name: '', endpoint: 'http://127.0.0.1', port: 80, enabled: true, timeout: 5000 }, bank);
    this.db.data.remoteBanks.push(newBank);
    await this.db.write();
    return newBank;
  }

  async updateRemoteBank(id, data) {
    await this.db.read();
    if (!this.db.data.remoteBanks) this.db.data.remoteBanks = [];
    const idx = this.db.data.remoteBanks.findIndex(b => b.id === id);
    if (idx === -1) throw new Error('远程题库不存在');
    Object.assign(this.db.data.remoteBanks[idx], data);
    await this.db.write();
    return { success: true };
  }

  async deleteRemoteBank(id) {
    await this.db.read();
    if (!this.db.data.remoteBanks) this.db.data.remoteBanks = [];
    const idx = this.db.data.remoteBanks.findIndex(b => b.id === id);
    if (idx === -1) throw new Error('远程题库不存在');
    this.db.data.remoteBanks.splice(idx, 1);
    await this.db.write();
    return { success: true };
  }
}

// --- 5. 报告与题目相似度管理器 ---
class ReportManager {
  constructor(dbInstance) { this.db = dbInstance; }

  async saveOrUpdateReport(projectName, reportData = {}) {
    await this.db.read();
    if (!this.db.data.reports) this.db.data.reports = [];

    const existingIndex = this.db.data.reports.findIndex(r => r.projectName === projectName);
    const now = new Date().toISOString();

    if (existingIndex > -1) {
      this.db.data.reports[existingIndex] = {
        ...this.db.data.reports[existingIndex],
        ...reportData,
        projectName,
        updatedTime: now
      };
    } else {
      const newReport = {
        id: Date.now(),
        projectName,
        threshold: reportData.threshold ?? null,
        summary: reportData.summary ?? '',
        createdTime: now,
        updatedTime: now
      };
      this.db.data.reports.push(newReport);
    }

    await this.db.write();
    return { success: true };
  }

  async getFullReport(projectName) {
    await this.db.read();
    const report = (this.db.data.reports || []).find(r => r.projectName === projectName) || null;
    const similarityResults = (this.db.data.similarityResults || [])
      .filter(s => s.projectName === projectName)
      .sort((a, b) => a.id - b.id);
    return { report, similarityResults };
  }

  async deleteReport(projectName) {
    await this.db.read();
    if (!this.db.data.reports) this.db.data.reports = [];
    if (!this.db.data.similarityResults) this.db.data.similarityResults = [];

    const reportIndex = this.db.data.reports.findIndex(r => r.projectName === projectName);
    if (reportIndex === -1) throw new Error('报告不存在');

    this.db.data.reports.splice(reportIndex, 1);
    this.db.data.similarityResults = this.db.data.similarityResults.filter(
      s => s.projectName !== projectName
    );

    await this.db.write();
    return { success: true };
  }
}

class SimilarityManager {
  constructor(dbInstance) { this.db = dbInstance; }

  async addResult(projectName, data) {
    await this.db.read();
    if (!this.db.data.similarityResults) this.db.data.similarityResults = [];

    if (!projectName) throw new Error('项目名称不能为空');
    if (data.similarity == null) throw new Error('相似度分数不能为空');

    const newResult = {
      id: Date.now(),
      projectName,
      question1Id: data.question1Id ?? null,
      question2Id: data.question2Id ?? null,
      similarity: data.similarity,
      reason: data.reason ?? '',
      createdTime: new Date().toISOString()
    };
    this.db.data.similarityResults.push(newResult);
    await this.db.write();
    return { success: true, result: newResult };
  }

  async listByProject(projectName) {
    await this.db.read();
    const results = (this.db.data.similarityResults || [])
      .filter(s => s.projectName === projectName)
      .sort((a, b) => a.id - b.id);
    return results;
  }

  async deleteResult(resultId) {
    await this.db.read();
    if (!this.db.data.similarityResults) this.db.data.similarityResults = [];
    const index = this.db.data.similarityResults.findIndex(r => r.id === resultId);
    if (index === -1) {
      console.warn(`相似度记录 ${resultId} 不存在，可能已被删除`);
      return { success: true };
    }
    this.db.data.similarityResults.splice(index, 1);
    await this.db.write();
    return { success: true };
  }

  async deleteByProject(projectName) {
    await this.db.read();
    if (!this.db.data.similarityResults) this.db.data.similarityResults = [];
    const before = this.db.data.similarityResults.length;
    this.db.data.similarityResults = this.db.data.similarityResults.filter(r => r.projectName !== projectName);
    const after = this.db.data.similarityResults.length;
    console.log(`删除项目 ${projectName} 的相似度记录: ${before - after} 条`);
    await this.db.write();
    return { success: true };
  }
}

// --- 6. 格式校验结果管理器 (FormatCheckManager) ---
class FormatCheckManager {
  constructor(dbInstance) {
    this.db = dbInstance;
  }

  async saveBatch(docId, checks) {
    await this.db.read();
    if (!this.db.data.formatChecks) this.db.data.formatChecks = [];

    this.db.data.formatChecks = this.db.data.formatChecks.filter(c => c.docId !== docId);

    for (const check of checks) {
      this.db.data.formatChecks.push({
        docId,
        code: check.code,
        name: check.name,
        passed: check.passed,
        reason: check.reason || '',
        createdAt: new Date().toISOString()
      });
    }

    await this.db.write();
    return { success: true };
  }

  async getByDocId(docId) {
    await this.db.read();
    const results = (this.db.data.formatChecks || []).filter(c => c.docId === docId);
    return results;
  }
}

// ================== 用户管理器 (UserManager) ==================
class UserManager {
  constructor(dbInstance) {
    this.db = dbInstance;
  }

  async list() {
    await this.db.read();
    const users = this.db.data.users || [];
    return users.map(({ password, ...rest }) => rest);
  }

  async getByEmployeeId(employeeId) {
    await this.db.read();
    return (this.db.data.users || []).find(u => u.employeeId === employeeId) || null;
  }

  async getById(id) {
    await this.db.read();
    const user = (this.db.data.users || []).find(u => u.id === id);
    if (!user) return null;
    const { password, ...rest } = user;
    return rest;
  }

  async create(userData) {
    await this.db.read();
    const users = this.db.data.users || [];
    if (users.some(u => u.employeeId === userData.employeeId)) {
      throw new Error('工号已存在');
    }
    if (!userData.employeeId || !userData.password) {
      throw new Error('工号和密码不能为空');
    }
    const newId = Date.now();
    const newUser = {
      id: newId,
      employeeId: userData.employeeId,
      password: userData.password,
      role: userData.role ?? 3,
      fullName: userData.fullName || '',
      department: userData.department || '',
      createdAt: new Date().toISOString()
    };
    users.push(newUser);
    await this.db.write();
    const { password, ...result } = newUser;
    return result;
  }

  async update(id, updates) {
    await this.db.read();
    const users = this.db.data.users || [];
    const index = users.findIndex(u => u.id === id);
    if (index === -1) throw new Error('用户不存在');

    if (updates.employeeId !== undefined) delete updates.employeeId;
    if (updates.password !== undefined) {
      users[index].password = updates.password;
      delete updates.password;
    }
    const allowed = ['fullName', 'department', 'role'];
    for (const key of allowed) {
      if (updates[key] !== undefined) {
        users[index][key] = updates[key];
      }
    }
    await this.db.write();
    const { password, ...result } = users[index];
    return result;
  }

  async delete(id) {
    await this.db.read();
    const users = this.db.data.users || [];
    const userToDelete = users.find(u => u.id === id);
    if (!userToDelete) throw new Error('用户不存在');
    const superAdminCount = users.filter(u => u.role === 1).length;
    if (userToDelete.role === 1 && superAdminCount === 1) {
      throw new Error('不能删除最后一个超级管理员');
    }
    this.db.data.users = users.filter(u => u.id !== id);
    await this.db.write();
    return { success: true };
  }

  async authenticate(employeeId, password) {
    const user = await this.getByEmployeeId(employeeId);
    if (!user || user.password !== password) {
      return null;
    }
    const { password: _, ...safeUser } = user;
    return safeUser;
  }
}

// ================== 7. 学院管理器 (CollegeManager) ==================
class CollegeManager {
  constructor(dbInstance) {
    this.db = dbInstance;
  }

  async listAll() {
    await this.db.read();
    return this.db.data.colleges || [];
  }

  async search(keyword) {
    await this.db.read();
    const k = keyword.toLowerCase();
    return (this.db.data.colleges || []).filter(c =>
      c.name.toLowerCase().includes(k)
    );
  }

  async add(name) {
    await this.db.read();
    const colleges = this.db.data.colleges || [];
    if (colleges.some(c => c.name === name)) {
      throw new Error('学院名称已存在');
    }
    const newId = Date.now();
    const newCollege = { id: newId, name };
    colleges.push(newCollege);
    await this.db.write();
    return { success: true, college: newCollege };
  }

  async update(id, newName) {
    await this.db.read();
    const colleges = this.db.data.colleges || [];
    const index = colleges.findIndex(c => c.id === id);
    if (index === -1) throw new Error('学院不存在');
    if (colleges.some(c => c.name === newName && c.id !== id)) {
      throw new Error('新学院名称已存在');
    }
    colleges[index].name = newName;
    await this.db.write();
    return { success: true };
  }

  async delete(id) {
    await this.db.read();
    const colleges = this.db.data.colleges || [];
    const index = colleges.findIndex(c => c.id === id);
    if (index === -1) throw new Error('学院不存在');
    colleges.splice(index, 1);
    await this.db.write();
    return { success: true };
  }
}

// --- 主程序逻辑 ---
let mainWindow, db;
let courseManager, projectManager, documentManager, settingsManager;
let reportManager, similarityManager, formatCheckManager;
let userManager, collegeManager;
let fileStorage;

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000, height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, nodeIntegration: false
    }
  });
  mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL || `file://${path.join(__dirname, 'dist/index.html')}`);
}

app.on('ready', async () => {
  const { JSONFilePreset } = await import('lowdb/node');
  const appRoot = path.dirname(app.getPath('exe'));
  const dbPath = path.join(appRoot, 'db.json');

  const defaultData = {
    courses: [{ code: "808", name: "材料力学" }, { code: "408", name: "计算机学科基础" }],
    projects: [],
    documents: [],
    questions: [],
    documentProjects: [],
    settings: {},
    apiConfigs: [],
    reports: [],
    similarityResults: [],
    formatChecks: [],
    users: [],
    colleges: []
  };

  db = await JSONFilePreset(dbPath, defaultData);

  // 数据向后兼容与修补
  if (!db.data.documents) db.data.documents = [];
  if (!db.data.questions) db.data.questions = [];
  if (!db.data.documentProjects) {
    db.data.documentProjects = [];
    for (const doc of db.data.documents) {
      if (doc.projectName) {
        db.data.documentProjects.push({ docId: doc.id, projectName: doc.projectName });
      }
    }
    db.data.documents.forEach(doc => { delete doc.projectName; });
  }
  for (const doc of db.data.documents) {
    if (doc.subjectCode === undefined) doc.subjectCode = '';
    if (doc.parsed === undefined) doc.parsed = false;
    if (doc.localFilePath === undefined) doc.localFilePath = null;
    if (doc.examYear === undefined) doc.examYear = null;
    if (doc.examCollege === undefined) doc.examCollege = null;
  }
  for (const project of db.data.projects) {
    if (project.mainDocId === undefined) project.mainDocId = null;
    if (project.totalScore === undefined) project.totalScore = 0;
  }
  for (const q of db.data.questions) {
    if (q.tag1 === undefined) q.tag1 = '';
    if (q.tag2 === undefined) q.tag2 = '';
    if (q.tag3 === undefined) q.tag3 = '';
    if (q.type === undefined) q.type = '';
    if (q.score === undefined) q.score = 0;
  }
  if (!db.data.settings || Object.keys(db.data.settings).length === 0) {
    db.data.settings = new SettingsManager().getDefaultSettings();
  }
  if (!db.data.apiConfigs) db.data.apiConfigs = [];
  if (!db.data.reports) db.data.reports = [];
  if (!db.data.similarityResults) db.data.similarityResults = [];
  if (!db.data.formatChecks) db.data.formatChecks = [];

  if (!db.data.users) db.data.users = [];
  if (db.data.users.length === 0) {
    db.data.users.push({
      id: Date.now(),
      employeeId: 'admin',
      password: 'admin',
      role: 1,
      fullName: '超级管理员',
      department: '系统管理部',
      createdAt: new Date().toISOString()
    });
  }

  // 确保 colleges 存在
  if (!db.data.colleges) db.data.colleges = [];

  await db.write();

  // 初始化 FileStorageManager
  fileStorage = new FileStorageManager(appRoot);

  // 实例化所有 Manager
  courseManager = new CourseManager(db);
  projectManager = new ProjectManager(db);
  documentManager = new DocumentManager(db, fileStorage);
  settingsManager = new SettingsManager(db);
  reportManager = new ReportManager(db);
  similarityManager = new SimilarityManager(db);
  formatCheckManager = new FormatCheckManager(db);
  userManager = new UserManager(db);
  collegeManager = new CollegeManager(db);

  // ================== IPC 注册 ==================

  // 课程
  ipcMain.handle('course:search', (e, k) => courseManager.search(k));
  ipcMain.handle('course:add', (e, d) => courseManager.add(d.code, d.name));
  ipcMain.handle('course:listAll', () => courseManager.listAll());
  ipcMain.handle('course:update', (e, oldCode, newCode, newName) => courseManager.update(oldCode, newCode, newName));
  ipcMain.handle('course:delete', (e, code) => courseManager.delete(code));

  // 项目
  ipcMain.handle('project:getByName', (e, name) => projectManager.getByName(name));
  ipcMain.handle('project:save', (e, d) => projectManager.saveToDb(d));
  ipcMain.handle('project:list', () => projectManager.list());
  ipcMain.handle('project:delete', (e, name) => projectManager.deleteByName(name));
  ipcMain.handle('project:update', (e, oldName, data) => projectManager.updateByName(oldName, data));

  // 文档
  ipcMain.handle('document:save', (e, data) => documentManager.saveDocument(data));
  ipcMain.handle('document:listByProject', (e, projectName) => documentManager.listByProject(projectName));
  ipcMain.handle('document:listAll', () => documentManager.listAllDocuments());
  ipcMain.handle('document:associate', (e, projectName, docId) => documentManager.associateDocument(projectName, docId));
  ipcMain.handle('document:disassociate', (e, projectName, docId) => documentManager.disassociateDocument(projectName, docId));
  ipcMain.handle('document:delete', (e, docId) => documentManager.deleteDocument(docId));
  ipcMain.handle('document:getDetail', (e, docId) => documentManager.getDocumentDetail(docId));
  ipcMain.handle('document:update', (e, docId, data) => documentManager.updateDocument(docId, data));
  ipcMain.handle('document:getProjectsByDocId', (e, docId) => documentManager.getProjectsByDocId(docId));
  ipcMain.handle('document:listAvailableYears', () => documentManager.listAvailableYears());

  // 设置与 API 配置
  ipcMain.handle('settings:get', () => settingsManager.getSettings());
  ipcMain.handle('settings:update', (e, { key, value }) => settingsManager.updateSetting(key, value));
  ipcMain.handle('apiconfig:list', () => settingsManager.listApiConfigs());
  ipcMain.handle('apiconfig:add', (e, config) => settingsManager.addApiConfig(config));
  ipcMain.handle('apiconfig:update', (e, id, data) => settingsManager.updateApiConfig(id, data));
  ipcMain.handle('apiconfig:delete', (e, id) => settingsManager.deleteApiConfig(id));

  // 远程题库 IPC
  ipcMain.handle('remoteBanks:list', async () => await settingsManager.listRemoteBanks());
  ipcMain.handle('remoteBanks:add', async (e, bank) => await settingsManager.addRemoteBank(bank));
  ipcMain.handle('remoteBanks:update', async (e, id, data) => await settingsManager.updateRemoteBank(id, data));
  ipcMain.handle('remoteBanks:delete', async (e, id) => await settingsManager.deleteRemoteBank(id));

  ipcMain.handle('remoteBanks:test', async (e, bank) => {
    // bank.endpoint should be a URL string like https://example.com or http://host
    try {
      const timeout = (bank && bank.timeout) || 5000;
      let endpoint = (bank && bank.endpoint) || '';
      if (!endpoint) return { success: false, error: 'missing endpoint' };
      if (!/^https?:\/\//i.test(endpoint)) endpoint = 'http://' + endpoint;
      const u = new URL(endpoint);
      const protocol = u.protocol === 'https:' ? 'https' : 'http';
      const lib = protocol === 'https' ? require('https') : require('http');
      const options = {
        hostname: u.hostname,
        port: bank.port || (u.port ? Number(u.port) : (protocol === 'https' ? 443 : 80)),
        path: u.pathname || '/',
        method: 'GET',
        timeout: timeout,
        headers: {}
      };

      return await new Promise((resolve) => {
        const req = lib.request(options, (res) => {
          // 只要收到响应（包括404）就视为可达
          res.on('data', () => {});
          res.on('end', () => resolve({ success: true, statusCode: res.statusCode }));
        });
        req.on('timeout', () => { req.destroy(); resolve({ success: false, error: 'timeout' }); });
        req.on('error', (err) => resolve({ success: false, error: err.message }));
        req.end();
      });
    } catch (err) {
      return { success: false, error: err.message };
    }
  });

  // 从远程 MongoDB 查询 papers 列表
  ipcMain.handle('remoteBanks:fetchPapers', async (e, connection, queryOptions) => {
    try {
      // 如果未提供连接信息，则尝试从 settings 中获取常见的 mongodb 连接字符串
      let connStr = (connection && connection.connectionString) || null
      let endpoint = connection && connection.endpoint ? String(connection.endpoint) : null
      let port = connection && connection.port ? Number(connection.port) : null
      let dbName = (connection && connection.dbName && String(connection.dbName).trim()) || 'examSystem'

      if (!connStr && !endpoint) {
        // 读取 settings
        const settings = await settingsManager.getSettings();
        const candidates = [
          'mongo_connection', 'mongodb_connection', 'mongodb_uri', 'mongo_uri',
          'remote_db_connection', 'remote_db_uri', 'remote_db_url', 'remote_db_link',
          'db_connection', 'connection_string', 'exam_db_url'
        ];
        for (const k of candidates) {
          if (settings[k]) {
            connStr = String(settings[k]);
            break;
          }
        }
        // 兼容：settings 里也可能只存了 endpoint+port
        if (!connStr) {
          if (settings.remote_db_host) endpoint = settings.remote_db_host;
          if (settings.remote_db_port) port = Number(settings.remote_db_port);
        }
      }

      // 优先使用完整连接串；否则构建 mongodb://endpoint:port
      if (!connStr) {
        if (!endpoint) return { success: false, error: 'missing endpoint (no connection provided and none in settings)' };
        port = port || 27017;
        connStr = `mongodb://${endpoint.replace(/^https?:\/\//i, '')}:${port}`;
      }
      // 如果 connStr 并不包含 mongodb:// 前缀，尝试补全
      if (!/^mongodb(?:\+srv)?:\/\//i.test(connStr)) connStr = `mongodb://${connStr}`;
      // 强制使用 examSystem 数据库名（用户要求）
      dbName = 'examSystem'

      const { MongoClient } = require('mongodb');
      const client = new MongoClient(connStr, { serverSelectionTimeoutMS: 5000 });
      await client.connect();
      const db = client.db(dbName);
      const coll = db.collection('papers');

      const q = queryOptions || {};
      const filter = {};
      if (q.name) filter.name = { $regex: q.name, $options: 'i' };
      if (q.department) filter.department = { $regex: q.department, $options: 'i' };
      if (q.year) filter.year = q.year;
      if (q.code) filter.code = { $regex: q.code, $options: 'i' };
      if (q.paperId) filter.paperId = { $regex: q.paperId, $options: 'i' };

      const sortBy = q.sortBy || 'createdAt';
      const sortOrder = q.sortOrder === 'desc' ? -1 : 1;
      const limit = Math.min(500, Number(q.limit || 50));
      const skip = Number(q.skip || 0);

      const total = await coll.countDocuments(filter);
      const cursor = coll.find(filter).project({ _id: 0, paperId: 1, name: 1, score: 1, department: 1, year: 1, code: 1, createdAt: 1, updatedAt: 1 }).sort({ [sortBy]: sortOrder }).skip(skip).limit(limit);
      const papers = await cursor.toArray();
      await client.close();
      return { success: true, papers, total };
    } catch (err) {
      return { success: false, error: err.message };
    }
  });

  // 根据 paperId 从远程 MongoDB 的 questions 表中获取题目列表
  ipcMain.handle('remoteBanks:fetchQuestions', async (e, connection, paperId) => {
    try {
      let connStr = (connection && connection.connectionString) || null
      let endpoint = connection && connection.endpoint ? String(connection.endpoint) : null
      let port = connection && connection.port ? Number(connection.port) : null
      let dbName = (connection && connection.dbName && String(connection.dbName).trim()) || 'examSystem'

      if (!connStr && !endpoint) {
        const settings = await settingsManager.getSettings();
        const candidates = [
          'mongo_connection', 'mongodb_connection', 'mongodb_uri', 'mongo_uri',
          'remote_db_connection', 'remote_db_uri', 'remote_db_url', 'remote_db_link',
          'db_connection', 'connection_string', 'exam_db_url'
        ];
        for (const k of candidates) {
          if (settings[k]) {
            connStr = String(settings[k]);
            break;
          }
        }
        if (!connStr && settings.remote_db_host) endpoint = settings.remote_db_host;
        if (!connStr && settings.remote_db_port) port = Number(settings.remote_db_port);
      }

      if (!connStr) {
        if (!endpoint) throw new Error('missing endpoint (no connection provided and none in settings)');
        port = port || 27017;
        connStr = `mongodb://${endpoint.replace(/^https?:\/\//i, '')}:${port}`;
      }
      if (!/^mongodb(?:\+srv)?:\/\//i.test(connStr)) connStr = `mongodb://${connStr}`;
      dbName = 'examSystem';

      const { MongoClient } = require('mongodb');
      const client = new MongoClient(connStr, { serverSelectionTimeoutMS: 5000 });
      await client.connect();
      const db = client.db(dbName);
      const coll = db.collection('questions');

      // 查询该试卷的文档（注意：一个 paperId 对应一个文档）
      const doc = await coll.findOne({ paperId: paperId });
      await client.close();

      if (!doc) {
        return []; // 没有找到试卷题目数据
      }

      // 提取 questions 数组，并按 id 升序排序
      let questions = doc.questions || [];
      questions = questions.sort((a, b) => (a.id || 0) - (b.id || 0));

      // 返回精简字段（只保留前端需要的）
      return questions.map(q => ({
        id: q.id,
        type: q.type || '',
        richTextContent: q.richTextContent || '',
        score: q.score || 0
      }));
    } catch (err) {
      console.error('fetchQuestions error:', err);
      throw err;
    }
  });

  // 题目元数据更新
  ipcMain.handle('question:updateMeta', (e, questionId, meta) => documentManager.updateQuestionMeta(questionId, meta));

  // 报告和相似度
  ipcMain.handle('report:saveOrUpdate', (e, projectName, reportData) =>
    reportManager.saveOrUpdateReport(projectName, reportData)
  );
  ipcMain.handle('report:getFull', (e, projectName) =>
    reportManager.getFullReport(projectName)
  );
  ipcMain.handle('report:delete', (e, projectName) =>
    reportManager.deleteReport(projectName)
  );
  ipcMain.handle('similarity:add', (e, projectName, data) =>
    similarityManager.addResult(projectName, data)
  );
  ipcMain.handle('similarity:listByProject', (e, projectName) =>
    similarityManager.listByProject(projectName)
  );
  ipcMain.handle('similarity:delete', (e, resultId) =>
    similarityManager.deleteResult(resultId)
  );
  ipcMain.handle('similarity:deleteByProject', (e, projectName) =>
    similarityManager.deleteByProject(projectName)
  );

  // 格式校验结果
  ipcMain.handle('formatcheck:saveBatch', async (event, docId, checks) => {
    return await formatCheckManager.saveBatch(docId, checks);
  });
  ipcMain.handle('formatcheck:getByDocId', async (event, docId) => {
    return await formatCheckManager.getByDocId(docId);
  });

  // 文件备份
  ipcMain.handle('file:backup', async (event, sourcePath) => {
    try {
      const backupPath = await fileStorage.saveFile(sourcePath);
      return { success: true, backupPath };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // 打开本地文件
  ipcMain.handle('file:open', async (event, filePath) => {
    try {
      const result = await shell.openPath(filePath);
      if (result) throw new Error(result);
      return { success: true };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // 读取本地文件为 base64
  ipcMain.handle('file:read', async (event, filePath) => {
    try {
      const data = await fs.readFile(filePath);
      return { success: true, data: data.toString('base64') };
    } catch (error) {
      return { success: false, error: error.message };
    }
  });

  // 保存文件对话框和写入文件
  ipcMain.handle('dialog:showSaveDialog', async (event, options) => {
    const result = await dialog.showSaveDialog(mainWindow, options);
    return result;
  });
  ipcMain.handle('fs:writeFile', async (event, filePath, content) => {
    await fs.writeFile(filePath, content, 'utf8');
    return { success: true };
  });

  // 用户管理 IPC
  ipcMain.handle('user:list', async () => await userManager.list());
  ipcMain.handle('user:getById', async (event, id) => await userManager.getById(id));
  ipcMain.handle('user:create', async (event, userData) => await userManager.create(userData));
  ipcMain.handle('user:update', async (event, id, updates) => await userManager.update(id, updates));
  ipcMain.handle('user:delete', async (event, id) => await userManager.delete(id));
  ipcMain.handle('user:authenticate', async (event, employeeId, password) => 
    await userManager.authenticate(employeeId, password)
  );

  // ================== 学院管理 IPC ==================
  ipcMain.handle('college:listAll', async () => await collegeManager.listAll());
  ipcMain.handle('college:search', async (event, keyword) => await collegeManager.search(keyword));
  ipcMain.handle('college:add', async (event, name) => await collegeManager.add(name));
  ipcMain.handle('college:update', async (event, id, newName) => await collegeManager.update(id, newName));
  ipcMain.handle('college:delete', async (event, id) => await collegeManager.delete(id));

  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});