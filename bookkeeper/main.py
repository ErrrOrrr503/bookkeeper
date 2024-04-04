"""
Bookkeeper logic, in fact presenter
"""
from datetime import datetime, timedelta
import re
from locale import setlocale, LC_ALL

from bookkeeper.models.budget import Budget
from bookkeeper.models.category import Category
from bookkeeper.models.expense import Expense

from bookkeeper.config.configurator import Configurator

from bookkeeper.view.abstract_view import ExpenseEntry, CategoryEntry, BudgetEntry
from bookkeeper.view.abstract_view import AbstractView
from bookkeeper.view.abstract_view import ViewError
from bookkeeper.view.qt6_view import Qt6View

from bookkeeper.repository.abstract_repository import AbstractRepository
from bookkeeper.repository.repository_factory import RepositoryFactory

from bookkeeper.config import constants


class EntriesConverter:
    """
    Converter between models and view entries.
    Should include only converting logic.
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
        if re.fullmatch(r'(\d+)([,\.]\d\d?)?', cost_str) is None:
            raise ViewError(f'Wrong cost value: {cost_str}')
        s = cost_str.replace(',', '.')
        pos = s.find('.')
        multiplier = 100
        if pos > 0 and pos == len(s) - 2:
            multiplier = 10
        if pos > 0 and pos == len(s) - 3:
            multiplier = 1
        s = s.replace('.', '')
        return int(s) * multiplier  # no exception here possible due to strict re

    def _get_cat_pk_by_name(self, cat_name: str) -> int | None:
        if cat_name == constants.TOP_CATEGORY_NAME:
            return None
        cats = self._cat_repo.get_all(where={'name': cat_name})
        if len(cats) == 0:
            raise ViewError(f'No category {cat_name} present.')
        if len(cats) > 1:
            raise ViewError(f'Multiple categories {cat_name} present. '
                            'Repo seems to be corrupted.')
        return cats[0].pk

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
        if budget.budget_type != '':
            b.period = budget.budget_type
        else:
            b.period = budget.start.strftime('%x') + '-' + budget.end.strftime('%x')
        return b

    def entry_to_expense(self, entry: ExpenseEntry) -> Expense:
        exp = Expense()
        exp.added_date = datetime.now()
        exp.category = self._get_cat_pk_by_name(entry.category)
        exp.comment = entry.comment
        exp.cost = self._cost_str_to_int(entry.cost)
        try:
            exp.expense_date = datetime.strptime(entry.date, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            raise ViewError(f'Wrong date: {entry.date} '
                            'needed \'YYYY-M(M)-D(D) h(h):m(m):s(s)\'')
        return exp

    def entry_to_budget(self, entry: BudgetEntry) -> Budget:
        bud = Budget()
        bud.category = self._get_cat_pk_by_name(entry.category)
        bud.set_type(entry.period)
        bud.cost_limit = self._cost_str_to_int(entry.cost_limit)
        return bud

    def entry_to_category(self, entry: CategoryEntry) -> Category:
        cat = Category()
        if (entry.category == constants.TOP_CATEGORY_NAME
                or len(entry.category) == 0):
            raise ViewError('Category name must not be empty '
                            f'or \'{constants.TOP_CATEGORY_NAME}\'')
        cat.name = entry.category
        cat.parent = self._get_cat_pk_by_name(entry.parent)
        return cat


class BookKeeper():
    """
    Presenter, that contains logic
    """
    _cat_repo: AbstractRepository[Category]
    _bud_repo: AbstractRepository[Budget]
    _exp_repo: AbstractRepository[Expense]

    _view: AbstractView
    _entries_converter: EntriesConverter

    _exp_viewed: list[Expense]
    _bud_viewed: list[Budget]
    _cat_viewed: list[Category]

    def __init__(self) -> None:
        # set locale from env variable for proper datetime representation
        setlocale(LC_ALL, '')
        # 3 factories due to in 'f(t: T) -> T' it's hard to explain mypy
        # that T stands for equal types
        cat_repo_factory: RepositoryFactory[Category] = RepositoryFactory()
        bud_repo_factory: RepositoryFactory[Budget] = RepositoryFactory()
        exp_repo_factory: RepositoryFactory[Expense] = RepositoryFactory()
        self._cat_repo = cat_repo_factory.repo_for(Category)
        self._bud_repo = bud_repo_factory.repo_for(Budget)
        self._exp_repo = exp_repo_factory.repo_for(Expense)
        self._entries_converter = EntriesConverter(self._exp_repo,
                                                   self._cat_repo,
                                                   self._bud_repo)
        self._init_budgets()
        self._init_configuration()

        self._view.expenses.connect_add(self._cb_add_expense)
        self._view.expenses.connect_delete(self._cb_delete_expense)
        self._view.expenses.connect_edited(self._cb_edited_expense)
        self._view.expenses.connect_get_attr_allowed(self._cb_get_allowed_attrs)
        self._view.expenses.connect_get_default_entry(self._cb_get_def_expense)
        self._set_expenses()

        self._view.budgets.connect_edited(self._cb_edited_budget)
        self._view.budgets.connect_get_attr_allowed(self._cb_get_allowed_attrs)
        self._set_budgets()

        self._view.categories.connect_add(self._cb_add_category)
        self._view.categories.connect_delete(self._cb_delete_category)
        self._view.categories.connect_edited(self._cb_edited_category)
        self._view.categories.connect_get_attr_allowed(self._cb_get_allowed_attrs)
        self._view.categories.connect_get_default_entry(self._cb_get_def_category)
        self._set_categories()

    def start(self) -> None:
        """ the only public entity in presenter """
        self._view.start()

    def _init_configuration(self) -> None:
        confer = Configurator()
        desired_view = confer[type(self).__name__]['desired_view']
        if desired_view == 'Qt6View':
            self._view = Qt6View()
        else:
            raise ValueError(
                f'Unknown view \'{desired_view}\'specified in configuration.'
            )

    def _init_budgets(self) -> None:
        """ Create special budgets if none. """
        if len(self._bud_repo.get_all()) == 0:
            self._bud_repo.add(Budget(budget_type=constants.BUDGET_DAILY))
            self._bud_repo.add(Budget(budget_type=constants.BUDGET_WEEKLY))
            self._bud_repo.add(Budget(budget_type=constants.BUDGET_MONTHLY))
        else:
            self._update_budget_periods()

    def _update_budget_periods(self) -> None:
        """ Update starts and periods, days, weeks and months tend to pass. """
        for budget in self._bud_repo.get_all():
            budget.recalculate_period()
            self._bud_repo.update(budget)

    def _set_expenses(self) -> None:
        """ set expenses in view, may include representing logic, i.e. sorting """
        self._exp_viewed = self._exp_repo.get_all()
        entries = [self._entries_converter.expense_to_entry(e)
                   for e in self._exp_viewed]
        self._view.expenses.set_contents(entries)

    def _set_budgets(self) -> None:
        """ set budgets in view, may include representing logic, i.e. sorting """
        self._bud_viewed = self._bud_repo.get_all()
        entries = [self._entries_converter.budget_to_entry(b, self._calculate_spent(b))
                   for b in self._bud_viewed]
        self._view.budgets.set_contents(entries)

    def _set_categories(self) -> None:
        """ set categories in view, may include representing logic, i.e. sorting """
        self._cat_viewed = list(Category.get_all_categories_sorted(self._cat_repo))
        entries = [self._entries_converter.category_to_entry(c)
                   for c in self._cat_viewed]
        self._view.categories.set_contents(entries)

    def _calculate_spent(self, budget: Budget) -> int:
        spent = 0
        for exp in self._exp_repo.get_all():
            if (exp.expense_date > budget.start
                    and exp.expense_date < budget.end):
                spent += exp.cost
        return spent

    def _cb_get_allowed_attrs(self, attr_str: str) -> list[str]:
        if attr_str == "category":
            cats = [cat.name
                    for cat in Category.get_all_categories_sorted(self._cat_repo)]
            cats.insert(0, constants.TOP_CATEGORY_NAME)
            return cats
        return []

    def _cb_add_expense(self, entry: ExpenseEntry) -> None:
        exp = self._entries_converter.entry_to_expense(entry)
        exp.added_date = datetime.now()
        exp.expense_date = datetime.now()
        self._exp_repo.add(exp)
        self._set_expenses()
        self._set_budgets()  # recalculate

    def _cb_delete_expense(self, positions: list[int]) -> None:
        for pos in positions:
            self._exp_repo.delete(self._exp_viewed[pos].pk)
        self._set_expenses()
        self._set_budgets()  # recalculate

    def _cb_edited_expense(self, position: int, new_entry: ExpenseEntry) -> None:
        exp = self._exp_viewed[position]
        try:
            new_exp = self._entries_converter.entry_to_expense(new_entry)
            new_exp.pk = exp.pk
            self._exp_repo.update(new_exp)
            self._exp_viewed[position] = new_exp
            self._view.expenses.set_at_position(position, new_entry)
        except BaseException:
            # revert to old entry
            old_entry = self._entries_converter.expense_to_entry(exp)
            self._view.expenses.set_at_position(position, old_entry)
            raise
        self._set_budgets()  # recalculate

    def _cb_get_def_expense(self) -> ExpenseEntry:
        return self._entries_converter.expense_to_entry(Expense())

    def _cb_edited_budget(self, position: int, new_entry: BudgetEntry) -> None:
        bud = self._bud_viewed[position]
        try:
            new_bud = self._entries_converter.entry_to_budget(new_entry)
            new_bud.pk = bud.pk
            self._bud_repo.update(new_bud)
            self._bud_viewed[position] = new_bud
            self._view.budgets.set_at_position(position, new_entry)
        except BaseException:
            # revert to old entry
            old_entry = (
                self._entries_converter.budget_to_entry(bud,
                                                        self._calculate_spent(bud)))
            self._view.budgets.set_at_position(position, old_entry)
            raise

    def _cb_add_category(self, entry: CategoryEntry) -> None:
        cat = self._entries_converter.entry_to_category(entry)
        for c in self._cat_repo.get_all():
            if c.name == cat.name:
                raise ViewError('Category name must be unique.' f'({cat.name})')
        self._cat_repo.add(cat)
        self._set_categories()

    def _cb_delete_category(self, positions: list[int]) -> None:
        if len(positions) > 1:
            raise NotImplementedError('By far deletion of several categories '
                                      'at once is not supported.')
        if len(positions) == 0:
            return
        pos = positions[0]
        cat = self._cat_viewed[pos]
        parent = cat.parent
        to_delete = [subcat.pk for subcat in cat.get_subcategories(self._cat_repo)]
        to_delete.append(cat.pk)
        # delete category with subcategories
        for pk in to_delete:
            self._cat_repo.delete(pk)
        # re-link expenses
        for exp in self._exp_repo.get_all():
            if exp.category in to_delete:
                exp.category = parent
                self._exp_repo.update(exp)
        # re-link budgets
        for bud in self._bud_repo.get_all():
            if bud.category in to_delete:
                bud.category = parent
                self._bud_repo.update(bud)
        self._set_categories()
        self._set_expenses()
        self._set_budgets()

    def _cb_edited_category(self, position: int, new_entry: CategoryEntry) -> None:
        cat = self._cat_viewed[position]
        try:
            new_cat = self._entries_converter.entry_to_category(new_entry)
            for c in self._cat_repo.get_all():
                if c.name == new_cat.name and c.name != cat.name:
                    raise ViewError('Category name must be unique.' f'({cat.name})')
            new_cat.pk = cat.pk
            self._cat_repo.update(new_cat)
            self._cat_viewed[position] = new_cat
            self._view.categories.set_at_position(position, new_entry)
        except BaseException:
            # revert to old entry
            old_entry = self._entries_converter.category_to_entry(cat)
            self._view.categories.set_at_position(position, old_entry)
            raise
        self._set_categories()
        self._set_expenses()
        self._set_budgets()

    def _cb_get_def_category(self) -> CategoryEntry:
        return self._entries_converter.category_to_entry(Category(name=''))


# BookKeeper start #


if __name__ == '__main__':
    bookkeeper = BookKeeper()
    bookkeeper.start()
