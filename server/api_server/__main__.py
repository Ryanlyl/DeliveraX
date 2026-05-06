from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "api_server.main:app",
        host=os.getenv("DELIVERAX_HOST", "127.0.0.1"),
        port=int(os.getenv("DELIVERAX_PORT", "8000")),
        reload=os.getenv("DELIVERAX_RELOAD", "true").lower() in {"1", "true", "yes"},
    )


if __name__ == "__main__":
    main()
