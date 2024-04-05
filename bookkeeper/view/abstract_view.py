"""
View types and abstract class
"""
from abc import ABC, abstractmethod
from typing import Callable, Generic, TypeVar
from dataclasses import dataclass


class ViewError(Exception):
    """ Some exception with clear error string that view can handle. """


class ViewWarning(Exception):
    """ Some exception with clear error string that view can handle. """


@dataclass
class ExpenseEntry():
    """
    Type that represents an Expense instance.

    Default attributes represent column/sections names.
    All attributes are strings. View's job is not to format, but to draw.

    Attributes
    ----------
    date : str
        Date of the expense.
    cost : str
        Cost of the expense.
    category : str
        Category of the expense.
    comment : str
        User comment about the expense.
    """
    date: str = 'Date'
    cost: str = 'Cost'
    category: str = 'Category'
    comment: str = 'Comment'


@dataclass
class BudgetEntry():
    """
    Type that represents a Budget instance.

    Default attributes represent columns/sections names.
    All attributes are strings. View's job is not to format, but to draw.

    Attributes
    ----------
    period : str
        Period fot the budget restriction.
    cost_limit : str
        Budget restriction.
    spent : str
        How much is spent during the period.
    category : str
        Category, for which budget is restricted.
    """
    period: str = "Period"
    cost_limit: str = "Limit"
    spent: str = "Spent"
    category: str = "Category"


@dataclass
class CategoryEntry():
    """
    Type that represents Categories tree item.

    Default attributes represent columns/sections names.
    All attributes are strings. View's job is not to format, but to draw.

    Attributes
    ----------
    category : str
        Name of the category.
    parent : str
        Name of the parent category.
    """
    category: str = "Category name"
    parent: str = "Parent category"


T = TypeVar('T', ExpenseEntry, BudgetEntry, CategoryEntry)


class AbstractEntries(ABC, Generic[T]):
    """
    Abstract expenses list viewer, i.e. table widget or tree widget.

    Methods that raise NotImplementedError are optional,
    but can be used for optimization (performance or ux).
    """
    @abstractmethod
    def set_contents(self, entries: list[T]) -> None:
        """
        Set the contents of the table/other representation.

        Parameters
        ----------
        entries : list[T]
            List of entries to be viewed.
            For trees (categories), the list must be topologically sorted.
        """

    @abstractmethod
    def set_at_position(self, position: int, entry: T) -> None:
        """
        Set an entry at existing position in the table/other representation.
        Position becomes existing after set_contents() call.
        Position matches one in the list, passed to set_contents().

        Parameters
        ----------
        position : int
            Position, where the entry will be placed.
        entry : T
            Entry to be placed at the position.
        """

    @abstractmethod
    def connect_edited(self,
                       callback: Callable[[int, T], None]) -> None:
        """
        Register callback on "an entry is edited" event.

        Parameters
        ----------
        callback : Callable[[int, T], None]
            Callback, that accepts entry's position and new value.
            And is responsible for editing logic.
        """

    @abstractmethod
    def connect_delete(self,
                       callback: Callable[[list[int]], None]) -> None:
        """
        Register callback on "an entry wants to be deleted" event.

        Parameters
        ----------
        callback : Callable[[list[int]], None]
            Callback, that accepts list of 'entries to delete' positions.
            And is responsible for deletion logic.
        """

    @abstractmethod
    def connect_add(self,
                    callback: Callable[[T], None]) -> None:
        """
        Register callback on "want to add entry" event.

        Parameters
        ----------
        callback : Callable[[T], None]
            Callback, that accepts new entry.
            And is responsible for addition logic for this entry.
        """

    @abstractmethod
    def connect_get_default_entry(self,
                                  callback: Callable[[], T]) -> None:
        """
        Register callback that returns default entry.

        Parameters
        ----------
        callback : Callable[[], T]
            Callback, that returns default (suitable for current situation) entry.
        """

    @abstractmethod
    def connect_get_attr_allowed(self,
                                 callback: Callable[[str], list[str]]) -> None:
        """
        Register callback, that AbstractExpenses can call to query, if
        ExpenseEntry's attribute can take only specific values.
        This enables view to make optimizations, i.e. dropdowns.

        Parameters
        ----------
        callback : Callable[[str], list[str]]
            Callback, that accepts attribute name, and returns a list of values,
            this attribute can take. Empty list if there are no specific values.
        """

    def color_entry(self, position: int, red: int, green: int, blue: int) -> None:
        """
        Color the entry at position in RGB.
        Optional method.
        Use (red, green, blue) == constants.RGB_RESET_COLOR to revert color.

        Parameters
        ----------
            position : int
                The position to be colored.
            red : int
                Red component in RGB (0-255).
                constants.RGB_RESET_COLOR[0] when resetting.
            green : int
                Green component in RGB (0-255).
                constants.RGB_RESET_COLOR[1] when resetting.
            blue : int
                Blue component in RGB (0-255).
                constants.RGB_RESET_COLOR[2] when resetting.
        """
        raise NotImplementedError


class AbstractView(ABC):
    """
    View abstract class.
    Unites AbstractEntries for expenses, budgets and categories
    """
    @property
    @abstractmethod
    def expenses(self) -> AbstractEntries[ExpenseEntry]:
        """
        Expenses implementation property (or attribute)
        in AbstractView implementation.
        """

    @property
    @abstractmethod
    def budgets(self) -> AbstractEntries[BudgetEntry]:
        """
        Budgets implementation property (or attribute)
        in AbstractView implementation.
        """

    @property
    @abstractmethod
    def categories(self) -> AbstractEntries[CategoryEntry]:
        """
        Categories implementation property (or attribute)
        in AbstractView implementation.
        """

    @abstractmethod
    def start(self) -> None:
        """ Start the gui and the event loop. """
