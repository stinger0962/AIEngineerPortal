"""Request logging middleware with latency tracking."""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("portal")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        latency_ms = int((time.time() - start) * 1000)

        # Skip health check noise
        if request.url.path == "/health":
            return response

        logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "client": request.client.host if request.client else "unknown",
            },
        )

        # Log slow requests as warnings
        if latency_ms > 5000:
            logger.warning(
                "slow_request",
                extra={
                    "path": request.url.path,
                    "latency_ms": latency_ms,
                },
            )

        return response
