import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from app.api.health import record_metric

logger = logging.getLogger(__name__)

class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware that attaches a unique Request ID to every incoming request,
    logs duration and status code, and records metrics for Prometheus monitoring.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        duration = time.time() - start_time
        response.headers["x-request-id"] = request_id
        response.headers["x-response-time"] = f"{duration:.4f}s"

        endpoint_path = request.url.path
        record_metric(endpoint_path, response.status_code, duration)

        logger.info(
            f"[{request_id[:8]}] {request.method} {endpoint_path} -> {response.status_code} ({duration:.3f}s)"
        )

        return response
