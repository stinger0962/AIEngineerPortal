"""Global error handling middleware."""
import logging
import traceback
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("portal")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(
                "unhandled_error",
                extra={
                    "path": request.url.path,
                    "method": request.method,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error. Please try again."},
            )
