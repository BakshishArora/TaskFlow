from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from taskflow.controllers import projects, tasks

OWNER_1 = uuid4()

FUTURE_DATE = datetime.now(UTC).date() + timedelta(days=30)


@pytest.fixture(autouse=True)
def reset_store():
    projects.clear_projects()
    tasks.clear_tasks()


@pytest.fixture
def project_id() -> str:
    return projects.create_project("Site", owner_id=OWNER_1).id


def test_create_and_get(project_id):
    t = tasks.create_task(project_id, "Build homepage", due_date=date(2026, 9, 1))
    assert isinstance(t.id, str)
    assert t.project_id == project_id
    assert t.status == "todo"
    assert tasks.get_task(t.id) == t


def test_create_requires_due_date(project_id):
    with pytest.raises(ValueError):
        tasks.create_task(project_id, "No date")


def test_create_with_full_fields(project_id):
    t = tasks.create_task(
        project_id,
        "Ship",
        status="in_progress",
        assignee="alice",
        due_date=date(2026, 9, 1),
        description="details",
    )
    assert t.status == "in_progress"
    assert t.assignee == "alice"
    assert t.due_date == date(2026, 9, 1)
    assert t.description == "details"


def test_create_invalid_status_raises(project_id):
    with pytest.raises(ValueError):
        tasks.create_task(project_id, "Bad", status="paused", due_date=date(2026, 9, 1))


def test_create_blank_title_raises(project_id):
    with pytest.raises(ValueError):
        tasks.create_task(project_id, "   ", due_date=date(2026, 9, 1))


def test_list_filters_by_project(project_id):
    tasks.create_task(project_id, "A", due_date=date(2026, 9, 1))
    tasks.create_task(project_id, "B", due_date=date(2026, 9, 1))
    other = projects.create_project("Other", owner_id=OWNER_1)
    tasks.create_task(other.id, "C", due_date=date(2026, 9, 1))
    page = tasks.list_tasks(project_id)
    assert sorted(t.title for t in page.items) == ["A", "B"]
    assert page.total == 2


def test_list_filters_by_status(project_id):
    done = tasks.create_task(project_id, "Done", due_date=FUTURE_DATE)
    tasks.update_task(done.id, status="done", due_date=FUTURE_DATE)
    tasks.create_task(project_id, "Todo", due_date=date(2026, 9, 1))
    page = tasks.list_tasks(project_id, status="done")
    assert [t.title for t in page.items] == ["Done"]
    assert page.total == 1


def test_list_filters_by_assignee(project_id):
    tasks.create_task(project_id, "Mine", assignee="alice", due_date=date(2026, 9, 1))
    tasks.create_task(project_id, "Yours", assignee="bob", due_date=date(2026, 9, 1))
    tasks.create_task(project_id, "Nobody", due_date=date(2026, 9, 1))
    page = tasks.list_tasks(project_id, assignee="alice")
    assert [t.title for t in page.items] == ["Mine"]


def test_list_empty_assignee_ignored(project_id):
    tasks.create_task(project_id, "Mine", assignee="alice", due_date=date(2026, 9, 1))
    page = tasks.list_tasks(project_id, assignee="")
    assert [t.title for t in page.items] == ["Mine"]


def test_list_filters_by_due_date_range(project_id):
    tasks.create_task(project_id, "Aug", due_date=date(2026, 8, 15))
    tasks.create_task(project_id, "Sep", due_date=date(2026, 9, 1))
    tasks.create_task(project_id, "Oct", due_date=date(2026, 10, 1))
    page = tasks.list_tasks(project_id, due_from=date(2026, 9, 1), due_to=date(2026, 10, 1))
    assert [t.title for t in page.items] == ["Sep", "Oct"]
    assert page.total == 2


def test_list_filters_combine(project_id):
    done = tasks.create_task(
        project_id, "Done alice", assignee="alice", due_date=FUTURE_DATE
    )
    tasks.update_task(done.id, status="done", due_date=FUTURE_DATE)
    tasks.create_task(project_id, "Todo alice", assignee="alice", due_date=FUTURE_DATE)
    page = tasks.list_tasks(project_id, status="done", assignee="alice")
    assert [t.title for t in page.items] == ["Done alice"]


def test_list_orders_by_due_date_then_id(project_id):
    tasks.create_task(project_id, "Late", due_date=date(2026, 10, 1))
    tasks.create_task(project_id, "Early", due_date=date(2026, 8, 15))
    tasks.create_task(project_id, "Mid", due_date=date(2026, 9, 1))
    page = tasks.list_tasks(project_id)
    assert [t.title for t in page.items] == ["Early", "Mid", "Late"]


def test_list_paginates(project_id):
    for title in ["A", "B", "C", "D", "E"]:
        tasks.create_task(project_id, title, due_date=date(2026, 9, 1))
    seen = []
    for page in (1, 2, 3):
        result = tasks.list_tasks(project_id, page=page, page_size=2)
        seen.extend(t.title for t in result.items)
    assert sorted(seen) == ["A", "B", "C", "D", "E"]
    assert len(seen) == len(set(seen))
    first = tasks.list_tasks(project_id, page=2, page_size=2)
    assert first.total == 5
    assert first.page == 2
    assert first.page_size == 2
    assert len(first.items) == 2


def test_get_missing_returns_none():
    assert tasks.get_task(str(uuid4())) is None


def test_update_task(project_id):
    t = tasks.create_task(project_id, "Old", due_date=FUTURE_DATE)
    updated = tasks.update_task(
        t.id,
        status="done",
        assignee="bob",
        due_date=FUTURE_DATE,
    )
    assert updated.status == "done"
    assert updated.assignee == "bob"
    assert updated.due_date == FUTURE_DATE


def test_update_task_assignee(project_id):
    t = tasks.create_task(project_id, "Old", due_date=date(2026, 9, 1))
    updated = tasks.update_task(t.id, assignee="bob")
    assert updated.assignee == "bob"
    assert tasks.get_task(t.id).assignee == "bob"


def test_update_task_clear_assignee(project_id):
    t = tasks.create_task(project_id, "Old", assignee="alice", due_date=date(2026, 9, 1))
    updated = tasks.update_task(t.id, assignee=None)
    assert updated.assignee is None
    assert tasks.get_task(t.id).assignee is None


def test_update_task_omit_assignee_unchanged(project_id):
    t = tasks.create_task(project_id, "Old", assignee="alice", due_date=date(2026, 9, 1))
    updated = tasks.update_task(t.id, status="done")
    assert updated.assignee == "alice"


def test_update_invalid_status_raises(project_id):
    t = tasks.create_task(project_id, "Fine", due_date=date(2026, 9, 1))
    with pytest.raises(ValueError):
        tasks.update_task(t.id, status="bogus")


def test_update_expired_due_date_raises(project_id):
    t = tasks.create_task(project_id, "Fine", due_date=date(2026, 9, 1))
    past = datetime.now(UTC).date() - timedelta(days=1)
    with pytest.raises(ValueError, match="already expired"):
        tasks.update_task(t.id, due_date=past)


def test_delete_task(project_id):
    t = tasks.create_task(project_id, "Gone", due_date=date(2026, 9, 1))
    assert tasks.delete_task(t.id) is not None
    assert tasks.get_task(t.id) is None
