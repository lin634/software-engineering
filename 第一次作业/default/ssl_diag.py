import ssl
import socket
import time
import sys
from urllib.parse import urlparse

print("Python:", sys.version.split()[0], "| OpenSSL:", ssl.OPENSSL_VERSION)

HOSTS = ["fal.run", "queue.fal.run", "huggingface.co", "rest.fal.ai"]

def try_handshake(host, force_tls12=False, port=443):
    if force_tls12:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.maximum_version = ssl.TLSVersion.TLSv1_2
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    else:
        ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=15) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                return True, ssock.version()
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

for host in HOSTS:
    print(f"\n=== {host} ===")
    for label, force in [("默认(允许1.3)", False), ("强制TLS1.2", True)]:
        ok, info = try_handshake(host, force_tls12=force)
        print(f"  {label}: {'OK ' + info if ok else 'FAIL ' + str(info)}")
