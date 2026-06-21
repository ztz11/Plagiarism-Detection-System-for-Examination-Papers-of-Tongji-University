import os
import shutil
import subprocess
import tempfile

import instructor
import re
import json
from typing import List, Optional, Dict, Any

from openai import OpenAI
from pydantic import BaseModel, Field

import fitz  # PyMuPDF

from schemas import (
    ExamMap, QuestionInfoResponse,
    TagSimilarityResult, SimilarityScoreResult, QuestionItem
)


# ---------- 格式校验的结构化模型 ----------
class FormatCheckResult(BaseModel):
    code: str = Field(..., description="校验项代码，如 SUBJECT_NAME_CORRECT_FILLED")
    name: str = Field(..., description="校验项名称")
    passed: bool = Field(..., description="是否通过校验")
    reason: str = Field(default="", description="未通过时的具体原因")


class FormatValidationOutput(BaseModel):
    results: List[FormatCheckResult] = Field(..., description="所有校验项的结果列表")

# ---------- 新增：本地文档解析 ----------
def _docx_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    """使用 LibreOffice 将 docx 字节流转为 pdf 字节流"""
    if not shutil.which("soffice"):
        raise RuntimeError("LibreOffice 未安装或不在 PATH 中")
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "input.docx")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmpdir, docx_path],
            check=True, capture_output=True, text=True
        )
        pdf_path = os.path.join(tmpdir, "input.pdf")
        with open(pdf_path, "rb") as f:
            return f.read()


def _extract_structured_text(pdf_bytes: bytes,
                             header_height: int = 70,
                             footer_bottom_margin: int = 70) -> str:
    """从 pdf 字节流提取每页的页眉、正文、页脚，拼成结构化文本"""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    total = doc.page_count
    for i, page in enumerate(doc):
        w, h = page.rect.width, page.rect.height
        header_rect = fitz.Rect(0, 0, w, header_height)
        body_rect = fitz.Rect(0, header_height, w, h - footer_bottom_margin)
        footer_rect = fitz.Rect(0, h - footer_bottom_margin, w, h)

        header = page.get_text("text", clip=header_rect).strip()
        body = page.get_text("text", clip=body_rect).strip()
        footer = page.get_text("text", clip=footer_rect).strip()

        parts = [f"=== 第 {i+1} 页 / 共 {total} 页 ==="]
        if header:
            parts.append(f"[页眉] {header}")
        if body:
            parts.append(f"[正文]\n{body}")
        if footer:
            parts.append(f"[页脚] {footer}")
        pages.append("\n".join(parts))
    doc.close()
    return "\n\n".join(pages)


# ---------- 新增：本地模式校验函数 ----------
def call_llm_for_format_validation_local(
        docx_bytes: bytes,
        enabled_checks: dict,
        api_key: str,
        base_url: str,
        model_name: str,
        expected_total_score: Optional[float] = None
) -> List[Dict[str, Any]]:
    """本地解析 docx 后直接发送文本给 LLM 进行格式校验"""
    text_prompt = build_format_validation_prompt(enabled_checks, expected_total_score)
    if text_prompt == "没有需要校验的格式项。":
        return []

    # 1. 本地解析 docx → 结构化文本
    try:
        pdf_bytes = _docx_to_pdf_bytes(docx_bytes)
        document_text = _extract_structured_text(pdf_bytes)
    except Exception as e:
        return _build_fallback_results(enabled_checks, f"本地文档解析失败: {str(e)}")

    # 2. 构建消息（不再使用 fileid）
    system_content = "你是一个试卷格式校验专家。请仔细阅读以下文档内容，并严格按照要求输出结构化的数据。"
    user_content = f"{text_prompt}\n\n文档内容：\n{document_text}"

    raw_client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)
    client = instructor.from_openai(raw_client)

    try:
        output: FormatValidationOutput = client.chat.completions.create(
            model=model_name,
            response_model=FormatValidationOutput,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content}
            ],
            temperature=0.0
        )
        raw_results = [item.dict() for item in output.results]

        # 3. 后处理（与原函数完全相同的逻辑，可抽取共用，这里为清晰直接复制）
        enabled_codes = {code for code, enabled in enabled_checks.items() if enabled}
        results_dict = {}
        for res in raw_results:
            code = res.get("code", "").strip()
            if code in enabled_codes:
                if code not in results_dict:
                    results_dict[code] = res

        # 补全缺失项
        standard_name_map = {
            "SUBJECT_NAME_CORRECT_FILLED": "科目名称是否正确填写",
            "SUBJECT_CODE_CORRECT_FILLED": "科目代码是否正确填写",
            "SUBJECT_NAME_AND_CODE_NOT_MATCH": "科目名称与代码是否匹配",
            "HEADER_SUBJECT_CODE_CORRECT_CONSISTENT": "每页的页眉科目代码是否正确填写且与首页一致",
            "PAGE_NUM_CORRECT_FILLED": "当前页脚的页码/总页码是否正确填写",
            "ALL_SECTIONS_MARKED_POINTS": "所有章节均标记分值",
            "SEQ_CORRECT_FILLED": "章节/题目的序号是否正确填写",
            "OPTIONS_NO_DUPLICATE": "所有选择题的选项编号和内容均无重复",
            "TOTAL_SCORE_IN_PREDETERMINED_RANGE": "总分在预设范围内"
        }
        for code in enabled_codes:
            if code not in results_dict:
                results_dict[code] = {
                    "code": code,
                    "name": standard_name_map.get(code, code),
                    "passed": False,
                    "reason": "LLM 未返回该项校验结果"
                }

        final_results = [results_dict[code] for code in enabled_codes if code in results_dict]
        return final_results

    except Exception as e:
        return _build_fallback_results(enabled_checks, f"LLM 调用失败: {str(e)}")


def build_format_validation_prompt(enabled_checks: dict, expected_total_score: Optional[float] = None) -> str:
    """
    构建格式校验的文本指令部分。
    如果 TOTAL_SCORE_IN_PREDETERMINED_RANGE 启用，则加入总分校验规则。
    重要：在输出格式中明确列出所有标准代码，要求 LLM 严格使用。
    """
    check_descriptions = {
        "SUBJECT_NAME_CORRECT_FILLED": {
            "name": "科目名称是否正确填写",
            "rule": "检查文档中是否明确写了科目名称。科目名称可以是“数学（一）”、“数学一”、“高等数学”、“大学物理”等形式，通常出现在试卷大标题中，如“2023年全国硕士研究生招生考试数学（一）”。只要出现类似“数学（一）”这样的标识，即认为科目名称正确。不要因为缺少“高等数学”等词而误判。"
        },
        "SUBJECT_CODE_CORRECT_FILLED": {
            "name": "科目代码是否正确填写",
            "rule": "检查文档中是否明确写了科目代码，例如“408”、“MATH101”等由字母或数字组成的代码。如果全文没有任何类似代码，判定为不通过。"
        },
        "SUBJECT_NAME_AND_CODE_NOT_MATCH": {
            "name": "科目名称与代码是否匹配",
            "rule": "只有当科目名称和科目代码都存在时，才判断它们是否匹配（例如“高等数学”对应“MATH101”）。如果科目名称缺失或科目代码缺失，该项直接判定为不通过。如果两者都存在但不匹配，也不通过。"
        },
        "HEADER_SUBJECT_CODE_CORRECT_CONSISTENT": {
            "name": "每页的页眉科目代码是否正确填写且与首页一致",
            "rule": "如果文档中根本没有填写科目代码，该项判定为不通过。如果存在科目代码，则检查每页页眉（或第一页的页眉）中的科目代码是否与文档开头（或首页）的科目代码完全一致。如果某页缺少页眉中的代码或代码不一致，判定为不通过。"
        },
        "PAGE_NUM_CORRECT_FILLED": {
            "name": "当前页脚的页码/总页码是否正确填写",
            "rule": "检查文档页码格式是否为“第X页，共Y页”或“X / Y”等形式，且数值合理（当前页码不超过总页码）。如果没有任何页码信息或格式错误，判定为不通过。"
        },
        "ALL_SECTIONS_MARKED_POINTS": {
            "name": "所有章节均标记分值",
            "rule": "检查每个章节（如“一、选择题”、“二、填空题”、“三、解答题”）是否都有明确的分值标注。分值标注常见形式包括：“每小题5分，共50分”、“共70分”等。请仔细识别以下模式：\n"
                    "- 选择题：“1～10小题，每小题5分，共50分”\n"
                    "- 填空题：“11～16小题，每小题5分，共30分”\n"
                    "- 解答题：“17～22小题，共70分”\n"
                    "只要每个章节有总分或每小题分的信息，即判定为通过。如果某个章节完全没有分数信息（例如只有标题“三、解答题”而没有“共70分”），判定为不通过。"
        },
        "SEQ_CORRECT_FILLED": {
            "name": "章节/题目的序号是否正确填写",
            "rule": "检查章节和题目的序号是否连续、无重复、无跳号，且序号格式统一。例如“一、选择题”之后应为“二、填空题”，再之后“三、解答题”。如果缺少中间章节（如只有一和三，没有二），判定为不通过。题目序号如（1）、（2）...应连续。"
        },
        "OPTIONS_NO_DUPLICATE": {
            "name": "所有选择题的选项编号和内容均无重复",
            "rule": "检查每个选择题的选项编号（A、B、C、D等）是否唯一，且选项内容（文字）没有重复。注意：必须基于文档中实际出现的内容，不要自行编造或引用文档中不存在的选项。如果你看到某个选择题的选项内容有重复（例如两个选项的文字完全相同），则判定为不通过。如果没有发现重复，判定为通过。"
        },
        "TOTAL_SCORE_IN_PREDETERMINED_RANGE": {
            "name": "总分在预设范围内",
            "rule": (
                "检查试卷所有题目分数总和是否等于预设总分。\n"
                "重要说明：\n"
                "1. **预设总分必须提供**：如果预设总分未提供（或为0、空值），此项直接判定为不通过，原因填写“预设总分未提供”。\n"
                "2. **选做题计分规则**：如果试卷中存在选做题（如“二选一”、“三选一”或明确标注选做），则统计总分时只计入其中一道题的最高得分（按试卷说明或默认取最大值），不能将多道选做题的分数重复累加。\n"
                "3. **统计方法**：逐题累加所有必做题分数；对于一组选做题（如题A、题B），只加一次（通常取最高分，或根据试卷说明选择）。\n"
                f"4. **预设总分**：{expected_total_score if expected_total_score is not None else '未提供'} 分。\n"
                "5. **通过条件**：预设总分有效且实际总分与预设总分相差不超过1分（允许四舍五入误差）。"
            )
        }
    }

    # 收集启用的校验项
    enabled_list = []
    for code, enabled in enabled_checks.items():
        if enabled and code in check_descriptions:
            enabled_list.append({
                "code": code,
                "name": check_descriptions[code]["name"],
                "rule": check_descriptions[code]["rule"]
            })

    if not enabled_list:
        return "没有需要校验的格式项。"

    rules_text = "\n".join([
        f"- **{item['name']}** (code: {item['code']})：{item['rule']}" for item in enabled_list
    ])

    # 构建输出示例，明确列出所有需要输出的 code
    example_results = []
    for item in enabled_list:
        example_results.append({
            "code": item["code"],
            "name": item["name"],
            "passed": True,
            "reason": "示例原因（若通过则留空）"
        })

    example_json = json.dumps({"results": example_results}, ensure_ascii=False, indent=2)

    prompt = f"""
你是一位专业的试卷格式校验专家。请根据以下规则对提供的试卷文档（PDF 格式）进行逐项检查。

**重要提示**：请严格依据文档中的实际内容进行判断，不要编造文档中不存在的信息。如果文档中有些内容因格式转换而丢失（例如某些章节标题或分值信息未显示），请基于你实际看到的内容作答。如果某一章分明应该存在但在文档中找不到，则判定为缺失。

## 需要检查的格式项及规则：
{rules_text}

## 输出要求：
请严格按照以下 JSON 结构返回结果，不要输出任何额外解释。**必须为上述所有启用的格式项都返回一个结果对象，且 code 字段必须使用上述括号中给出的精确代码（区分大小写）**。

示例输出（仅作格式参考，请根据实际判断填写）：
{example_json}

实际输出时，请根据文档内容判断每个项的 passed 和 reason。
"""
    return prompt


def _build_fallback_results(enabled_checks: dict, reason: str) -> List[Dict[str, Any]]:
    """降级处理：返回所有开启项为未通过，并给出原因"""
    check_names = {
        "SUBJECT_NAME_CORRECT_FILLED": "科目名称是否正确填写",
        "SUBJECT_CODE_CORRECT_FILLED": "科目代码是否正确填写",
        "SUBJECT_NAME_AND_CODE_NOT_MATCH": "科目名称与代码是否匹配",
        "HEADER_SUBJECT_CODE_CORRECT_CONSISTENT": "每页的页眉科目代码是否正确填写且与首页一致",
        "PAGE_NUM_CORRECT_FILLED": "当前页脚的页码/总页码是否正确填写",
        "ALL_SECTIONS_MARKED_POINTS": "所有章节均标记分值",
        "SEQ_CORRECT_FILLED": "章节/题目的序号是否正确填写",
        "OPTIONS_NO_DUPLICATE": "所有选择题的选项编号和内容均无重复",
        "TOTAL_SCORE_IN_PREDETERMINED_RANGE": "总分在预设范围内"
    }
    fallback = []
    for code, enabled in enabled_checks.items():
        if enabled and code in check_names:
            fallback.append({
                "code": code,
                "name": check_names[code],
                "passed": False,
                "reason": reason
            })
    return fallback


def call_llm_for_format_validation(
        file_bytes: bytes,
        filename: str,
        enabled_checks: dict,
        api_key: str,
        base_url: str,
        model_name: str,
        expected_total_score: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    直接将 PDF 文件上传到 LLM 服务端，并通过 fileid:// 协议引用。
    使用 instructor 保证结构化输出。
    expected_total_score: 预期的试卷总分，用于 TOTAL_SCORE_IN_PREDETERMINED_RANGE 校验。
    """
    print("=" * 60)
    print("📋 格式校验请求参数")
    print(f"  文件名: {filename}")
    print(f"  文件大小: {len(file_bytes)} 字节")
    print(f"  启用的校验项: {enabled_checks}")
    print(f"  期望总分: {expected_total_score}")
    print(f"  模型: {model_name}")
    print(f"  API Base URL: {base_url}")
    print("=" * 60)

    text_prompt = build_format_validation_prompt(enabled_checks, expected_total_score)
    if text_prompt == "没有需要校验的格式项。":
        print("⚠️ 没有需要校验的格式项，直接返回空结果")
        return []

    raw_client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)

    # 上传文件
    file_id = None
    try:
        print("📤 正在上传 PDF 文件到 LLM 服务端...")
        file_obj = (filename, file_bytes, "application/pdf")
        file_response = raw_client.files.create(
            file=file_obj,
            purpose="file-extract"
        )
        file_id = file_response.id
        print(f"✅ PDF 文件上传成功，File ID: {file_id}")
    except Exception as e:
        print(f"❌ 文件上传失败: {e}")
        return _build_fallback_results(enabled_checks, f"文件上传失败: {str(e)}")

    system_content = (
        f"你是一个试卷格式校验专家。用户上传了一个试卷文件（PDF 格式，File ID: fileid://{file_id})。"
        "请仔细阅读该文档内容，并严格按照要求输出结构化的数据。"
    )

    client = instructor.from_openai(raw_client)

    try:
        output: FormatValidationOutput = client.chat.completions.create(
            model=model_name,
            response_model=FormatValidationOutput,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": text_prompt}
            ],
            temperature=0.0
        )
        raw_results = [item.dict() for item in output.results]
        print(f"✅ LLM 调用成功，返回 {len(raw_results)} 条校验结果")

        # 获取启用的标准 code 集合
        enabled_codes = {code for code, enabled in enabled_checks.items() if enabled}

        # 构建结果字典（code -> result），只保留在 enabled_codes 中的项
        results_dict = {}
        for res in raw_results:
            code = res.get("code", "").strip()
            # 注意：这里不做任何映射，只做精确匹配（要求 LLM 返回精确 code）
            if code in enabled_codes:
                # 如果同一个 code 出现多次，保留第一个
                if code not in results_dict:
                    results_dict[code] = res
            else:
                print(f"  ⚠️ 忽略未知或未启用的 code: {code}")

        # 补全缺失的启用项（LLM 未返回的）
        missing_codes = enabled_codes - set(results_dict.keys())
        # 标准名称映射
        standard_name_map = {
            "SUBJECT_NAME_CORRECT_FILLED": "科目名称是否正确填写",
            "SUBJECT_CODE_CORRECT_FILLED": "科目代码是否正确填写",
            "SUBJECT_NAME_AND_CODE_NOT_MATCH": "科目名称与代码是否匹配",
            "HEADER_SUBJECT_CODE_CORRECT_CONSISTENT": "每页的页眉科目代码是否正确填写且与首页一致",
            "PAGE_NUM_CORRECT_FILLED": "当前页脚的页码/总页码是否正确填写",
            "ALL_SECTIONS_MARKED_POINTS": "所有章节均标记分值",
            "SEQ_CORRECT_FILLED": "章节/题目的序号是否正确填写",
            "OPTIONS_NO_DUPLICATE": "所有选择题的选项编号和内容均无重复",
            "TOTAL_SCORE_IN_PREDETERMINED_RANGE": "总分在预设范围内"
        }
        for code in missing_codes:
            results_dict[code] = {
                "code": code,
                "name": standard_name_map.get(code, code),
                "passed": False,
                "reason": "LLM 未返回该项校验结果"
            }
            print(f"  ➕ 补全缺失项: {code}")

        # 转换为列表，保持与前端传入顺序一致（可选）
        final_results = [results_dict[code] for code in enabled_codes if code in results_dict]

        # 打印最终结果
        print("--- 最终校验结果 ---")
        for res in final_results:
            print(f"  - {res['name']}: {'✅ 通过' if res['passed'] else '❌ 未通过'} {res['reason']}")
        print("=" * 60)
        return final_results

    except Exception as e:
        print(f"❌ LLM 调用失败: {e}")
        return _build_fallback_results(enabled_checks, f"LLM 调用失败: {str(e)}")
    finally:
        if file_id:
            try:
                raw_client.files.delete(file_id)
                print(f"🗑️ 已删除临时文件: {file_id}")
            except Exception as e:
                print(f"⚠️ 删除文件失败: {e}")


# ---------- 以下为原有函数（未修改） ----------
def get_online_segmentation(
        blocks: list,
        api_key: str,
        prompt: str,
        base_url: str,
        model_name: str
) -> ExamMap:
    clean_blocks = []
    for b in blocks:
        clean_blocks.append({
            "id": b["id"],
            "text": b.get("text", ""),
            "tag": b.get("tag", "normal")
        })
    blocks_json = json.dumps(clean_blocks, ensure_ascii=False, indent=2)

    system_msg = {"role": "system", "content": prompt}
    user_msg = {
        "role": "user",
        "content": (
            "请严格按照系统指令处理以下 blocks 数据（JSON 数组）：\n"
            f"{blocks_json}\n\n"
            "只输出系统指令要求的 JSON，不要添加任何解释。"
        )
    }

    client = instructor.from_openai(
        OpenAI(api_key=api_key, base_url=base_url, timeout=180.0, max_retries=2)
    )
    messages = [system_msg, user_msg]
    return client.chat.completions.create(
        model=model_name, response_model=ExamMap, messages=messages
    )


def extract_question_info(
        content: str,
        api_key: str,
        base_url: str,
        model_name: str,
        context_blocks: Optional[List[str]] = None
) -> QuestionInfoResponse:
    try:
        instruction = (
            "你是一位中学/大学试题分析专家，请严格按以下规则解析题目。\n\n"
            "### 核心要求\n"
            "**将整个题目视为一个整体进行分析，即使题目包含多个小题，也请输出该大题的整体信息，绝对不要拆分成子题。**\n\n"
            "### 题型推断规则（重要）\n"
            "请根据题目的**语义结构和作答要求**判断题型，而不是依赖简单的符号（如下划线、括号）。\n"
            "常见的题型包括：\n"
            "- 选择题：题目中明确列出选项（如 A. B. C. D.）或包含“选择”、“单选”、“多选”等字眼。\n"
            "- 填空题：题目要求填写缺失的内容，通常有“填空”、“填写”、“填入”等提示词，或题干中有明确的空缺位置（如“______”）。**注意**：公式中的下划线或括号不代表填空。\n"
            "- 计算题/解答题：题目要求计算、证明、求解、回答等，且没有给出选项，也没有明显的填空位置。\n"
            "- 判断题：题目要求判断陈述的真假。\n"
            "- 简答题：题目要求简要回答。\n"
            "- 其他：如匹配题、排序题等。\n\n"
            "**如果仅凭题目正文无法确定题型（例如没有明确选项、没有填空提示、也没有明确的计算要求），请输出“未知”。**\n"
            "不要随意猜测，尤其是不要把没有选项的题目误判为选择题。\n\n"
            "### 分数推断规则（重要）\n"
            "1. **优先从题目正文中提取分数**，如“（5分）”、“每小题5分”。\n"
            "2. **如果题目正文中无法找到分数，则从提供的“上下文文本”中寻找**：上下文文本可能包含大题标题（如“一、选择题：1～10小题，每小题5分，共50分”）。\n"
            "   - 请根据当前题目在试卷中的位置（题号）推断其所属的大题，并提取该大题的“每小题分”作为本题分数。\n"
            "3. 若仍无法确定，则输出0。\n\n"
            "### 标签规则\n"
            "提取3个最直接的**专业知识考点**（非主题/章节）。\n"
            "   - ✅ 正确示例：能量守恒、导数定义、CSS盒模型、双宾语结构\n"
            "   - ❌ 错误示例：物理、高等数学、web前端、英语语法\n"
            "   - 若不足3个，用“其他考点”填充。\n\n"
            "### 输出格式\n"
            "必须输出一个纯净的 JSON 对象，键名严格使用中文：\n"
            "{\n"
            '  "题型": "填空题",\n'
            '  "分数": 5,\n'
            '  "标签1": "导数",\n'
            '  "标签2": "极限",\n'
            '  "标签3": "连续性"\n'
            "}\n\n"
            f"### 待解析题目\n{content}\n\n"
        )
        if context_blocks:
            context_text = "\n\n".join(context_blocks)
            instruction += f"### 上下文文本（供分数推断参考）\n{context_text}\n\n"

        client = instructor.from_openai(
            OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=2)
        )
        messages = [
            {"role": "system", "content": "你是一个严谨的题目分析专家，只输出纯净的 JSON 数据，不要任何额外文字。"},
            {"role": "user", "content": instruction}
        ]
        info = client.chat.completions.create(
            model=model_name, response_model=QuestionInfoResponse, messages=messages
        )

        if info.score == 0.0:
            scores = re.findall(r'[（(]?\s*(\d+(?:\.\d+)?)\s*分\s*[）)]?', content)
            if scores:
                info.score = sum(float(s) for s in scores)
            else:
                per_scores = re.findall(r'每\s*(?:小题|题|问)\s*(\d+(?:\.\d+)?)\s*分', content)
                if per_scores:
                    info.score = float(per_scores[0])
                else:
                    num_match = re.search(r'(\d+(?:\.\d+)?)\s*分', content)
                    if num_match:
                        info.score = float(num_match.group(1))
        return info

    except Exception as e:
        print(f"[extract_question_info] 发生异常: {type(e).__name__}: {e}")
        return QuestionInfoResponse(
            question_type="未知",
            score=0.0,
            tag1="其他考点",
            tag2="其他考点",
            tag3="其他考点"
        )


def check_tags_similarity(
        tags1: list[str],
        tags2: list[str],
        api_key: str,
        base_url: str,
        model_name: str
) -> bool:
    if not tags1 or not tags2:
        return True

    system_msg = "你是一个标签相似度判断工具，只输出纯净的 JSON，不要添加任何解释。"
    user_msg = (
        f"请判断以下两个标签集合中，是否存在至少一对标签在语义上相同或高度相似。\n\n"
        f"集合A：{tags1}\n"
        f"集合B：{tags2}\n\n"
        "判定规则：\n"
        "- 语义相同或核心考点一致即为相似（如“导数”与“微分”、“能量守恒”与“能量守恒定律”）。\n"
        "- 忽略大小写、空格、标点差异。\n"
        "- 如果存在任意一对相似标签，请回答 true，否则回答 false。\n\n"
        "输出格式（严格 JSON）：\n"
        '{"有相似标签": true/false}'
    )

    client = instructor.from_openai(
        OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=1)
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]
    result = client.chat.completions.create(
        model=model_name, response_model=TagSimilarityResult, messages=messages, temperature=0.0
    )
    return result.has_similar


def compute_question_similarity(
        q1: QuestionItem,
        q2: QuestionItem,
        api_key: str,
        base_url: str,
        model_name: str,
        reason_threshold: float = 60.0
) -> tuple[int, str]:
    system_msg = (
        "你是一位教育内容分析专家。请分析两道题目是否语义重复，"
        "即是否考查相同的知识点和解题方法，即使题面、数值、情境做了修改。"
        "只输出纯净的 JSON，不要任何额外说明。"
    )

    user_msg = (
        f"题目1信息：\n"
        f"- 题型：{q1.type}\n"
        f"- 标签：{q1.tags}\n"
        f"- 正文：\n{q1.body}\n\n"
        f"题目2信息：\n"
        f"- 题型：{q2.type}\n"
        f"- 标签：{q2.tags}\n"
        f"- 正文：\n{q2.body}\n\n"
        "请从以下维度比较：\n"
        "1. 考查的核心知识点是否一致\n"
        "2. 解题思路和关键步骤是否相同\n"
        "3. 是否存在仅表面修改（换数字、换名称、换情境等）\n\n"
        "给出0-100的相似度分数：0表示完全不同，100表示完全相同或仅有极细微修改。\n"
        f"如果相似度≥{reason_threshold}，请用简洁中文说明重复原因（例如：“考查相同二次函数最值，仅将商品利润问题改为矩形面积”）；"
        f"若相似度<{reason_threshold}，原因字段留空字符串。\n\n"
        "输出格式（严格 JSON）：\n"
        '{"相似度": 整数, "原因": "字符串"}'
    )

    client = instructor.from_openai(
        OpenAI(api_key=api_key, base_url=base_url, timeout=120.0, max_retries=1)
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]
    result = client.chat.completions.create(
        model=model_name, response_model=SimilarityScoreResult, messages=messages, temperature=0.0
    )
    return result.similarity, result.reason