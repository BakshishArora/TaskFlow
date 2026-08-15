from datetime import date
from uuid import uuid4

import pytest

from taskflow.controllers import project_tasks, projects

OWNER_1 = uuid4()


@pytest.fixture(autouse=True)
def reset_store():
    projects.clear_projects()
    project_tasks.clear_tasks()


@pytest.fixture
def project_id() -> str:
    return projects.create_project("Site", owner_id=OWNER_1).id


def test_create_and_get(project_id):
    t = project_tasks.create_task(project_id, "Build homepage")
    assert isinstance(t.id, str)
    assert t.project_id == project_id
    assert t.status == "todo"
    assert project_tasks.get_task(t.id) == t


def test_create_with_full_fields(project_id):
    t = project_tasks.create_task(
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
        project_tasks.create_task(project_id, "Bad", status="paused")


def test_create_blank_title_raises(project_id):
    with pytest.raises(ValueError):
        project_tasks.create_task(project_id, "   ")


def test_list_filters_by_project(project_id):
    project_tasks.create_task(project_id, "A")
    project_tasks.create_task(project_id, "B")
    other = projects.create_project("Other", owner_id=OWNER_1)
    project_tasks.create_task(other.id, "C")
    assert [t.title for t in project_tasks.list_tasks(project_id)] == ["A", "B"]


def test_get_missing_returns_none():
    assert project_tasks.get_task(str(uuid4())) is None


def test_update_task(project_id):
    t = project_tasks.create_task(project_id, "Old")
    updated = project_tasks.update_task(
        t.id,
        status="done",
        assignee="bob",
        due_date=date(2026, 8, 20),
    )
    assert updated.status == "done"
    assert updated.assignee == "bob"
    assert updated.due_date == date(2026, 8, 20)


def test_update_invalid_status_raises(project_id):
    t = project_tasks.create_task(project_id, "Fine")
    with pytest.raises(ValueError):
        project_tasks.update_task(t.id, status="bogus")


def test_delete_task(project_id):
    t = project_tasks.create_task(project_id, "Gone")
    assert project_tasks.delete_task(t.id) is True
    assert project_tasks.get_task(t.id) is None
