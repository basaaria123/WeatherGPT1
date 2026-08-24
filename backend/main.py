"""ASGI entrypoint.

Hosting platforms commonly look for an ``app`` callable in a module at the
service root. The application itself lives in ``app/main.py``; this is only a
re-export so ``uvicorn main:app`` and platform auto-detection both work.
"""

from app.main import app

__all__ = ["app"]
