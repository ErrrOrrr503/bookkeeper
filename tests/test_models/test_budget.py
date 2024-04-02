from datetime import datetime

import pytest

from freezegun import freeze_time

from bookkeeper.repository.memory_repository import MemoryRepository
from bookkeeper.models.budget import Budget
from bookkeeper.models.category import Category
from bookkeeper.config import constants

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
    e = Budget(cost_limit=100, start=datetime1, end=datetime2, budget_type='', category=1, pk=1)
    assert e.cost_limit == 100
    assert e.category == 1
    assert e.pk == 1
    assert e.start == datetime1
    assert e.end == datetime2
    assert e.budget_type == ''

def test_create_brief(datetime1, datetime2):
    e = Budget(100)
    assert e.cost_limit == 100
    assert e.category == None
    assert e.pk == 0
    assert e.budget_type == ''

def test_eq():
    e1 = Budget(cost_limit=100, start=datetime1, end=datetime2, budget_type='', category=1, pk=1)
    e2 = Budget(cost_limit=100, start=datetime1, end=datetime2, budget_type='', category=1, pk=1)
    assert e1 == e2
    with pytest.raises(NotImplementedError):
        e1 == 42

def test_can_add_to_repo(repo, datetime1, datetime2):
    e = Budget(100)
    pk = repo.add(e)
    assert e.pk == pk
    assert repo.get(pk) == e

@freeze_time('2024-03-15')
def test_special_types_ordinary():
    dtn = datetime.now()
    dison = dtn.isocalendar()
    e = Budget(budget_type=constants.BUDGET_DAILY)
    assert e.start == datetime(dtn.year, dtn.month, dtn.day)
    assert e.end == datetime(dtn.year, dtn.month, dtn.day + 1)
    e = Budget(budget_type=constants.BUDGET_WEEKLY)
    assert e.start == datetime.fromisocalendar(dison.year, dison.week, 1)
    assert e.end == datetime.fromisocalendar(dison.year, dison.week + 1, 1)
    e = Budget(budget_type=constants.BUDGET_MONTHLY)
    assert e.start == datetime(dtn.year, dtn.month, 1)
    assert e.end == datetime(dtn.year, dtn.month + 1, 1)

@freeze_time('2024-03-31')
def test_special_types_month_edge():
    dtn = datetime.now()
    dison = dtn.isocalendar()
    e = Budget(budget_type=constants.BUDGET_DAILY)
    assert e.start == datetime(dtn.year, dtn.month, dtn.day)
    assert e.end == datetime(dtn.year, dtn.month + 1, 1)
    e.set_type(constants.BUDGET_WEEKLY)
    assert e.start == datetime.fromisocalendar(dison.year, dison.week, 1)
    assert e.end == datetime.fromisocalendar(dison.year, dison.week + 1, 1)
    e = Budget(budget_type=constants.BUDGET_MONTHLY)
    assert e.start == datetime(dtn.year, dtn.month, 1)
    assert e.end == datetime(dtn.year, dtn.month + 1, 1)

@freeze_time('2024-12-25')
def test_special_types_year_edge():
    dtn = datetime.now()
    dison = dtn.isocalendar()
    e = Budget(budget_type=constants.BUDGET_DAILY)
    assert e.start == datetime(dtn.year, dtn.month, dtn.day)
    assert e.end == datetime(dtn.year, dtn.month, dtn.day + 1)
    e = Budget(budget_type=constants.BUDGET_WEEKLY)
    assert e.start == datetime.fromisocalendar(dison.year, dison.week, 1)
    assert e.end == datetime.fromisocalendar(dison.year + 1, 1, 1)
    e.set_type(constants.BUDGET_MONTHLY)
    assert e.start == datetime(dtn.year, dtn.month, 1)
    assert e.end == datetime(dtn.year + 1, 1, 1)

@freeze_time('2024-12-31')
def test_special_types_month_year_edge():
    dtn = datetime.now()
    dison = dtn.isocalendar()
    e = Budget(budget_type=constants.BUDGET_DAILY)
    assert e.start == datetime(dtn.year, dtn.month, dtn.day)
    assert e.end == datetime(dtn.year + 1, 1, 1)
    e = Budget(budget_type=constants.BUDGET_WEEKLY)
    # 31st is already 2025's first week by iso calendar
    assert e.start == datetime.fromisocalendar(dison.year, dison.week, 1)
    assert e.end == datetime.fromisocalendar(dison.year, dison.week + 1, 1)
    e = Budget(budget_type=constants.BUDGET_MONTHLY)
    assert e.start == datetime(dtn.year, dtn.month, 1)
    assert e.end == datetime(dtn.year + 1, 1, 1)

def test_special_types_bad_type():
    with pytest.raises(NotImplementedError):
        e = Budget(budget_type='owejowegojtuirgreearrgn')

def test_get_category(repo):
    e = Budget()
    assert e.get_category(repo) == None
    c = Category()
    pk = repo.add(c)
    e.category = pk
    assert e.get_category(repo) == c