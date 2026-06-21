"""
ocr_module.py - 本地OCR识别引擎模块

基于 Pix2Text 实现中英文文本与数学公式的混合识别。
模型文件存放在项目目录的 models 子目录中，实现便携式部署。
"""

import os
import io
import asyncio
import logging

# ==================== 抑制第三方库的冗余日志输出 ====================
# 必须在导入相关库之前设置
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"          # 抑制 TensorFlow 日志
os.environ["YOLO_VERBOSE"] = "False"              # 抑制 YOLO 详细输出
os.environ["PIX2TEXT_LOG_LEVEL"] = "ERROR"        # Pix2Text 日志级别

# 设置各类日志记录器的级别为 ERROR，仅显示错误信息
logging.getLogger("cnocr").setLevel(logging.ERROR)
logging.getLogger("cnstd").setLevel(logging.ERROR)
logging.getLogger("Pix2Text").setLevel(logging.ERROR)
logging.getLogger("ultralytics").setLevel(logging.ERROR)
logging.getLogger("PIL").setLevel(logging.ERROR)

# ==================== 模型路径配置 ====================
current_dir = os.path.dirname(os.path.abspath(__file__))
models_dir = os.path.join(current_dir, "models")

os.environ["PIX2TEXT_HOME"] = os.path.join(models_dir, "pix2text")
os.environ["CNOCR_HOME"] = os.path.join(models_dir, "cnocr")
os.environ["CNSTD_HOME"] = os.path.join(models_dir, "cnstd")

# ==================== 导入 Pix2Text ====================
try:
    from pix2text import Pix2Text
except ImportError:
    raise ImportError("未检测到 pix2text 库，请先运行 'pip install pix2text' 安装。")

import torch
from PIL import Image


class LocalOCREngine:
    """
    本地 OCR 识别引擎，基于 Pix2Text 实现。
    支持中英文文本与数学公式的混合识别，可运行在 CPU 或 CUDA 设备上。
    """

    def __init__(
            self,
            model_path: str = None,       # 保留参数以兼容旧接口，实际不使用
            clip_model_path: str = None,  # 保留参数以兼容旧接口，实际不使用
            n_threads: int = 4,           # 保留参数以兼容旧接口，实际不使用
            chat_format: str = None       # 保留参数以兼容旧接口，实际不使用
    ):
        """
        初始化 Pix2Text 引擎。
        """
        # 自动检测计算设备：优先使用 CUDA（GPU），否则使用 CPU
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # 尝试在检测到的设备上加载模型；若失败则降级到 CPU
        try:
            self.model = Pix2Text(languages=('ch', 'en'), device=self.device)
        except Exception:
            self.model = Pix2Text(languages=('ch', 'en'), device='cpu')

    async def recognize(self, image_bytes: bytes) -> str:
        """
        异步执行 OCR 识别。

        参数:
            image_bytes: 图片的原始二进制数据

        返回值:
            识别出的文本字符串
        """
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._run_ocr, image_bytes)
        return result

    def _run_ocr(self, image_bytes: bytes) -> str:
        """
        同步执行 OCR 识别，内部调用 Pix2Text 引擎。
        """
        image = Image.open(io.BytesIO(image_bytes))

        # 优先使用 Pix2Text 的混合识别接口
        if hasattr(self.model, 'recognize_text_formula'):
            output_text = self.model.recognize_text_formula(image)
        else:
            outs = self.model.recognize(image)
            if isinstance(outs, str):
                output_text = outs
            elif isinstance(outs, list):
                res_list = []
                for out in outs:
                    if isinstance(out, dict):
                        text = out.get('text', '')
                        type_ = out.get('type', 'text')
                        if type_ == 'formula':
                            res_list.append(f" $${text}$$ ")
                        else:
                            res_list.append(text)
                    else:
                        res_list.append(str(out))
                output_text = "\n".join(res_list)
            else:
                output_text = str(outs)

        return output_text

    def unload(self):
        """
        释放模型占用的显存/内存资源。
        """
        if hasattr(self, 'model'):
            del self.model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()