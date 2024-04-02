from typing import Any, Callable, Generic
from datetime import datetime, timedelta
import re
from locale import setlocale, LC_ALL

import pytest

from bookkeeper.models.budget import Budget
from bookkeeper.models.category import Category
from bookkeeper.models.expense import Expense

from bookkeeper.config.configurator import Configurator

from bookkeeper.view.abstract_view import ExpenseEntry, CategoryEntry, BudgetEntry
from bookkeeper.view.abstract_view import AbstractView
from bookkeeper.view.abstract_view import ViewError, ViewWarning
from bookkeeper.view.qt6_view import Qt6View

from bookkeeper.repository.abstract_repository import AbstractRepository
from bookkeeper.repository.repository_factory import RepositoryFactory
from bookkeeper.repository.memory_repository import MemoryRepository

from bookkeeper.config import constants

from bookkeeper.main import EntriesConverter, BookKeeper

@pytest.fixture
def cat_repo():
    return MemoryRepository()

@pytest.fixture
def bud_repo():
    return MemoryRepository()

@pytest.fixture
def exp_repo():
    return MemoryRepository()

class TestEntriesConverter():

    def test_expense_to_entry(self, cat_repo, exp_repo, bud_repo):
        conv = EntriesConverter(exp_repo, cat_repo, bud_repo)
        e = Expense(100, None, datetime(1970, 1, 1), datetime(1970, 1, 1), 'comment', 0)
        assert(conv.expense_to_entry(e)) == ExpenseEntry('1970-01-01 00:00:00', '1.0', '-', 'comment')
        cat = Category()
        pk = cat_repo.add(cat)
        e.category = pk
        assert(conv.expense_to_entry(e)) == ExpenseEntry('1970-01-01 00:00:00', '1.0', 'Category', 'comment')

    def test_category_to_entry(self, cat_repo, exp_repo, bud_repo):
        conv = EntriesConverter(exp_repo, cat_repo, bud_repo)
        c = Category()
        assert(conv.category_to_entry(c)) == CategoryEntry('Category', '-')
        ppk = cat_repo.add(Category('Top'))
        c = Category(parent=ppk)
        assert(conv.category_to_entry(c)) == CategoryEntry('Category', 'Top')

    def test_budget_to_entry(self, cat_repo, exp_repo, bud_repo):
        setlocale(LC_ALL, '')
        conv = EntriesConverter(exp_repo, cat_repo, bud_repo)
        b = Budget(100, datetime(1970, 12, 30), datetime(1970, 12, 30))
        assert(conv.budget_to_entry(b, 100)) == BudgetEntry('30.12.1970-30.12.1970', '1.0', '1.0', '-')
        pk = cat_repo.add(Category())
        b = Budget(100, datetime(1970, 12, 30), datetime(1970, 12, 30), constants.BUDGET_DAILY, pk)
        assert(conv.budget_to_entry(b, 100)) == BudgetEntry(constants.BUDGET_DAILY, '1.0', '1.0', 'Category')
