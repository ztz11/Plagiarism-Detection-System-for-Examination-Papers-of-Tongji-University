import asyncio
import difflib
import glob
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import sys
from contextlib import asynccontextmanager
from io import BytesIO
from typing import Optional, List, Dict, Any, Tuple, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
import pypandoc
from docx import Document
from docx.oxml import OxmlElement
from docx.shared import RGBColor
from docx.text.paragraph import Paragraph
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from docx.oxml.ns import qn

from llm_service import (
    get_online_segmentation, extract_question_info,
    check_tags_similarity, compute_question_similarity,
    call_llm_for_format_validation,
    call_llm_for_format_validation_local
)
from ocr_module import LocalOCREngine
from schemas import (
    ExamMap, AppConfig, SimilarityRequest, SimilarityResponse,
    FormatValidationResponse, FormatCheckItemResult,
    ReportGenerateRequest
)


# ==================== 本地 NLP 相似度计算（基于 sentence-transformers） ====================
_NLP_MODEL: Optional[SentenceTransformer] = None


def _get_nlp_model() -> SentenceTransformer:
    """单例模式加载多语言句子相似度模型（本地优先，否则在线下载）"""
    global _NLP_MODEL
    if _NLP_MODEL is not None:
        return _NLP_MODEL

    # 尝试从本地指定路径加载（与 compare.py 中一致）
    base_dir = "./distiluse-base-multilingual-cased-v1"
    official_name = "sentence-transformers/distiluse-base-multilingual-cased-v1"
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    # 自动寻找本地模型
    local_path = None
    if os.path.isdir(base_dir):
        if os.path.exists(os.path.join(base_dir, "config.json")):
            local_path = base_dir
        else:
            snapshots_dir = os.path.join(base_dir, "snapshots")
            if os.path.isdir(snapshots_dir):
                snapshots = [d for d in os.listdir(snapshots_dir)
                             if os.path.isdir(os.path.join(snapshots_dir, d))]
                if snapshots:
                    local_path = os.path.join(snapshots_dir, snapshots[0])

    if local_path:
        print(f"从本地加载 NLP 模型: {local_path}")
        try:
            _NLP_MODEL = SentenceTransformer(local_path, device=device)
            print("本地 NLP 模型加载成功")
            return _NLP_MODEL
        except Exception as e:
            print(f"本地加载失败: {e}")

    print("尝试从 HuggingFace 在线下载 NLP 模型...")
    _NLP_MODEL = SentenceTransformer(official_name, device=device)
    print("在线 NLP 模型加载成功")
    return _NLP_MODEL


def _clean_text(text: str) -> str:
    """去除多余空白，用于相似度比较"""
    if not isinstance(text, str):
        text = str(text)
    # 移除 HTML 标签（如果有）
    cleaned = re.sub(r'<[^>]+>', '', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def compute_local_similarity(text1: str, text2: str) -> float:
    """
    使用本地多语言 sentence-transformers 模型计算两个文本的余弦相似度 (0~1)
    """
    model = _get_nlp_model()
    clean1 = _clean_text(text1)
    clean2 = _clean_text(text2)
    emb1 = model.encode([clean1], convert_to_numpy=True)[0]
    emb2 = model.encode([clean2], convert_to_numpy=True)[0]
    dot = np.dot(emb1, emb2)
    norm1 = np.linalg.norm(emb1)
    norm2 = np.linalg.norm(emb2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return float(dot / (norm1 * norm2))


# ==================== LibreOffice 便携版专用路径 ====================
def get_soffice_path() -> str:
    """
    获取 LibreOffice 可执行文件路径（仅使用同目录下的便携版）。
    若找不到则抛出 RuntimeError。
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    portable_root = os.path.join(script_dir, "LibreOfficePortable")

    if sys.platform == "win32":
        candidates = [
            os.path.join(portable_root, "App", "libreoffice", "program", "soffice.exe"),
            os.path.join(portable_root, "LibreOfficePortable.exe"),
        ]
    else:
        candidates = [
            os.path.join(portable_root, "App", "libreoffice", "program", "soffice"),
            os.path.join(portable_root, "libreoffice", "program", "soffice"),
        ]

    for cand in candidates:
        if os.path.isfile(cand):
            return cand

    raise RuntimeError(
        f"未找到 LibreOffice 便携版，请确保目录存在且结构正确：{portable_root}\n"
        "期望路径例如：LibreOfficePortable/App/libreoffice/program/soffice.exe"
    )


_SOFFICE_PATH: Optional[str] = None


def get_soffice_path_cached() -> str:
    global _SOFFICE_PATH
    if _SOFFICE_PATH is None:
        _SOFFICE_PATH = get_soffice_path()
    return _SOFFICE_PATH


# ==================== 应用生命周期 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global ocr_engine

    try:
        ocr_engine = LocalOCREngine()
    except Exception:
        ocr_engine = None

    # 预加载本地 NLP 模型（可选，避免首次请求延迟）
    try:
        _get_nlp_model()
    except Exception:
        pass

    app.state.config = AppConfig()
    app.state.last_exam_map = None
    app.state.last_blocks = None
    yield
    if ocr_engine:
        try:
            ocr_engine.unload()
        except:
            pass


app = FastAPI(title="Exam Boundary Parser", lifespan=lifespan)
ocr_engine: Optional[LocalOCREngine] = None


# ==================== 异步 OCR 替换函数 ====================
async def convert_image_blob_to_png(blob: bytes, cache_dir: Optional[str] = None) -> bytes:
    soffice_path = get_soffice_path_cached()

    if cache_dir is None:
        cache_dir = os.path.join(tempfile.gettempdir(), "ocr_img_cache")
    os.makedirs(cache_dir, exist_ok=True)

    blob_hash = hashlib.md5(blob).hexdigest()
    cached_png_path = os.path.join(cache_dir, f"{blob_hash}.png")
    if os.path.exists(cached_png_path):
        with open(cached_png_path, "rb") as f:
            return f.read()

    if blob.startswith(b'\xd7\xcd\xc6\x9a'):
        ext = ".wmf"
    elif blob.startswith(b'\x01\x00\x00\x00'):
        ext = ".emf"
    elif blob.startswith(b'\xff\xd8'):
        ext = ".jpg"
    elif blob.startswith(b'\x89PNG'):
        ext = ".png"
    elif blob.startswith(b'GIF8'):
        ext = ".gif"
    else:
        ext = ".bin"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_in_path = os.path.join(tmpdir, f"input{ext}")
        with open(tmp_in_path, "wb") as f:
            f.write(blob)

        out_dir = os.path.join(tmpdir, "output")
        os.makedirs(out_dir, exist_ok=True)

        cmd = [
            soffice_path, "--headless", "--convert-to", "png",
            "--outdir", out_dir, tmp_in_path
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"LibreOffice 转换失败 (code {proc.returncode}): {error_msg}")

        base_name = os.path.splitext(os.path.basename(tmp_in_path))[0]
        png_path = os.path.join(out_dir, f"{base_name}.png")
        if not os.path.exists(png_path):
            files = glob.glob(os.path.join(out_dir, "*.png"))
            if not files:
                raise FileNotFoundError(f"未找到转换后的 PNG 文件，输出目录: {out_dir}")
            png_path = files[0]

        with open(png_path, "rb") as f:
            png_bytes = f.read()
        with open(cached_png_path, "wb") as f:
            f.write(png_bytes)
        return png_bytes


async def replace_images_with_ocr_async(docx_bytes: bytes, markdown_text: str, ocr_engine: LocalOCREngine) -> str:
    doc = Document(BytesIO(docx_bytes))
    image_map: Dict[str, bytes] = {}
    for rel in doc.part.rels.values():
        if "image" in rel.target_ref:
            image_map[rel.target_ref] = rel.target_part.blob

    pattern = re.compile(r'!\[.*?\]\((.*?)\)')
    matches = list(pattern.finditer(markdown_text))
    if not matches:
        return markdown_text

    async def recognize_image(blob: bytes, img_path: str) -> str:
        try:
            png_bytes = await convert_image_blob_to_png(blob)
            try:
                text = await ocr_engine.recognize(png_bytes)
            except Exception:
                return ""
            return text.strip()
        except Exception:
            return ""

    tasks = []
    for match in matches:
        img_path = match.group(1)
        blob = image_map.get(img_path)
        if blob is None:
            base_name = os.path.basename(img_path)
            for ref, b in image_map.items():
                if ref.endswith(base_name) or base_name in ref:
                    blob = b
                    break
        if blob is None:
            tasks.append(asyncio.sleep(0, result=""))
        else:
            tasks.append(recognize_image(blob, img_path))

    ocr_results = await asyncio.gather(*tasks)

    result_chars = list(markdown_text)
    for (match, ocr_text) in zip(reversed(matches), reversed(ocr_results)):
        start, end = match.start(), match.end()
        if ocr_text:
            replacement = f" {ocr_text} "
        else:
            replacement = match.group(0)
        result_chars[start:end] = replacement
    new_markdown = ''.join(result_chars)
    return new_markdown


# ==================== 文档转换辅助函数 ====================
def convert_docx_to_markdown(docx_bytes: bytes) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_in_path = os.path.join(tmpdir, "input.docx")
        with open(tmp_in_path, "wb") as f:
            f.write(docx_bytes)

        output = pypandoc.convert_file(
            tmp_in_path,
            'markdown+tex_math_dollars+raw_tex',
            format='docx',
            extra_args=['--wrap=none']
        )
        return output


def convert_docx_to_pdf(docx_bytes: bytes) -> bytes:
    soffice_path = get_soffice_path_cached()
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "input.docx")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        cmd = [
            soffice_path, "--headless", "--convert-to", "pdf",
            "--outdir", tmpdir, docx_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice 转换失败: {result.stderr}")

        pdf_path = os.path.join(tmpdir, "input.pdf")
        if not os.path.exists(pdf_path):
            raise RuntimeError("转换后未找到 PDF 文件")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        return pdf_bytes


def split_markdown_into_blocks(markdown_text: str) -> List[Dict[str, Any]]:
    lines = markdown_text.split('\n')
    blocks: List[Dict[str, Any]] = []
    current_lines: List[str] = []
    block_id = 0

    def flush_block() -> None:
        nonlocal block_id
        if not current_lines:
            return
        text = '\n'.join(current_lines).strip()
        if text:
            tag = 'math' if text.startswith('$$') and text.endswith('$$') and len(text.split('\n')) == 1 else 'normal'
            blocks.append({
                "id": block_id,
                "text": text,
                "tag": tag,
                "image": None,
                "mime": None
            })
            block_id += 1
        current_lines.clear()

    for line in lines:
        if line.strip() == '':
            flush_block()
        else:
            current_lines.append(line)
    flush_block()
    return blocks


def get_blocks_from_docx(docx_path: str) -> List[Dict[str, Any]]:
    with open(docx_path, "rb") as f:
        docx_bytes = f.read()
    markdown_text = convert_docx_to_markdown(docx_bytes)
    blocks = split_markdown_into_blocks(markdown_text)
    return blocks


# ==================== API 端点 ====================
@app.post("/set-config")
async def set_config(
        request: Request,
        base_url: str = Form(...),
        model_name: str = Form(...),
        api_key: str = Form(...)
) -> Dict[str, Any]:
    config: AppConfig = request.app.state.config
    config.base_url = base_url.strip()
    config.model_name = model_name.strip()
    config.api_key = api_key.strip()
    return {"status": "success", "data": config.model_dump()}


@app.post("/analyze-exam")
async def analyze_exam(
        request: Request,
        file: UploadFile = File(...),
        api_type: str = Form(default="online"),
        prompt: str = Form(default="")
) -> Dict[str, Any]:
    if not file.filename.endswith('.docx'):
        raise HTTPException(400, "仅支持 .docx 文件")
    config = request.app.state.config
    if api_type == "online" and not config.is_online_ready():
        raise HTTPException(400, "在线模式未配置：请先调用 /set-config")
    if not prompt.strip():
        raise HTTPException(400, "必须提供 prompt")

    if api_type == "online" and config.model_name.strip().lower() == "nlp":
        raise HTTPException(400, "NLP模型无法处理试卷分割问题")

    try:
        docx_bytes = await file.read()
        markdown_text = convert_docx_to_markdown(docx_bytes)

        if ocr_engine is not None:
            markdown_text = await replace_images_with_ocr_async(docx_bytes, markdown_text, ocr_engine)

        blocks = split_markdown_into_blocks(markdown_text)

        if api_type == "none":
            exam_map = ExamMap(questions=[])
        else:
            exam_map = get_online_segmentation(
                blocks=blocks,
                api_key=config.api_key,
                prompt=prompt,
                base_url=config.base_url,
                model_name=config.model_name
            )

        request.app.state.last_exam_map = exam_map
        request.app.state.last_blocks = blocks
        block_map = {b["id"]: b for b in blocks}
        for q in exam_map.questions:
            if q.indices:
                first_block = block_map.get(q.indices[0])
                if first_block:
                    raw_text = first_block.get("text", "")
                    match = re.search(r'^(\d+)[\.\．]\s*(.+?)$', raw_text, re.MULTILINE)
                    q.title = (match.group(2).strip()[:50] if match else raw_text[:50]) or "题目"
                else:
                    q.title = "题目"

        clean_blocks = [{k: v for k, v in b.items() if k != "image"} for b in blocks]

        return {"status": "success",
                "data": {"api_type": api_type, "blocks": clean_blocks, "questions": exam_map.questions}}
    except Exception:
        raise HTTPException(500, "服务器内部错误")


@app.post("/extract-tags")
async def extract_tags_endpoint(
        request: Request,
        content: str = Form(...),
        context_blocks: Optional[str] = Form(None),
        question_id: Optional[int] = Form(None)
) -> Dict[str, Any]:
    config: AppConfig = request.app.state.config
    if not config.is_online_ready():
        raise HTTPException(400, "全局配置未完成：请先调用 /set-config")
    if not content.strip():
        raise HTTPException(400, "题目内容不能为空")

    if config.model_name.strip().lower() == "nlp":
        raise HTTPException(400, "NLP模型无法处理标签提取问题")

    context_texts: Optional[List[str]] = None
    if context_blocks and context_blocks.strip():
        try:
            context_texts = json.loads(context_blocks)
            if not isinstance(context_texts, list):
                context_texts = None
        except Exception:
            pass

    default_score: Optional[float] = None
    if question_id is not None and hasattr(request.app.state, 'last_exam_map'):
        exam_map = request.app.state.last_exam_map
        if exam_map:
            for q in exam_map.questions:
                if q.id == question_id:
                    default_score = getattr(q, 'default_score', None)
                    break

    try:
        info = extract_question_info(
            content=content,
            api_key=config.api_key,
            base_url=config.base_url,
            model_name=config.model_name,
            context_blocks=context_texts
        )
        if info.score == 0.0 and default_score is not None:
            info.score = float(default_score)
        return {"status": "success", "data": info.model_dump(by_alias=True)}
    except Exception:
        raise HTTPException(500, "服务器内部错误")


@app.post("/check-similarity", response_model=SimilarityResponse)
async def check_similarity(request: Request, payload: SimilarityRequest) -> SimilarityResponse:
    try:
        config: AppConfig = request.app.state.config
        if not config.is_online_ready():
            raise HTTPException(400, "全局配置未完成：请先调用 /set-config")

        q1, q2 = payload.question1, payload.question2

        # ----- NLP 模式 -----
        if config.model_name.strip().lower() == "nlp":
            try:
                sim_score_decimal = compute_local_similarity(q1.body, q2.body)
                sim_score_percent = sim_score_decimal * 100.0
                sim_score_percent = 100 * (sim_score_percent / 100) ** 5.5
            except Exception as e:
                raise HTTPException(500, f"本地 NLP 模型计算相似度失败: {type(e).__name__}: {str(e)}")

            is_dup = sim_score_percent >= payload.threshold
            print(f"[NLP] 阈值: {payload.threshold}%, 相似度: {sim_score_percent:.2f}%, 判定: {'重复' if is_dup else '不重复'}")

            reason = None
            if is_dup:
                reason = f"基于 NLP 模型的内容相似度判定（相似度 {sim_score_percent:.2f}%）"
            return SimilarityResponse(
                is_duplicate=is_dup,
                similarity=sim_score_percent,   # 百分数，与 LLM 一致
                reason=reason,
                tag_check_passed=True
            )

        # ----- LLM 模式（-----
        tag_pass = check_tags_similarity(
            tags1=q1.tags, tags2=q2.tags,
            api_key=config.api_key, base_url=config.base_url, model_name=config.model_name
        )
        if not tag_pass:
            return SimilarityResponse(is_duplicate=False, similarity=0.0, reason=None, tag_check_passed=False)

        similarity, reason = compute_question_similarity(
            q1, q2,
            api_key=config.api_key,
            base_url=config.base_url,
            model_name=config.model_name,
            reason_threshold=payload.threshold
        )
        is_dup = similarity >= payload.threshold
        return SimilarityResponse(
            is_duplicate=is_dup,
            similarity=float(similarity),
            reason=reason if is_dup else None,
            tag_check_passed=True
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"服务器内部错误: {type(e).__name__}: {str(e)}")

@app.post("/validate-format", response_model=FormatValidationResponse)
async def validate_format(
        request: Request,
        file: UploadFile = File(...),
        format_checks: str = Form(...),
        expected_total_score: Optional[float] = Form(None),
        is_local_api: bool = Form(False)
) -> FormatValidationResponse:
    if not file.filename.endswith('.docx'):
        raise HTTPException(400, "仅支持 .docx 文件")
    try:
        checks_dict = json.loads(format_checks)
    except json.JSONDecodeError:
        raise HTTPException(400, "format_checks 参数必须是有效的 JSON 字符串")

    docx_bytes = await file.read()
    original_filename = file.filename
    config: AppConfig = request.app.state.config
    if not config.is_online_ready():
        raise HTTPException(400, "未配置 LLM 服务，请先调用 /set-config")

    if config.model_name.strip().lower() == "nlp":
        raise HTTPException(400, "NLP模型无法处理格式校验问题")

    try:
        if is_local_api:
            results = call_llm_for_format_validation_local(
                docx_bytes=docx_bytes,
                enabled_checks=checks_dict,
                api_key=config.api_key,
                base_url=config.base_url,
                model_name=config.model_name,
                expected_total_score=expected_total_score
            )
        else:
            pdf_bytes = convert_docx_to_pdf(docx_bytes)
            pdf_filename = original_filename.rsplit('.', 1)[0] + ".pdf"
            results = call_llm_for_format_validation(
                file_bytes=pdf_bytes,
                filename=pdf_filename,
                enabled_checks=checks_dict,
                api_key=config.api_key,
                base_url=config.base_url,
                model_name=config.model_name,
                expected_total_score=expected_total_score
            )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Connection error" in error_msg or "Connection refused" in error_msg or "timed out" in error_msg:
            raise HTTPException(
                status_code=502,
                detail=f"无法连接到 LLM 服务 (base_url: {config.base_url})。请检查：\n"
                       "1. 本地 LLM 服务是否已启动（如 Ollama、LM Studio）\n"
                       "2. base_url 是否正确（例如 Ollama 默认 http://localhost:11434/v1）\n"
                       "3. 端口是否开放，防火墙是否放行\n"
                       f"原始错误: {error_msg}"
            )
        raise HTTPException(500, f"格式校验失败: {error_msg}")

    passed_count = sum(1 for r in results if r.get("passed", False))
    total_count = len(results)
    summary = f"通过 {passed_count} 项，未通过 {total_count - passed_count} 项"
    response_items = [
        FormatCheckItemResult(
            code=r.get("code", ""),
            name=r.get("name", ""),
            passed=r.get("passed", False),
            reason=r.get("reason", "")
        )
        for r in results
    ]
    return FormatValidationResponse(results=response_items, summary=summary)


from docx.oxml.ns import qn   # 请确保文件头部已有此导入

from docx.oxml.ns import qn   # 必须在文件头部

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

@app.post("/generate-report")
async def generate_report(request: ReportGenerateRequest) -> Dict[str, Any]:
    if not os.path.exists(request.docx_file_path):
        raise HTTPException(400, f"原始文件不存在: {request.docx_file_path}")
    if not request.save_path.endswith('.docx'):
        raise HTTPException(400, "保存路径必须以 .docx 结尾")
    save_dir = os.path.dirname(request.save_path)
    if save_dir and not os.path.exists(save_dir):
        os.makedirs(save_dir)

    try:
        shutil.copy2(request.docx_file_path, request.save_path)
    except Exception as e:
        raise HTTPException(500, f"复制文件失败: {str(e)}")

    try:
        blocks = get_blocks_from_docx(request.docx_file_path)
        block_text_map = {block["id"]: block["text"] for block in blocks}
    except Exception as e:
        if os.path.exists(request.save_path):
            os.remove(request.save_path)
        raise HTTPException(500, f"文档切分失败: {str(e)}")

    try:
        doc = Document(request.save_path)

        w_ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

        def get_all_paragraphs_with_location(doc: Document):
            items = []
            for para in doc.paragraphs:
                items.append((para.text, para, False))

            sdt_elements = doc.element.findall(f'.//{{{w_ns}}}sdt')
            for sdt in sdt_elements:
                para_elems = sdt.findall(f'.//{{{w_ns}}}p')
                for p_elem in para_elems:
                    texts = []
                    for t_elem in p_elem.findall(f'.//{{{w_ns}}}t'):
                        if t_elem.text:
                            texts.append(t_elem.text)
                    para_text = ''.join(texts)
                    items.append((para_text, p_elem, True))
            return items

        text_items = get_all_paragraphs_with_location(doc)

        # ---------- 添加格式检查表格 + 分页符 ----------
        if request.format_checks:
            table = doc.add_table(rows=len(request.format_checks) + 1, cols=3)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = "格式条目"
            hdr_cells[1].text = "通过/不通过"
            hdr_cells[2].text = "原因"
            for i, check in enumerate(request.format_checks, start=1):
                row_cells = table.rows[i].cells
                row_cells[0].text = check.item
                row_cells[1].text = "✅ 通过" if check.passed else "❌ 不通过"
                row_cells[2].text = check.reason

            tbl = table._element
            body = doc.element.body
            first = body[0] if len(body) > 0 else None
            if first is not None:
                body.insert(0, tbl)
            else:
                body.append(tbl)

            # ---------- 在表格后面插入分页符 ----------
            # 构造分页符元素（<w:p><w:r><w:br w:type="page"/></w:r></w:p>）
            page_break = OxmlElement('w:p')
            run = OxmlElement('w:r')
            br = OxmlElement('w:br')
            br.set(qn('w:type'), 'page')
            run.append(br)
            page_break.append(run)

            # 找到表格在 body 中的位置，在其后插入分页符
            body = doc.element.body
            tbl_index = list(body).index(tbl)   # 获取表格元素的索引
            body.insert(tbl_index + 1, page_break)

        # ---------- 标注重复内容 ----------
        for dup in reversed(request.duplicate_results):
            if not dup.block_ids:
                continue
            first_block_id = dup.block_ids[0]
            block_text = block_text_map.get(first_block_id)
            if not block_text:
                continue

            best_item = None
            best_score = 0.0
            target_norm = re.sub(r'\s+', ' ', block_text.strip())
            for item_text, location, in_sdt in text_items:
                item_norm = re.sub(r'\s+', ' ', item_text.strip())
                score = difflib.SequenceMatcher(None, target_norm, item_norm).ratio()
                if score > best_score:
                    best_score = score
                    best_item = (item_text, location, in_sdt)

            if best_item is None:
                continue

            _, location, in_sdt = best_item

            if not in_sdt and isinstance(location, Paragraph):
                for run in location.runs:
                    run.font.color.rgb = RGBColor(255, 0, 0)

            target_elem = location._element if isinstance(location, Paragraph) else location

            comment_text = f"【重复提示】相似度：{dup.similarity}% | 重复位置：{dup.duplicate_location} | 原因：{dup.reason}"

            new_para = OxmlElement('w:p')
            run = OxmlElement('w:r')
            t = OxmlElement('w:t')
            t.text = comment_text
            run.append(t)

            rPr = OxmlElement('w:rPr')
            color = OxmlElement('w:color')
            color.set(qn('w:val'), 'FF0000')
            rPr.append(color)
            run.insert(0, rPr)

            new_para.append(run)
            target_elem.addnext(new_para)

        doc.save(request.save_path)

        return {
            "status": "success",
            "message": "报告生成成功",
            "save_path": request.save_path
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        if os.path.exists(request.save_path):
            os.remove(request.save_path)
        raise HTTPException(500, f"报告生成失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)