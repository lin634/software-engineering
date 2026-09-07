"""
Hugging Face Inference API 测试脚本
====================================
独立测试对 XLabs-AI/flux-RealismLora 模型的 API 调用。
同时演示两种调用方式：
  方式一：使用 huggingface_hub 的 InferenceClient（推荐）
  方式二：直接使用 requests 调用 REST API（便于理解底层原理）

运行方式：
  python test_api.py
  或
  python test_api.py --prompt "your custom prompt" --method rest
"""

import os
import sys
import time
import base64
import argparse
import requests
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# ============================================================
# 配置
# ============================================================
HF_TOKEN = os.getenv("HF_TOKEN", "")
MODEL_ID = "XLabs-AI/flux-RealismLora"
PROVIDER = "fal-ai"
OUTPUT_DIR = "test_outputs"

# 真实感提示词（详细设计，见 README）
REALISM_PROMPT = (
    "A close-up portrait of an elderly fisherman with weathered, sun-darkened skin "
    "and deep wrinkles, piercing blue eyes, white beard, wearing a rain-soaked yellow "
    "raincoat, standing on a weathered wooden dock at dawn, soft overcast lighting, "
    "water droplets on his skin, shot on Canon EOS R5 with 85mm f/1.4 lens, shallow "
    "depth of field, ultra realistic, highly detailed, 8K photography"
)
NEGATIVE_PROMPT = (
    "cartoon, anime, illustration, painting, low quality, blurry, "
    "deformed, extra fingers, watermark, text, oversaturated"
)


def log(msg, level="INFO"):
    """带时间戳的日志输出"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def check_token():
    """检查 Token 是否已配置"""
    if not HF_TOKEN:
        log("❌ HF_TOKEN 未配置！请在 .env 文件中设置你的 Hugging Face Access Token", "ERROR")
        log("   获取地址: https://huggingface.co/settings/tokens", "ERROR")
        sys.exit(1)
    log(f"✅ Token 已配置 (前8位: {HF_TOKEN[:8]}...)")
    return True


# ============================================================
# 方式一：使用 InferenceClient（官方推荐方式）
# ============================================================
def test_with_inference_client(prompt, negative_prompt, save_path):
    """使用 huggingface_hub.InferenceClient 调用 API"""
    from huggingface_hub import InferenceClient

    log("=" * 60)
    log("方式一：使用 InferenceClient 调用 API")
    log("=" * 60)
    log(f"  模型: {MODEL_ID}")
    log(f"  提供商: {PROVIDER}")
    log(f"  提示词: {prompt[:80]}...")

    # 创建客户端
    client = InferenceClient(
        token=HF_TOKEN,
        provider=PROVIDER,
    )

    # 计时开始
    start_time = time.time()

    # 调用 text_to_image
    image = client.text_to_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        height=1024,
        width=1024,
        num_inference_steps=28,
        guidance_scale=3.5,
        model=MODEL_ID,
    )

    elapsed = time.time() - start_time

    # 保存图像
    image.save(save_path)
    file_size = os.path.getsize(save_path)

    log(f"✅ 图像生成成功！")
    log(f"  耗时: {elapsed:.2f} 秒")
    log(f"  图像尺寸: {image.size}")
    log(f"  文件大小: {file_size} bytes ({file_size / 1024:.1f} KB)")
    log(f"  保存路径: {save_path}")

    return True


# ============================================================
# 方式二：直接 REST API 调用（展示底层原理）
# ============================================================
def test_with_rest_api(prompt, negative_prompt, save_path):
    """直接使用 HTTP POST 调用 Hugging Face Router API"""
    log("=" * 60)
    log("方式二：使用 REST API 直接调用")
    log("=" * 60)

    # Hugging Face Router API 端点
    # 格式: https://router.huggingface.co/{provider}/v1/
    # 对于 text-to-image，使用 fal-ai 提供商
    api_url = f"https://router.huggingface.co/{PROVIDER}/v1/"

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    # fal-ai 提供商的 text-to-image 请求体格式
    payload = {
        "model": MODEL_ID,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "image_size": {"width": 1024, "height": 1024},
        "num_inference_steps": 28,
        "guidance_scale": 3.5,
    }

    log(f"  API URL: {api_url}")
    log(f"  请求头: Authorization: Bearer {HF_TOKEN[:8]}...")
    log(f"  模型: {MODEL_ID}")

    start_time = time.time()

    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=120,
    )

    elapsed = time.time() - start_time

    log(f"  HTTP 状态码: {response.status_code}")
    log(f"  响应头 Content-Type: {response.headers.get('content-type', 'unknown')}")

    if response.status_code == 200:
        # 响应为图像数据
        content_type = response.headers.get("content-type", "")

        if "image" in content_type:
            # 直接是图像二进制数据
            image_bytes = response.content
            with open(save_path, "wb") as f:
                f.write(image_bytes)
            log(f"✅ 图像生成成功！")
            log(f"  耗时: {elapsed:.2f} 秒")
            log(f"  文件大小: {len(image_bytes)} bytes ({len(image_bytes) / 1024:.1f} KB)")
            log(f"  保存路径: {save_path}")
            return True
        else:
            # 可能是 JSON 响应（包含 base64 图像或 URL）
            try:
                data = response.json()
                log(f"  JSON 响应: {str(data)[:200]}...")
                if "image" in data:
                    image_bytes = base64.b64decode(data["image"])
                    with open(save_path, "wb") as f:
                        f.write(image_bytes)
                    log(f"✅ 图像从 JSON 响应中提取成功！")
                    return True
                elif "url" in data:
                    img_response = requests.get(data["url"])
                    with open(save_path, "wb") as f:
                        f.write(img_response.content)
                    log(f"✅ 图像从 URL 下载成功！")
                    return True
            except Exception as e:
                log(f"❌ 解析响应失败: {e}", "ERROR")
                log(f"  响应内容前200字符: {response.text[:200]}")
                return False
    else:
        log(f"❌ API 调用失败！状态码: {response.status_code}", "ERROR")
        log(f"  错误响应: {response.text[:500]}", "ERROR")
        return False


# ============================================================
# 主函数
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="测试 Hugging Face Inference API 调用")
    parser.add_argument("--prompt", type=str, default=REALISM_PROMPT,
                        help="自定义提示词")
    parser.add_argument("--negative", type=str, default=NEGATIVE_PROMPT,
                        help="自定义负向提示词")
    parser.add_argument("--method", type=str, default="client",
                        choices=["client", "rest"],
                        help="调用方式: client (InferenceClient) 或 rest (REST API)")
    args = parser.parse_args()

    log("🚀 Hugging Face Inference API 测试")
    log(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  调用方式: {args.method}")

    # 检查 Token
    check_token()

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_path = os.path.join(OUTPUT_DIR, f"test_{args.method}_{timestamp}.png")

    # 执行测试
    if args.method == "client":
        success = test_with_inference_client(args.prompt, args.negative, save_path)
    else:
        success = test_with_rest_api(args.prompt, args.negative, save_path)

    # 汇总
    log("=" * 60)
    if success:
        log(f"🎉 测试完成！图像已保存至: {save_path}")
    else:
        log(f"💔 测试失败，请检查错误信息", "ERROR")
        sys.exit(1)
    log("=" * 60)


if __name__ == "__main__":
    main()
