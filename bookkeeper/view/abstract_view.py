"""
View types and abstract class
"""
from abc import ABC, abstractmethod
from typing import Callable
from dataclasses import dataclass


# TODO: translation
@dataclass
class ExpenseEntry():
    """
    Type that represents Expenses entry.

    Default attributes represent column/sections names.
    All attributes are strings. View's job is not to format, but to draw.
    """
    date: str = 'Date'
    cost: str = 'Cost'
    category: str = 'Category'
    comment: str = 'Comment'


class AbstractExpenses(ABC):
    """
    Abstract expenses list viewer, i.e. table widget
    """
    @abstractmethod
    def set_contents(self, entries: list[ExpenseEntry]) -> None:
        """
        Set the contents of the table/list/other representation
        """

    @abstractmethod
    def set_at_position(self, position: int, entry: ExpenseEntry) -> None:
        """
        Set an entry at specified position in the table/list/other representation
        """

    @abstractmethod
    def connect_edited(self,
                       callback: Callable[[int, ExpenseEntry], None]) -> None:
        """
        Register callback on "an entry is edited".
        Accepts entry's position and new value.
        """

    @abstractmethod
    def connect_delete(self,
                       callback: Callable[[list[int]], None]) -> None:
        """
        Register callback on "an entry wants to be deleted".
        Accepts list of deleted entries' positions.
        """

    @abstractmethod
    def connect_add(self,
                    callback: Callable[[], None]) -> None:
        """
        Register callback on "want to add entry".
        """

    @abstractmethod
    def connect_get_attr_allowed(self,
                                 callback: Callable[[str], list[str]]) -> None:
        """
        Register callback, thar AbstractExpenses can call to query, if
        ExpenseEntry's attribute can take only specific values.
        This enables view to make optimizations, i.e. dropdowns
        """


@dataclass
class BudgetEntry():
    """
    Type that represents ExpensesTable row.

    Default attributes represent columns/sections names.
    All attributes are strings. View's job is not to format, but to draw.
    """
    period: str = "Period"
    cost_limit: str = "Limit"
    spent: str = "Spent"
    category: str = "Category"


class AbstractBudgets(ABC):
    """
    Abstract budgets list viewer, i.e. table widget.

    This is separated from expenses, notwithstanding the task is similar(by far).
    Separation will allow to diverse view 'optimizations'.
    I.e. color marking is not necessary for expenses, but useful for budget.
    Single abstract class for both tasks will result in plenty of unused
    callback settings.
    """
    @abstractmethod
    def set_contents(self, entries: list[BudgetEntry]) -> None:
        """
        Set the contents of the table/list/other representation
        """

    @abstractmethod
    def set_at_position(self, position: int, entry: BudgetEntry) -> None:
        """
        Set an entry at specified position in the table/list/other representation
        """

    @abstractmethod
    def connect_edited(self,
                       callback: Callable[[int, BudgetEntry], None]) -> None:
        """
        Register callback on "an entry is edited".
        Accepts entry's position and new value.
        """

    @abstractmethod
    def connect_delete(self,
                       callback: Callable[[list[int]], None]) -> None:
        """
        Register callback on "an entry is deleted".
        Accepts list of deleted entries' positions.
        """

    @abstractmethod
    def connect_getattr_allowed(self,
                                callback: Callable[[str], list[str]]) -> None:
        """
        Register callback, thar AbstractExpenses can call to query, if
        ExpenseEntry's attribute can take only specific values.
        This enables view to make optimizations, i.e. dropdowns
        """
