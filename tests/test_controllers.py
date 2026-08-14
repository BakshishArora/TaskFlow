import pytest

from taskflow.controllers import tasks


@pytest.fixture(autouse=True)
def reset_store():
    tasks.clear_tasks()


def test_create_and_get():
    t = tasks.create_task("Buy groceries", "milk, eggs")
    assert t.id == 1
    assert t.title == "Buy groceries"
    assert tasks.get_task(t.id) == t


def test_list_tasks():
    tasks.create_task("First")
    tasks.create_task("Second")
    assert [t.title for t in tasks.list_tasks()] == ["First", "Second"]


def test_create_blank_title_raises():
    with pytest.raises(ValueError):
        tasks.create_task("   ")


def test_get_missing_returns_none():
    assert tasks.get_task(999) is None


def test_update_task():
    t = tasks.create_task("Old")
    updated = tasks.update_task(t.id, title="New", completed=True)
    assert updated.title == "New"
    assert updated.completed is True


def test_update_blank_title_raises():
    t = tasks.create_task("Fine")
    with pytest.raises(ValueError):
        tasks.update_task(t.id, title="")


def test_update_missing_returns_none():
    assert tasks.update_task(999, title="X") is None


def test_delete_task():
    t = tasks.create_task("Gone")
    assert tasks.delete_task(t.id) is True
    assert tasks.get_task(t.id) is None


def test_delete_missing_returns_false():
    assert tasks.delete_task(999) is False