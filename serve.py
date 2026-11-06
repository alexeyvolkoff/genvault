"""genvault v2 entry point: uvicorn on 127.0.0.1, port from config.json."""
import sys

import uvicorn

from backend.cfgfile import ConfigError

try:
    from backend import config
except ConfigError as e:
    print(f"[genvault] NOT STARTED — {e}", flush=True)
    sys.exit(2)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=config.PORT, log_level="info")
