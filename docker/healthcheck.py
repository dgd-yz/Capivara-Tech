"""Container healthcheck: bate em /health/ e sai 0 se responder 200."""
import sys
import urllib.request

URL = "http://127.0.0.1:8000/health/"

try:
    with urllib.request.urlopen(URL, timeout=5) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception as exc:  # noqa: BLE001
    print(f"healthcheck failed: {exc}", file=sys.stderr)
    sys.exit(1)
