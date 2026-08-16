import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://root:1234@localhost:5432/taskdb_test"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

import pytest
from redis import Redis
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

import taskflow.models  # noqa: F401
from taskflow.db import Base, engine

_TEST_DB_NAME = make_url(os.environ["DATABASE_URL"]).database


def _ensure_test_database() -> None:
    admin_url = make_url(os.environ["DATABASE_URL"]).set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": _TEST_DB_NAME},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{_TEST_DB_NAME}"'))
    admin_engine.dispose()


_ensure_test_database()
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def flush_redis():
    Redis.from_url("redis://localhost:6379/0").flushdb()
