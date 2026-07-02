"""Lightweight request logging middleware."""
from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("quran_rag.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and full latency for each request.

    For streaming endpoints (SSE /chat/stream, /lexical/stream) ``call_next``
    returns as soon as the response *starts* — the body (the LLM generation) is
    streamed afterwards. Timing right there would only capture time-to-first-byte
    and hide the slow part. So we wrap the body iterator and log once the whole
    response has been sent, giving the true end-to-end latency. Non-streaming
    responses are handled uniformly (they also flow through the body iterator).
    """

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        body_iterator = response.body_iterator

        async def timed_body():
            complete = False
            try:
                async for chunk in body_iterator:
                    yield chunk
                complete = True
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "%s %s -> %s (%.1f ms%s)",
                    request.method,
                    request.url.path,
                    response.status_code,
                    elapsed_ms,
                    "" if complete else ", client disconnected",
                )

        response.body_iterator = timed_body()
        return response
