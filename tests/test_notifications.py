from datetime import date
from uuid import uuid4

import pytest

from taskflow.controllers import projects, tasks, users
from taskflow.controllers.notifications import (
    create_status_change_notifications,
    list_notifications_for_user,
)
from taskflow.db import SessionLocal
from taskflow.models import Notification as NotificationModel

OWNER = uuid4()


@pytest.fixture(autouse=True)
def reset_store():
    with SessionLocal() as session:
        session.query(NotificationModel).delete()
        session.commit()
    projects.clear_projects()
    tasks.clear_tasks()
    users.clear_users()


@pytest.fixture
def project_id() -> str:
    return projects.create_project("Site", owner_id=OWNER).id


def test_status_change_notifies_owner_and_assignee(project_id):
    alice = users.create_user("alice", "password")
    t = tasks.create_task(
        project_id, "Ship", assignee="alice", due_date=date(2026, 9, 1)
    )
    tasks.update_task(t.id, status="done")

    owner_rows = list_notifications_for_user(str(OWNER))
    assignee_rows = list_notifications_for_user(alice.id)
    assert len(owner_rows) == 1
    assert len(assignee_rows) == 1
    assert owner_rows[0].user_id == str(OWNER)
    assert assignee_rows[0].user_id == alice.id
    assert owner_rows[0].task_id == t.id
    assert "done" in owner_rows[0].message
    assert owner_rows[0].read is False
    assert owner_rows[0].created_at is not None


def test_no_notification_when_status_unchanged(project_id):
    t = tasks.create_task(project_id, "Ship", due_date=date(2026, 9, 1))
    tasks.update_task(t.id, status="todo")
    assert list_notifications_for_user(str(OWNER)) == []


def test_no_notification_on_due_date_only_update(project_id):
    t = tasks.create_task(project_id, "Ship", due_date=date(2026, 9, 1))
    tasks.update_task(t.id, due_date=date(2026, 10, 1))
    assert list_notifications_for_user(str(OWNER)) == []


def test_unknown_assignee_gets_no_notification(project_id):
    t = tasks.create_task(
        project_id, "Ship", assignee="ghost", due_date=date(2026, 9, 1)
    )
    tasks.update_task(t.id, status="done")
    assert len(list_notifications_for_user(str(OWNER))) == 1
    assert list_notifications_for_user("ghost") == []


def test_owner_and_assignee_same_deduped(project_id):
    t = tasks.create_task(
        project_id, "Ship", assignee=str(OWNER), due_date=date(2026, 9, 1)
    )
    tasks.update_task(t.id, status="in_progress")
    assert len(list_notifications_for_user(str(OWNER))) == 1


def test_create_notifications_missing_task_returns_zero():
    assert create_status_change_notifications("missing", "todo", "done") == 0