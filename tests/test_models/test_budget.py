from datetime import datetime

import pytest

from bookkeeper.repository.memory_repository import MemoryRepository
from bookkeeper.models.budget import Budget


@pytest.fixture
def repo():
    return MemoryRepository()

@pytest.fixture
def datetime1():
    return datetime(1970, 1, 1)

@pytest.fixture
def datetime2():
    return datetime(1970, 1, 2)

def test_create_with_full_args_list(datetime1, datetime2):
    e = Budget(cost_limit=100, category=1, period=(datetime2 - datetime1), pk=1)
    assert e.cost_limit == 100
    assert e.category == 1
    assert e.pk == 1
    assert e.period == datetime2-datetime1


def test_create_brief(datetime1, datetime2):
    e = Budget(100, datetime2 - datetime1)
    assert e.cost_limit == 100
    assert e.category == None
    assert e.period == datetime2 - datetime1


def test_can_add_to_repo(repo, datetime1, datetime2):
    e = Budget(100, datetime2 - datetime1, 1)
    pk = repo.add(e)
    assert e.pk == pk
