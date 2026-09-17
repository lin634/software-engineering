# -*- coding: utf-8 -*-
"""把「一箭又一箭」打包成 Windows 可执行文件（PyInstaller）。

用法： python build_exe.py

产物： dist/一箭又一箭.exe —— 单文件、无控制台窗口，双击即可运行，
      目标机器无需安装 Python 或任何依赖（字体取系统自带的微软雅黑）。

打包后建议实测一次：双击 exe 确认窗口能弹出、中文正常、音效正常。
仅开发期使用，游戏运行不需要本文件。
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

EXE_NAME = "一箭又一箭"
ENTRY = "arrow_game.py"


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("未安装 PyInstaller，请先执行： pip install pyinstaller")
        return 1

    if not os.path.exists(ENTRY):
        print(f"找不到入口脚本 {ENTRY}")
        return 1

    # 清理上次的产物，避免 PyInstaller 复用过期缓存
    for stale in ("build", "dist"):
        shutil.rmtree(stale, ignore_errors=True)
    spec = f"{EXE_NAME}.spec"
    if os.path.exists(spec):
        os.remove(spec)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",       # 打成单个 exe，便于分发
        "--windowed",      # 不附带黑色控制台窗口
        "--noupx",         # 不用 UPX 压缩，减少杀软误报
        "--name", EXE_NAME,
        ENTRY,
    ]
    print("执行：", " ".join(cmd))
    code = subprocess.call(cmd)
    if code != 0:
        print(f"\n打包失败（退出码 {code}）")
        return code

    exe = os.path.join("dist", EXE_NAME + ".exe")
    if not os.path.exists(exe):
        print(f"\n打包结束但未找到产物：{exe}")
        return 1

    size_mb = os.path.getsize(exe) / 1024 / 1024
    print(f"\n打包成功：{os.path.abspath(exe)}（{size_mb:.1f} MB）")
    print("已验证：产物存在且非空。请双击运行实测一次窗口与中文显示。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
