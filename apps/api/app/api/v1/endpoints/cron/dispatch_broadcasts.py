"""Vercel Cron endpoint — one-shot broadcast dispatch pass.

Replaces the always-on background loop (removed for serverless). Vercel Cron hits
this daily; it runs ONE worker tick (promote scheduled -> send pending batch ->
complete) via the existing dispatcher and returns the counts. Protected by
CRON_SECRET — Vercel sends `Authorization: Bearer <CRON_SECRET>`; a `?secret=`
query is also accepted for manual runs.
"""
import logging

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.core.config import settings
from app.jobs.broadcast_dispatch_job import run_once_in_session

logger = logging.getLogger(__name__)
router = APIRouter()


def _authorized(authorization: str | None, secret: str | None) -> bool:
    expected = settings.CRON_SECRET
    if not expected:
        return False  # refuse to run an unprotected cron
    if authorization and authorization == f"Bearer {expected}":
        return True
    if secret and secret == expected:
        return True
    return False


@router.api_route(
    "/dispatch-broadcasts",
    methods=["GET", "POST"],
    summary="Cron: dispatch broadcast emails (one pass)",
)
def dispatch_broadcasts(
    authorization: str | None = Header(default=None),
    secret: str | None = Query(default=None),
):
    if not _authorized(authorization, secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid cron secret")
    result = run_once_in_session(
        batch_size=settings.BROADCAST_BATCH_SIZE,
        max_attempts=settings.BROADCAST_MAX_ATTEMPTS,
        stuck_timeout_s=settings.BROADCAST_STUCK_TIMEOUT_S,
    )
    logger.info("Cron dispatch-broadcasts: %s", result)
    return {"ok": True, **result}
