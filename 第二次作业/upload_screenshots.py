#!/usr/bin/env python3
"""把 screenshots/ 下的截图上传到博客园，并把 Markdown 里的图片链接替换成博客园地址。

用法：
    python upload_screenshots.py            # 上传 + 改写 README.md 与博文
    python upload_screenshots.py --dry      # 只上传打印映射，不改文件
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
UPLOADER_DIR = r"D:\软件工程\imgupload\marktext-cnblogs-uploader"
CNBLOG_CONFIG = r"D:\软件工程\imgupload\config.json"
MAPPING = os.path.join(HERE, "screenshots_cnblogs.json")

# 复用你写的上传器
sys.path.insert(0, UPLOADER_DIR)
from cnblog_uploader import load_config, upload_image  # noqa: E402

MARKDOWNS = ["README.md", "软件工程第二次个人作业.md"]
GITHUB_PREFIX = ("https://raw.githubusercontent.com/lin634/software-engineering/"
                 "master/%E7%AC%AC%E4%BA%8C%E6%AC%A1%E4%BD%9C%E4%B8%9A/screenshots/")


def main() -> int:
    dry = "--dry" in sys.argv
    cfg = load_config(None if not os.path.exists(CNBLOG_CONFIG)
                      else Path(CNBLOG_CONFIG))

    mapping: dict[str, str] = {}
    if os.path.exists(MAPPING):
        with open(MAPPING, encoding="utf-8") as f:
            mapping = json.load(f)

    files = sorted(f for f in os.listdir(os.path.join(HERE, "screenshots"))
                   if f.lower().endswith((".png", ".jpg", ".jpeg")))

    cfg_url = cfg["blog_url"]
    print(f"接口：{cfg_url}（{len(files)} 张）")
    ok = fail = 0
    for name in files:
        path = os.path.join(HERE, "screenshots", name)
        if name in mapping:
            print(f"  跳过（已上传）{name} -> {mapping[name]}")
            ok += 1
            continue
        url = upload_image(Path(path), cfg)
        # 校验链接真的能取到
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                size = r.status, r.headers.get("Content-Length", "?")
        except Exception as e:  # noqa: BLE001
            print(f"  ! {name} 上传后校验失败：{e}")
            fail += 1
            continue
        mapping[name] = url
        ok += 1
        print(f"  OK {name} -> {url}  (HTTP {size[0]}, {size[1]} bytes)")
        time.sleep(0.6)

    if not dry:
        with open(MAPPING, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        print(f"\n映射已保存：{MAPPING}")

    total = ok + fail
    print(f"\n上传完成：{ok}/{total} 成功")
    if fail:
        print(f"失败 {fail} 张，未改 Markdown 文件。")
        return 1
    if dry:
        print("--dry：未改写 Markdown 文件")
        return 0

    # ---- 改写 Markdown ----
    for rel in MARKDOWNS:
        p = os.path.join(HERE, rel)
        with open(p, encoding="utf-8") as f:
            text = f.read()
        before = text.count(GITHUB_PREFIX)
        for name, url in mapping.items():
            text = text.replace(GITHUB_PREFIX + name, url)
        left = text.count(GITHUB_PREFIX)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(f"{rel}：替换 {before} 处，剩余 GitHub 链接 {left} 处")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
