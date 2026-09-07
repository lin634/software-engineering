"""
Flux Realism 图像生成器 - FastAPI 后端
=====================================
调用 Hugging Face Inference API 中的 XLabs-AI/flux-RealismLora 模型，
通过前端交互式界面实现文本生成真实感图像。

模型说明：
  - XLabs-AI/flux-RealismLora 是基于 FLUX.1-dev 的 LoRA 适配器
  - 专门训练用于生成具有照片级真实感的图像
  - 通过 fal.ai 推理提供商在 Hugging Face 平台上可用

启动方式：
  uvicorn main:app --reload --port 8000
"""

import os
import io
import base64
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# ============================================================
# 配置与初始化
# ============================================================
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Hugging Face 配置
HF_TOKEN = os.getenv("HF_TOKEN", "")
MODEL_ID = "XLabs-AI/flux-RealismLora"
# 模型页面显示 "fal" 为推理提供商，客户端中使用 "fal-ai"
INFERENCE_PROVIDER = "fal-ai"

app = FastAPI(
    title="Flux Realism 图像生成器",
    description="基于 Hugging Face Inference API + XLabs-AI/flux-RealismLora 的交互式图像生成服务",
    version="1.0.0",
)

# 允许跨域请求（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 请求/响应数据模型
# ============================================================
class GenerateRequest(BaseModel):
    """图像生成请求参数"""
    prompt: str = Field(
        ..., min_length=1, max_length=2000,
        description="文本提示词，描述要生成的图像内容",
        examples=["A close-up portrait of an elderly fisherman, weathered skin, deep wrinkles, white beard, wearing a rain-soaked yellow raincoat, standing on a wooden dock at dawn, soft overcast lighting, shot on Canon EOS R5, 85mm f/1.4 lens, shallow depth of field, ultra realistic, 8K"],
    )
    negative_prompt: Optional[str] = Field(
        None, max_length=1000,
        description="负向提示词，描述不希望出现在图像中的元素",
        examples=["cartoon, anime, illustration, painting, low quality, blurry, deformed, extra fingers, watermark, text"],
    )
    width: int = Field(1024, ge=256, le=2048, description="输出图像宽度（像素）")
    height: int = Field(1024, ge=256, le=2048, description="输出图像高度（像素）")
    num_inference_steps: int = Field(28, ge=1, le=100, description="去噪步数，越多质量越高但越慢")
    guidance_scale: float = Field(3.5, ge=0, le=20, description="引导尺度，越高越贴合提示词但可能产生伪影")
    seed: Optional[int] = Field(None, ge=0, le=4294967295, description="随机种子，相同种子+参数可复现结果")


class GenerateResponse(BaseModel):
    """图像生成响应"""
    success: bool
    image_base64: str = Field("", description="Base64 编码的 PNG 图像数据")
    parameters: dict = Field({}, description="实际使用的生成参数")
    message: str = Field("", description="附加信息或错误描述")


# ============================================================
# API 端点
# ============================================================
@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "model": MODEL_ID,
        "provider": INFERENCE_PROVIDER,
        "token_configured": bool(HF_TOKEN),
    }


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_image(req: GenerateRequest):
    """
    调用 Hugging Face Inference API 生成图像。

    流程：
    1. 验证 HF_TOKEN 是否已配置
    2. 创建 InferenceClient（指定 fal-ai 提供商）
    3. 调用 text_to_image() 方法，传入提示词和生成参数
    4. 将返回的 PIL Image 转换为 Base64 编码
    5. 返回给前端展示
    """
    # 步骤 1：检查 Token
    if not HF_TOKEN:
        logger.error("HF_TOKEN 未配置")
        raise HTTPException(
            status_code=500,
            detail="Hugging Face API Token 未配置。请在 .env 文件中设置 HF_TOKEN。",
        )

    logger.info("=" * 60)
    logger.info("开始图像生成请求")
    logger.info(f"  模型: {MODEL_ID}")
    logger.info(f"  提供商: {INFERENCE_PROVIDER}")
    logger.info(f"  提示词: {req.prompt[:100]}{'...' if len(req.prompt) > 100 else ''}")
    logger.info(f"  负向提示词: {req.negative_prompt or '(无)'}")
    logger.info(f"  尺寸: {req.width}x{req.height}")
    logger.info(f"  步数: {req.num_inference_steps}")
    logger.info(f"  引导尺度: {req.guidance_scale}")
    logger.info(f"  种子: {req.seed}")
    logger.info("=" * 60)

    try:
        # 步骤 2：创建 InferenceClient
        # - token: Hugging Face Access Token
        # - provider: "fal-ai" 是该模型支持的推理提供商
        client = InferenceClient(
            token=HF_TOKEN,
            provider=INFERENCE_PROVIDER,
        )

        # 步骤 3：调用 text_to_image 生成图像
        image = client.text_to_image(
            prompt=req.prompt,
            negative_prompt=req.negative_prompt,
            height=req.height,
            width=req.width,
            num_inference_steps=req.num_inference_steps,
            guidance_scale=req.guidance_scale,
            seed=req.seed,
            model=MODEL_ID,
        )

        # 步骤 4：将 PIL Image 转为 Base64
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        logger.info(f"✅ 图像生成成功！图像大小: {len(image_bytes)} bytes "
                     f"({len(image_b64)} base64 chars)")
        logger.info(f"  图像尺寸: {image.size}")

        # 步骤 5：返回结果
        parameters = {
            "model": MODEL_ID,
            "provider": INFERENCE_PROVIDER,
            "prompt": req.prompt,
            "negative_prompt": req.negative_prompt,
            "width": req.width,
            "height": req.height,
            "num_inference_steps": req.num_inference_steps,
            "guidance_scale": req.guidance_scale,
            "seed": req.seed,
            "image_size_px": list(image.size),
            "image_bytes": len(image_bytes),
        }

        return GenerateResponse(
            success=True,
            image_base64=image_b64,
            parameters=parameters,
            message="图像生成成功",
        )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ 图像生成失败: {error_msg}")
        logger.exception("详细错误信息:")

        # 根据错误类型返回友好提示
        if "401" in error_msg or "Unauthorized" in error_msg:
            detail = "API Token 无效或已过期，请检查 .env 中的 HF_TOKEN"
        elif "429" in error_msg or "rate" in error_msg.lower():
            detail = "请求频率过高，请稍后重试"
        elif "503" in error_msg or "loading" in error_msg.lower():
            detail = "模型正在加载中，请等待几秒后重试"
        elif "502" in error_msg or "provider" in error_msg.lower():
            detail = f"推理提供商 {INFERENCE_PROVIDER} 暂时不可用，请稍后重试"
        else:
            detail = f"图像生成失败: {error_msg}"

        return GenerateResponse(
            success=False,
            image_base64="",
            parameters={},
            message=detail,
        )


# ============================================================
# 静态文件服务（前端页面）
# ============================================================
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
