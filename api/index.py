"""Vercel Python serverless entrypoint — serves the FastAPI ASGI app.

Vercel's @vercel/python runtime serves the top-level `app` (ASGI) natively — no
Mangum. `apps/api` is prepended to sys.path so `from main import app` resolves the
existing FastAPI application unchanged. vercel.json rewrites all `/api/*` here.
"""
import os
import sys

_API_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps", "api"
)
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)

from main import app  # noqa: E402  (sys.path configured above)

__all__ = ["app"]
