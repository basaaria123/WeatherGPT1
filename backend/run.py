#!/usr/bin/env python3
"""Development entry point: `python run.py`."""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"},
    )
