"""
View types and abstract class
"""
from abc import ABC, abstractmethod
from typing import Callable, Generic, TypeVar
from dataclasses import dataclass


class CallbackError(Exception):
    """ Some exception with clear error string that view can handle. """

class CallbackWarning(Exception):
    """ Some exception with clear error string that view can handle. """

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

@dataclass
class CategoryEntry():
    name: str = "Name"
    parent: str = "Parent"

T = TypeVar('T', ExpenseEntry, BudgetEntry, CategoryEntry)

class AbstractEntries(ABC, Generic[T]):
    """
    Abstract expenses list viewer, i.e. table widget
    """
    @abstractmethod
    def set_contents(self, entries: list[T]) -> None:
        """
        Set the contents of the table/list/other representation
        """

    @abstractmethod
    def set_at_position(self, position: int, entry: T) -> None:
        """
        Set an entry at specified position in the table/list/other representation
        """

    @abstractmethod
    def connect_edited(self,
                       callback: Callable[[int, T], None]) -> None:
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
                    callback: Callable[[T], None]) -> None:
        """
        Register callback on "want to add entry".
        """

    @abstractmethod
    def connect_get_default_entry(self,
                                  callback: Callable[[], T]) -> None:
        """
        Register callback that returns default entry in currect env.
        """

    @abstractmethod
    def connect_get_attr_allowed(self,
                                 callback: Callable[[str], list[str]]) -> None:
        """
        Register callback, thar AbstractExpenses can call to query, if
        ExpenseEntry's attribute can take only specific values.
        This enables view to make optimizations, i.e. dropdowns
        """
