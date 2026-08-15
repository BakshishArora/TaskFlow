from uuid import uuid4

import pytest

from taskflow.controllers import projects

OWNER_1 = uuid4()
OWNER_2 = uuid4()


@pytest.fixture(autouse=True)
def reset_store():
    projects.clear_projects()


def test_create_and_get():
    p = projects.create_project("Website", owner_id=OWNER_1)
    assert isinstance(p.id, str)
    assert p.owner_id == OWNER_1
    assert projects.get_project(p.id) == p


def test_create_validates_name():
    with pytest.raises(ValueError):
        projects.create_project("  ", owner_id=OWNER_1)


def test_get_missing_returns_none():
    assert projects.get_project(str(uuid4())) is None


def test_list_projects_filters_by_owner():
    projects.create_project("Mine", owner_id=OWNER_1)
    projects.create_project("Yours", owner_id=OWNER_2)
    assert [p.name for p in projects.list_projects(owner_id=OWNER_1)] == ["Mine"]


def test_clear_projects_empties_store():
    p = projects.create_project("One", owner_id=OWNER_1)
    projects.clear_projects()
    assert projects.get_project(p.id) is None
