"""
schemas.py - Pydantic 数据模型定义

本模块定义了整个后端服务中使用的所有请求/响应数据结构，
包括试卷切分、题目信息提取、相似度检测、格式校验和报告生成。
所有 LLM 结构化输出均通过 Pydantic 模型与 instructor 库协作完成。
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re

# ==================== 试卷切分模型 ====================
class QuestionGroup(BaseModel):
    """试卷中的一道题目，包含其在文档中的切分位置信息"""
    id: int
    title: str
    indices: List[int]              # 该题包含的 block ID 列表
    start_index: int                # 起始 block 序号
    end_index: int                  # 结束 block 序号

class ExamMap(BaseModel):
    """整张试卷的切分结果"""
    questions: List[QuestionGroup]

class AppConfig(BaseModel):
    """LLM 服务配置（base_url / model_name / api_key）"""
    base_url: str = ""
    model_name: str = ""
    api_key: str = ""

    def is_online_ready(self) -> bool:
        """检查三项配置是否均已填写（可发起在线 LLM 调用）"""
        return all([self.base_url.strip(), self.model_name.strip(), self.api_key.strip()])

class QuestionInfoResponse(BaseModel):
    """LLM 对单道题目的解析结果（题型、分值、3 个知识标签）"""
    question_type: str = Field(alias="题型", description="题目类型")
    score: float = Field(default=0.0, alias="分数", description="题目分值数字，若无明确分值则输出0")
    tag1: str = Field(alias="标签1", description="具体考点1（如：牛顿第二定律）")
    tag2: str = Field(alias="标签2", description="具体考点2（如：勾股定理）")
    tag3: str = Field(alias="标签3", description="具体考点3（如：反向传播算法）")

    @field_validator('score', mode='before')
    @classmethod
    def coerce_score(cls, v):
        """容错处理：如果 LLM 返回字符串格式的分数（如"5分"），自动提取数字"""
        if isinstance(v, str):
            num = re.search(r'\d+(\.\d+)?', v)
            if num:
                return float(num.group())
            return 0.0
        return v

# ==================== 相似度检测模型 ====================
class QuestionItem(BaseModel):
    """前端传入的单道题目信息（用于相似度比较请求）"""
    body: str = Field(..., description="题目正文")
    type: str = Field(..., description="题型")
    tags: List[str] = Field(default_factory=list, description="标签列表")

class SimilarityRequest(BaseModel):
    """相似度检测请求"""
    question1: QuestionItem
    question2: QuestionItem
    threshold: float = Field(default=80, ge=0, le=100, description="重复度阈值(0-100)")

class SimilarityResponse(BaseModel):
    """相似度检测响应"""
    is_duplicate: bool
    similarity: float = 0.0
    reason: Optional[str] = None
    tag_check_passed: bool = False          # LLM 模式：标签初筛是否通过

class TagSimilarityResult(BaseModel):
    """LLM 标签相似度判断的结构化输出"""
    has_similar: bool = Field(alias="有相似标签", description="是否存在至少一对语义相似的标签")

class SimilarityScoreResult(BaseModel):
    """LLM 内容相似度评分的结构化输出"""
    similarity: int = Field(alias="相似度", description="0-100的整数，表示重复程度")
    reason: str = Field(alias="原因", description="重复原因说明（相似度≥阈值时详细说明）")

# ==================== 格式校验模型 ====================
class FormatCheckItemResult(BaseModel):
    """单个格式校验项的结果"""
    code: str = Field(..., description="校验项代码，如 SUBJECT_NAME_CORRECT_FILLED")
    name: str = Field(..., description="校验项名称（便于展示）")
    passed: bool = Field(..., description="是否通过校验")
    reason: Optional[str] = Field(None, description="未通过时的具体原因说明")

class FormatValidationResponse(BaseModel):
    """格式校验接口的返回结构"""
    results: List[FormatCheckItemResult] = Field(..., description="所有开启项的校验结果列表")
    summary: str = Field(..., description="总体结论，如“通过 7 项，未通过 2 项”")

class SelectiveQuestionResult(BaseModel):
    """选做题判断结果（用于总分校验时去重计算）"""
    is_selective: bool = Field(..., description="是否为选做题")
    part: Optional[int] = Field(None, description="选做题分区编号（1,2,3...），若不是选做题则为 None")

# ==================== 报告生成模型 ====================
class FormatCheckItemInput(BaseModel):
    """格式校验输入项（用于生成报告）"""
    item: str = Field(..., description="格式条目名称")
    passed: bool = Field(..., description="是否通过")
    reason: str = Field(default="", description="原因说明")

class DuplicateResultInput(BaseModel):
    """重复度校验输入项（用于生成报告）"""
    block_ids: List[int] = Field(..., description="原文位置的block ID列表（来自原切分）")
    similarity: float = Field(..., description="相似度（0-100）")
    duplicate_location: str = Field(..., description="重复内容位置描述")
    reason: str = Field(..., description="重复原因")

class ReportGenerateRequest(BaseModel):
    """生成报告请求模型"""
    docx_file_path: str = Field(..., description="原始 DOCX 文件路径")
    format_checks: List[FormatCheckItemInput] = Field(default_factory=list, description="格式校验结果列表")
    duplicate_results: List[DuplicateResultInput] = Field(default_factory=list, description="重复度校验结果列表")
    save_path: str = Field(..., description="生成的报告保存路径（.docx）")