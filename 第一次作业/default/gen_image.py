#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用 Hugging Face Inference (fal-ai) 生成图片。

用法:
    HF_TOKEN=hf_xxx python gen_image.py "提示词"
    HF_TOKEN=hf_xxx python gen_image.py "提示词" -o out.png -m XLabs-AI/flux-RealismLora

说明:
    本机 Python 自带的 OpenSSL 1.1.1n 较旧，与 fal-ai 路由及图片 CDN
    (v3b.fal.media) 做 TLS 握手时存在间歇性 EOF 失败。脚本已内置
    重试 + curl 兜底来规避此问题。
"""
import argparse
import os
import sys
import time
import subprocess
from urllib.parse import urlparse

import huggingface_hub.inference._providers.fal_ai as fal_mod
from huggingface_hub import InferenceClient
from huggingface_hub.utils import get_session


def fetch_with_curl(url, timeout=90):
    res = subprocess.run(
        ["curl", "-sS", "-L", "-m", str(timeout), "-o", "-", url],
        capture_output=True,
    )
    if res.returncode != 0:
        raise RuntimeError(
            f"curl 失败(code {res.returncode}): "
            f"{res.stderr.decode(errors='replace').strip()}"
        )
    return res.stdout


# --- 绕开间歇性 TLS 失败: 取图先 httpx 重试, 失败则 curl 兜底 ---
def patched_get_response(self, response, request_params=None):
    data = fal_mod._as_dict(response)
    url = data["images"][0]["url"]

    for i in range(3):
        try:
            return get_session().get(url, timeout=30).content
        except Exception:
            time.sleep(1)

    return fetch_with_curl(url)


fal_mod.FalAITextToImageTask.get_response = patched_get_response


def main():
    p = argparse.ArgumentParser(description="HF fal-ai 文生图")
    p.add_argument("prompt", help="图片提示词")
    p.add_argument("-o", "--output", default="output.png", help="输出文件名")
    p.add_argument(
        "-m", "--model", default="XLabs-AI/flux-RealismLora", help="模型 ID"
    )
    p.add_argument("--tries", type=int, default=10, help="最大重试次数")
    args = p.parse_args()

    api_key = os.environ.get("HF_TOKEN")
    if not api_key:
        sys.exit("错误: 未设置 HF_TOKEN 环境变量")

    client = InferenceClient(provider="fal-ai", api_key=api_key)

    for attempt in range(1, args.tries + 1):
        print(f"[{attempt}/{args.tries}] 生成中...", flush=True)
        try:
            image = client.text_to_image(args.prompt, model=args.model)
            image.save(args.output)
            print(f"完成: {os.path.abspath(args.output)}  尺寸: {image.size}")
            return
        except Exception as e:
            print(f"  失败: {type(e).__name__}: {str(e)[:120]}")
            time.sleep(2)

    sys.exit(f"重试 {args.tries} 次仍失败")


if __name__ == "__main__":
    main()
