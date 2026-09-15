import time
import httpx
import logging
from typing import Dict, Any
from fastapi import APIRouter, status, Response
from fastapi.responses import JSONResponse
from app.config import settings
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health Checks & Observability"])

_START_TIME = time.time()

# Simple in-memory metrics store for Prometheus exporter format
_REQUEST_COUNTERS: Dict[str, int] = {}
_REQUEST_LATENCIES: Dict[str, float] = {}

def record_metric(endpoint: str, status_code: int, duration_sec: float):
    key = f"{endpoint}:{status_code}"
    _REQUEST_COUNTERS[key] = _REQUEST_COUNTERS.get(key, 0) + 1
    _REQUEST_LATENCIES[endpoint] = _REQUEST_LATENCIES.get(endpoint, 0.0) + duration_sec

@router.get("", status_code=status.HTTP_200_OK)
@router.get("/liveness", status_code=status.HTTP_200_OK)
def liveness_check():
    """
    Basic liveness probe verifying FastAPI process execution.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "uptime_seconds": round(time.time() - _START_TIME, 2)
    }

@router.get("/readiness")
async def readiness_check():
    """
    Comprehensive readiness probe verifying backend dependencies (Qdrant, LLM Provider, Visual Engine).
    """
    dependencies: Dict[str, Any] = {
        "qdrant": {"status": "unknown"},
        "llm_engine": {"status": "unknown"},
        "visual_engine": {"status": "unknown"}
    }
    all_healthy = True

    # 1. Qdrant Check
    try:
        mem_service = MemoryService.get_instance()
        collections = mem_service.client.get_collections()
        dependencies["qdrant"] = {"status": "healthy", "collections_count": len(collections.collections)}
    except Exception as e:
        logger.error(f"Readiness check failed for Qdrant: {e}", exc_info=True)
        dependencies["qdrant"] = {"status": "degraded", "error": "Dependency unavailable"}
        all_healthy = False

    # 2. LLM Engine Check
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            llm_url = settings.LLM_BASE_URL.rstrip("/v1") + "/api/tags" if "11434" in settings.LLM_BASE_URL else settings.LLM_BASE_URL
            resp = await client.get(llm_url)
            if resp.status_code in [200, 404]:
                dependencies["llm_engine"] = {"status": "healthy", "status_code": resp.status_code}
            else:
                dependencies["llm_engine"] = {"status": "degraded", "status_code": resp.status_code}
                all_healthy = False
    except Exception as e:
        logger.error(f"Readiness check failed for LLM engine: {e}", exc_info=True)
        dependencies["llm_engine"] = {"status": "degraded", "error": "Dependency unavailable"}
        all_healthy = False

    # 3. Visual Engine Check
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://127.0.0.1:8188/system_stats")
            if resp.status_code == 200:
                dependencies["visual_engine"] = {"status": "healthy"}
            else:
                dependencies["visual_engine"] = {"status": "degraded", "status_code": resp.status_code}
                all_healthy = False
    except Exception as e:
        logger.error(f"Readiness check failed for Visual engine: {e}", exc_info=True)
        dependencies["visual_engine"] = {"status": "offline", "error": "Dependency unavailable"}
        all_healthy = False

    overall_status = "healthy" if all_healthy else "degraded"
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        content={
            "status": overall_status,
            "timestamp": time.time(),
            "dependencies": dependencies
        },
        status_code=status_code
    )

@router.get("/metrics")
def prometheus_metrics():
    """
    Exposes metrics in standard Prometheus text exposition format.
    """
    lines = [
        "# HELP http_requests_total Total number of HTTP requests processed.",
        "# TYPE http_requests_total counter"
    ]
    for key, val in _REQUEST_COUNTERS.items():
        parts = key.split(":")
        ep = parts[0]
        st = parts[1] if len(parts) > 1 else "200"
        lines.append(f'http_requests_total{{endpoint="{ep}",status="{st}"}} {val}')

    lines.append("# HELP process_uptime_seconds Application uptime in seconds.")
    lines.append("# TYPE process_uptime_seconds gauge")
    lines.append(f'process_uptime_seconds {round(time.time() - _START_TIME, 2)}')

    return Response(content="\n".join(lines) + "\n", media_type="text/plain")
