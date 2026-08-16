from fastapi import APIRouter

from taskflow.controllers import metrics

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics")
def list_metrics() -> list[dict]:
    return metrics.list_all_metrics()
