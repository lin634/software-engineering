import urllib.request
import os

print("=== 环境里的 *_proxy 变量 ===")
for k in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","http_proxy","https_proxy","all_proxy","NO_PROXY","no_proxy"]:
    print(f"  {k}={os.environ.get(k)}")

print("\n=== urllib 检测到的代理 (含 Windows 注册表) ===")
print(" ", urllib.request.getproxies())

import httpx
print("\n=== httpx 直连测试 https://fal.run/ ===")

# 1) 默认 (trust_env=True，可能用系统代理)
try:
    r = httpx.get("https://fal.run/", timeout=20)
    print(f"  trust_env=True (默认): OK {r.status_code}")
except Exception as e:
    print(f"  trust_env=True (默认): FAIL {type(e).__name__}: {e}")

# 2) 关掉 trust_env，强制直连
try:
    with httpx.Client(trust_env=False) as c:
        r = c.get("https://fal.run/", timeout=20)
        print(f"  trust_env=False: OK {r.status_code}")
except Exception as e:
    print(f"  trust_env=False: FAIL {type(e).__name__}: {e}")

# 3) 显式 proxy=None + trust_env=False
try:
    with httpx.Client(trust_env=False, proxy=None) as c:
        r = c.get("https://fal.run/", timeout=20)
        print(f"  proxy=None: OK {r.status_code}")
except Exception as e:
    print(f"  proxy=None: FAIL {type(e).__name__}: {e}")
