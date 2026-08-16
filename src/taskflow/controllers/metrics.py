from datetime import UTC, datetime

from taskflow.db import SessionLocal
from taskflow.models import Metric as MetricModel


def record_metric(endpoint: str, status_code: int, user_id: str) -> None:
    with SessionLocal() as session:
        row = MetricModel(
            endpoint=endpoint,
            status_code=status_code,
            timestamp=datetime.now(UTC),
            user_id=user_id,
        )
        session.add(row)
        session.commit()


def list_metrics(user_id: str) -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(MetricModel)
            .filter(MetricModel.user_id == user_id)
            .order_by(MetricModel.timestamp, MetricModel.id)
            .all()
        )
        return [_to_dict(row) for row in rows]


def list_all_metrics() -> list[dict]:
    with SessionLocal() as session:
        rows = (
            session.query(MetricModel)
            .order_by(MetricModel.timestamp, MetricModel.id)
            .all()
        )
        return [_to_dict(row) for row in rows]


def _to_dict(row: MetricModel) -> dict:
    return {
        "endpoint": row.endpoint,
        "status_code": row.status_code,
        "timestamp": row.timestamp,
        "user_id": row.user_id,
    }


def list_all() -> list[MetricModel]:
    with SessionLocal() as session:
        return session.query(MetricModel).all()


def clear_metrics() -> None:
    with SessionLocal() as session:
        session.query(MetricModel).delete()
        session.commit()
