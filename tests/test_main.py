from typing import Any, Callable, Generic
from datetime import datetime, timedelta
import re
from locale import setlocale, LC_ALL
from freezegun import freeze_time

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

from bookkeeper.utils import read_tree

@pytest.fixture(scope='session')
def sqlite_configurator(tmp_path_factory):
    conffile = tmp_path_factory.mktemp('tmp') / 'config.ini'
    dbfile = tmp_path_factory.mktemp('tmp') / 'temp.db'
    with open(conffile, 'w') as cf:
        cf.write(f"""
            [BookKeeper]
            desired_view = Qt6View
            budget_warning_threshold = 0.9

            [SqliteRepository]
            db_file = {dbfile}

            [RepositoryFactory]
            desired_repo = SqliteRepository
        """)
    return Configurator([(conffile, 'abs')])

@pytest.fixture(scope='session')
def memory_configurator(tmp_path_factory):
    conffile = tmp_path_factory.mktemp('tmp') / 'config.ini'
    with open(conffile, 'w') as cf:
        cf.write(f"""
            [BookKeeper]
            desired_view = Qt6View
            budget_warning_threshold = 0.9

            [RepositoryFactory]
            desired_repo = MemoryRepository
        """)
    return Configurator([(conffile, 'abs')])

@pytest.fixture(scope='session')
def bad_view_configurator(tmp_path_factory):
    conffile = tmp_path_factory.mktemp('tmp') / 'config.ini'
    with open(conffile, 'w') as cf:
        cf.write(f"""
            [BookKeeper]
            desired_view = AbsentView
            budget_warning_threshold = 0.9

            [RepositoryFactory]
            desired_repo = MemoryRepository
        """)
    return Configurator([(conffile, 'abs')])

@pytest.fixture(scope='session')
def bad_thresh_configurator(tmp_path_factory):
    conffile = tmp_path_factory.mktemp('tmp') / 'config.ini'
    with open(conffile, 'w') as cf:
        cf.write(f"""
            [BookKeeper]
            desired_view = Qt6View
            budget_warning_threshold = 1.1

            [RepositoryFactory]
            desired_repo = MemoryRepository
        """)
    return Configurator([(conffile, 'abs')])

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

    def test__round_to_sec(self, cat_repo, exp_repo, bud_repo):
        conv = EntriesConverter(exp_repo, cat_repo, bud_repo)
        dt = datetime(1970, 1, 1, 1, 1, 1, 499999)
        assert(conv._round_to_sec(dt)) == datetime(1970, 1, 1, 1, 1, 1, 0)
        dt = datetime(1970, 1, 1, 1, 1, 1, 500000)
        assert(conv._round_to_sec(dt)) == datetime(1970, 1, 1, 1, 1, 2, 0)

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
        period = datetime(1970, 12, 30).strftime('%x') + '-' + datetime(1970, 12, 30).strftime('%x')
        assert(conv.budget_to_entry(b, 100)) == BudgetEntry(period, '1.0', '1.0', '-')
        pk = cat_repo.add(Category())
        b = Budget(100, datetime(1970, 12, 30), datetime(1970, 12, 30), constants.BUDGET_DAILY, pk)
        assert(conv.budget_to_entry(b, 100)) == BudgetEntry(constants.BUDGET_DAILY, '1.0', '1.0', 'Category')

    @freeze_time('2024-03-15')
    def test_entry_to_expense(self, cat_repo, exp_repo, bud_repo):
        conv = EntriesConverter(exp_repo, cat_repo, bud_repo)
        e = ExpenseEntry('1970-01-01 00:00:00', '1.0', '-', 'comment')
        assert(conv.entry_to_expense(e)) == Expense(expense_date=datetime(1970, 1, 1),
                                                    added_date=datetime.now(),
                                                    cost=100, comment='comment')
        e = ExpenseEntry('1970-1-1 00:00:00', '1.0', '-', 'comment')
        assert(conv.entry_to_expense(e)) == Expense(expense_date=datetime(1970, 1, 1),
                                                    added_date=datetime(2024, 3, 15),
                                                    cost=100, comment='comment')
        e = ExpenseEntry('1970-1-1 00:00:00', '1,01', '-', 'comment')
        assert(conv.entry_to_expense(e)) == Expense(expense_date=datetime(1970, 1, 1),
                                                    added_date=datetime(2024, 3, 15),
                                                    cost=101, comment='comment')
        e = ExpenseEntry('1970-1-1 00:00:00', '1', '-', 'comment')
        assert(conv.entry_to_expense(e)) == Expense(expense_date=datetime(1970, 1, 1),
                                                    added_date=datetime(2024, 3, 15),
                                                    cost=100, comment='comment')
        e = ExpenseEntry('1970-1-1', '1.0', '-', 'comment')
        with pytest.raises(ViewError):
            conv.entry_to_expense(e)
        e = ExpenseEntry('1970-1-1 00:00:00', '1.001', '-', 'comment')
        with pytest.raises(ViewError):
            conv.entry_to_expense(e)
        e = ExpenseEntry('1970-1-1 00:00:00', '-1.0', '-', 'comment')
        with pytest.raises(ViewError):
            conv.entry_to_expense(e)
        e = ExpenseEntry('1970-1-1 00:00:00', '1.0', 'Absent', 'comment')
        with pytest.raises(ViewError):
            conv.entry_to_expense(e)
        c = Category()
        pk = cat_repo.add(c)
        e = ExpenseEntry('1970-1-1 00:00:00', '1.0', 'Category', 'comment')
        assert(conv.entry_to_expense(e)) == Expense(expense_date=datetime(1970, 1, 1),
                                                    added_date=datetime(2024, 3, 15),
                                                    cost=100, comment='comment', category=pk)
        c1 = Category(parent=pk)
        cat_repo.add(c1)
        with pytest.raises(ViewError):
            conv.entry_to_expense(e)

    @freeze_time('2024-03-15')
    def test_entry_to_budget(self, cat_repo, exp_repo, bud_repo):
        """ cost, category conversions and budget type are already tested """
        conv = EntriesConverter(exp_repo, cat_repo, bud_repo)
        setlocale(LC_ALL, '')
        b = BudgetEntry(period=constants.BUDGET_DAILY, category=constants.TOP_CATEGORY_NAME,
                        cost_limit='0')
        #period = datetime.now().strftime('%x') + '-' + datetime.now().strftime('%x')
        assert(conv.entry_to_budget(b)) == Budget(budget_type=constants.BUDGET_DAILY)

    def test_entry_to_category(self, cat_repo, exp_repo, bud_repo):
        conv = EntriesConverter(exp_repo, cat_repo, bud_repo)
        with pytest.raises(ViewError):
            conv.entry_to_category(CategoryEntry(category=''))
        with pytest.raises(ViewError):
            conv.entry_to_category(CategoryEntry(category=constants.TOP_CATEGORY_NAME))
        c = CategoryEntry('Category', '-')
        assert(conv.entry_to_category(c)) == Category()
        p = Category('Parent')
        cat_repo.add(p)
        c = CategoryEntry('Category', 'Parent')
        assert(conv.entry_to_category(c)) == Category(parent=p.pk)


class TestBookKeeper:

    @pytest.mark.parametrize('custom_configurator', ['sqlite_configurator', 'memory_configurator'])
    def test_can_create(self, request, custom_configurator, monkeypatch):
        custom_configurator = request.getfixturevalue(custom_configurator)
        monkeypatch.setattr(Configurator, 'config_files', custom_configurator.config_files)
        bookkeeper = BookKeeper()
        bookkeeper._view.app.shutdown()

    def test_bad_view_config(self, bad_view_configurator, monkeypatch):
        custom_configurator = bad_view_configurator
        monkeypatch.setattr(Configurator, 'config_files', custom_configurator.config_files)
        with pytest.raises(ValueError):
            bookkeeper = BookKeeper()

    def test_bad_thresh_config(self, bad_thresh_configurator, monkeypatch):
        custom_configurator = bad_thresh_configurator
        monkeypatch.setattr(Configurator, 'config_files', custom_configurator.config_files)
        with pytest.raises(ValueError):
            bookkeeper = BookKeeper()

    # freeze_time breaks typing detection in sqlite repo.abs
    @freeze_time('2024-03-15')
    @pytest.mark.parametrize('custom_configurator', ['memory_configurator'])
    def test_expense_add_delete_edit(self, request, custom_configurator, monkeypatch):
        custom_configurator = request.getfixturevalue(custom_configurator)
        monkeypatch.setattr(Configurator, 'config_files', custom_configurator.config_files)
        bookkeeper = BookKeeper()
        bookkeeper._cb_add_expense(ExpenseEntry('1970-1-1 00:00:00', '1.0', '-'))
        # by far adding expense with custom date is unsupported
        assert Expense(100, None, comment="Comment", added_date=datetime.now(), expense_date=datetime.now()) in bookkeeper._exp_viewed
        assert Expense(100, None, comment="Comment", added_date=datetime.now(), expense_date=datetime.now()) in bookkeeper._exp_repo.get_all()
        bookkeeper._cb_delete_expense([0])
        assert len(bookkeeper._exp_viewed) == 0
        assert len(bookkeeper._exp_repo.get_all()) == 0
        bookkeeper._cb_add_expense(ExpenseEntry('1970-1-1 00:00:00', '1.0', '-'))
        bookkeeper._cb_edited_expense(0, ExpenseEntry('1970-1-1 00:00:00', '10.0', '-'))
        assert Expense(1000, None, comment="Comment", added_date=datetime.now(), expense_date=datetime(1970, 1, 1)) in bookkeeper._exp_viewed
        assert Expense(1000, None, comment="Comment", added_date=datetime.now(), expense_date=datetime(1970, 1, 1)) in bookkeeper._exp_repo.get_all()
        with pytest.raises(ViewError):
            bookkeeper._cb_edited_expense(0, ExpenseEntry('1970-1-1 wrong', '-10.0', '-'))
        # no changes should be made
        assert Expense(1000, None, comment="Comment", added_date=datetime.now(), expense_date=datetime(1970, 1, 1)) in bookkeeper._exp_viewed
        assert Expense(1000, None, comment="Comment", added_date=datetime.now(), expense_date=datetime(1970, 1, 1)) in bookkeeper._exp_repo.get_all()
        bookkeeper._view.app.shutdown()

    @pytest.mark.parametrize('custom_configurator', ['sqlite_configurator', 'memory_configurator'])
    def test_budget_edit(self, request, custom_configurator, monkeypatch):
        custom_configurator = request.getfixturevalue(custom_configurator)
        monkeypatch.setattr(Configurator, 'config_files', custom_configurator.config_files)
        bookkeeper = BookKeeper()
        bookkeeper._cb_add_expense(ExpenseEntry('1970-1-1 00:00:00', '110', '-'))
        bookkeeper._cb_edited_budget(0, BudgetEntry(constants.BUDGET_DAILY, '100', '0', '-'))
        assert Budget(10000, budget_type=constants.BUDGET_DAILY) in bookkeeper._bud_viewed
        assert Budget(10000, budget_type=constants.BUDGET_DAILY) in bookkeeper._bud_repo.get_all()
        with pytest.raises(ViewError):
            bookkeeper._cb_edited_budget(0, BudgetEntry(constants.BUDGET_DAILY, '-100', '0', '-'))
        # no changes should be made
        assert Budget(10000, budget_type=constants.BUDGET_DAILY) in bookkeeper._bud_viewed
        assert Budget(10000, budget_type=constants.BUDGET_DAILY) in bookkeeper._bud_repo.get_all()
        bookkeeper._view.app.shutdown()

    @pytest.mark.parametrize('custom_configurator', ['sqlite_configurator', 'memory_configurator'])
    def test_category_add_delete_edit(self, request, custom_configurator, monkeypatch):
        custom_configurator = request.getfixturevalue(custom_configurator)
        monkeypatch.setattr(Configurator, 'config_files', custom_configurator.config_files)
        bookkeeper = BookKeeper()
        bookkeeper._cb_add_category(CategoryEntry('Category', '-'))
        assert Category('Category') in bookkeeper._cat_viewed
        assert Category('Category') in bookkeeper._cat_repo.get_all()
        # add with dup name
        with pytest.raises(ViewError):
            bookkeeper._cb_add_category(CategoryEntry('Category', 'Category'))
        bookkeeper._cb_add_category(CategoryEntry('Child', 'Category'))
        with pytest.raises(NotImplementedError):
            bookkeeper._cb_delete_category([0, 1])
        bookkeeper._cb_add_expense(ExpenseEntry('1970-1-1 00:00:00', '1.0', 'Child'))
        bookkeeper._cb_edited_budget(0, BudgetEntry(constants.BUDGET_DAILY, '100', '0', 'Child'))
        bookkeeper._cb_delete_category([0])
        assert len(bookkeeper._cat_viewed) == 0
        assert len(bookkeeper._cat_repo.get_all()) == 0
        assert bookkeeper._exp_repo.get_all()[0].category == None
        assert bookkeeper._bud_repo.get_all()[0].category == None
        bookkeeper._cb_add_category(CategoryEntry('Category', '-'))
        bookkeeper._cb_add_category(CategoryEntry('Child', 'Category'))
        with pytest.raises(ViewError):
            bookkeeper._cb_edited_category(1, CategoryEntry('Category', 'Category'))
        assert Category('Child', bookkeeper._cat_viewed[0].pk) in bookkeeper._cat_viewed
        assert Category('Child', bookkeeper._cat_viewed[0].pk) in bookkeeper._cat_repo.get_all()
        bookkeeper._cb_edited_category(1, CategoryEntry('NewChild', 'Category'))
        assert Category('NewChild', bookkeeper._cat_viewed[0].pk) in bookkeeper._cat_viewed
        assert Category('NewChild', bookkeeper._cat_viewed[0].pk) in bookkeeper._cat_repo.get_all()
        bookkeeper._view.app.shutdown()