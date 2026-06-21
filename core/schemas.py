from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import re

# ---------- 原有模型 ----------
class QuestionGroup(BaseModel):
    id: int
    title: str
    indices: List[int]
    start_index: int
    end_index: int

class ExamMap(BaseModel):
    questions: List[QuestionGroup]

class AppConfig(BaseModel):
    base_url: str = ""
    model_name: str = ""
    api_key: str = ""

    def is_online_ready(self) -> bool:
        return all([self.base_url.strip(), self.model_name.strip(), self.api_key.strip()])

class QuestionInfoResponse(BaseModel):
    question_type: str = Field(alias="题型", description="题目类型")
    score: float = Field(default=0.0, alias="分数", description="题目分值数字，若无明确分值则输出0")
    tag1: str = Field(alias="标签1", description="具体考点1（如：牛顿第二定律）")
    tag2: str = Field(alias="标签2", description="具体考点2（如：勾股定理）")
    tag3: str = Field(alias="标签3", description="具体考点3（如：反向传播算法）")

    @field_validator('score', mode='before')
    @classmethod
    def coerce_score(cls, v):
        if isinstance(v, str):
            num = re.search(r'\d+(\.\d+)?', v)
            if num:
                return float(num.group())
            return 0.0
        return v

# ---------- 相似度相关模型 ----------
class QuestionItem(BaseModel):
    """前端传入的单道题目信息"""
    body: str = Field(..., description="题目正文")
    type: str = Field(..., description="题型")
    tags: List[str] = Field(default_factory=list, description="标签列表")

class SimilarityRequest(BaseModel):
    question1: QuestionItem
    question2: QuestionItem
    threshold: float = Field(default=80, ge=0, le=100, description="重复度阈值(0-100)")

class SimilarityResponse(BaseModel):
    is_duplicate: bool
    similarity: float = 0.0
    reason: Optional[str] = None
    tag_check_passed: bool = False

class TagSimilarityResult(BaseModel):
    has_similar: bool = Field(alias="有相似标签", description="是否存在至少一对语义相似的标签")

class SimilarityScoreResult(BaseModel):
    similarity: int = Field(alias="相似度", description="0-100的整数，表示重复程度")
    reason: str = Field(alias="原因", description="重复原因说明（相似度≥阈值时详细说明）")

# ---------- 格式校验相关模型 ----------
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
    is_selective: bool = Field(..., description="是否为选做题")
    part: Optional[int] = Field(None, description="选做题分区编号（1,2,3...），若不是选做题则为 None")

# ---------- 新增：报告生成相关模型 ----------
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