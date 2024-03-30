"""
Bookkeeper logic, in fact presenter
"""
from typing import Any, Callable
from datetime import datetime, timedelta
import re

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

from bookkeeper.config import constants

class EntriesConverter:
    """
    Converter between models and view entries.
    Should include only converting logic (no calculations).
    """
    def __init__(self, expense_repo: AbstractRepository[Expense],
                       category_repo: AbstractRepository[Category],
                       budget_repo: AbstractRepository[Budget]):
        self._exp_repo = expense_repo
        self._cat_repo = category_repo
        self._bud_repo = budget_repo

    def _round_to_sec(self, dt: datetime) -> datetime:
        if dt.microsecond >= 500000:
            dt += timedelta(seconds=1)
        return dt.replace(microsecond=0)

    def _cost_str_to_int(self, cost_str: str) -> int:
        if re.fullmatch('(\d+)([,\.]\d\d?)?', cost_str) is None:
            raise ViewError(f'Wrong cost value: {cost_str}')
        s = cost_str.replace('.', '')
        s = s.replace(',', '')
        return int(s)  # no exception here possible due to strict re

    def expense_to_entry(self, expense: Expense) -> ExpenseEntry:
        e = ExpenseEntry()
        cat = None
        if expense.category is not None:
            cat = self._cat_repo.get(expense.category)
        cat_name = cat.name if cat is not None else constants.TOP_CATEGORY_NAME
        e.category = cat_name
        e.comment = expense.comment
        e.cost = str(expense.cost / 100)
        e.date = str(self._round_to_sec(expense.expense_date))
        return e

    def category_to_entry(self, category: Category) -> CategoryEntry:
        c = CategoryEntry()
        c.category = category.name
        parent = category.get_parent(self._cat_repo)
        c.parent = parent.name if parent is not None else constants.TOP_CATEGORY_NAME
        return c

    def budget_to_entry(self, budget: Budget, spent: int) -> BudgetEntry:
        b = BudgetEntry()
        category = budget.get_category(self._cat_repo)
        b.category = constants.TOP_CATEGORY_NAME
        if category is not None:
            b.category = category.name
        b.cost_limit = str(budget.cost_limit / 100)
        b.spent = str(spent / 100)
        if budget.budget_type == constants.BUDGET_DAILY:
            b.period = constants.BUDGET_DAILY
        elif budget.budget_type == constants.BUDGET_WEEKLY:
            b.period = constants.BUDGET_WEEKLY
        elif budget.budget_type == constants.BUDGET_MONTHLY:
            b.period = constants.BUDGET_MONTHLY
        else:
            b.period = str(budget.period)
        return b

    def entry_to_expense(self, entry: ExpenseEntry) -> Expense:
        e = Expense()
        if entry.category != constants.TOP_CATEGORY_NAME:
            cats = self._cat_repo.get_all(where={ 'name': entry.category })
            if len(cats) == 0:
                raise ViewError(f'No category {entry.category} present.')
            elif len(cats) > 1:
                raise ViewError(f'Multiple categories {entry.category} present. '
                                 'Repo seems to be corrupted.')
            e.category = cats[0].pk
        e.comment = entry.comment
        e.cost = self._cost_str_to_int(entry.cost)
        return e


class BookKeeper:
    """
    Presenter, that contains logic
    """
    _repo_factory: RepositoryFactory
    _cat_repo: AbstractRepository[Category]
    _bud_repo: AbstractRepository[Budget]
    _exp_repo: AbstractRepository[Expense]

    _view: AbstractView

    _entries_converter: EntriesConverter

    _top_cat: Category

    def __init__(self):
        self._repo_factory = RepositoryFactory()
        self._cat_repo = self._repo_factory.repo_for(Category)
        self._bud_repo = self._repo_factory.repo_for(Budget)
        self._exp_repo = self._repo_factory.repo_for(Expense)
        self._entries_converter = EntriesConverter(self._exp_repo,
                                                   self._cat_repo,
                                                   self._bud_repo)
        self._init_budgets()
        self._view = Qt6View()


    def start(self) -> None:
        """ the only public entity in presenter """
        self._view.start()

    def _init_budgets(self) -> None:
        """ Create budgets if none. """
        if len(self._bud_repo.get_all()) == 0:
            self._bud_repo.add(Budget(budget_type=constants.BUDGET_DAILY))
            self._bud_repo.add(Budget(budget_type=constants.BUDGET_WEEKLY))
            self._bud_repo.add(Budget(budget_type=constants.BUDGET_MONTHLY))
        self._update_budget_periods()

    def _update_budget_periods(self) -> None:
        """ Update starts and periods, days, weeks and months tend to pass. """
        dt_now = datetime.now()
        cur_day_start = datetime(dt_now.year, dt_now.month, dt_now.day)
        isoc_now = dt_now.isocalendar()
        cur_week_start = datetime.fromisocalendar(isoc_now.year, isoc_now.week, 1)
        cur_month_start = datetime(dt_now.year, dt_now.month, 1)
        nxt_month_start = datetime(dt_now.year, dt_now.month + 1, 1)
        for budget in self._bud_repo.get_all():
            if budget.budget_type == constants.BUDGET_DAILY:
                budget.start = cur_day_start
            elif budget.budget_type == constants.BUDGET_WEEKLY:
                budget.start = cur_week_start
            elif budget.budget_type == constants.BUDGET_MONTHLY:
                budget.start = cur_month_start
                budget.period = nxt_month_start - cur_month_start
            self._bud_repo.update(budget)

    def _cat_sorted_list(self) -> list[CategoryEntry]:
        return [ self._entries_converter.category_to_entry(cat)
                 for cat in Category.get_all_categories_sorted(self._cat_repo) ]


    def _cb_get_allowed_attrs(self, attr_str: str) -> list[str]:
        if attr_str != "category":
            return []
        return [ cat.name for cat in self._cat_repo.get_all() ]

    def _add_expense(self, entry: ExpenseEntry) -> None:
        e = self._entries_converter.entry_to_expense(entry)
        self._exp_repo.add(e)
