"""
Pyside6 view implementation.

In this file there are mypy ignores:

type: ignore[attr-defined] - used when mypy does not recognize existing Qt property
    i.e. QMessageBox.Ok, Qt.Key_Delete.

type: ignore[misc] - used due to mypy is unable to determine dynamic base classes.
    See https://github.com/python/mypy/issues/2477
"""
import sys
import traceback
from inspect import get_annotations
from typing import Callable, Any, Tuple
from functools import partial
from PySide6.QtWidgets import (QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QMenu, QMessageBox, QGridLayout, QHBoxLayout,
                               QVBoxLayout, QLineEdit, QLabel, QPushButton, QTreeWidget,
                               QTreeWidgetItem, QApplication, QMainWindow, QSizePolicy,
                               QAbstractScrollArea)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import (QKeyEvent, QContextMenuEvent, QColor, QBrush,
                           QPaintEvent, QShowEvent, QWheelEvent)

from bookkeeper.config import constants

from bookkeeper.view.abstract_view import (T, AbstractEntries, ExpenseEntry,
                                           BudgetEntry, ViewError, ViewWarning,
                                           CategoryEntry, AbstractView)

from bookkeeper.locale.gettext import _


def call_callback(widget: QWidget,
                  callback: Callable[..., Any] | None,
                  *args: Any, **kwargs: Any) -> Tuple[Any, str | None]:
    """
    Helper function to call callbacks and handle exceptions.
    If callback raises ViewError and ViewWarning, corresponding dialogs are displayed.
    If callback raises other Exception, traceback is displayed in critical dialog.

    Parameters
    ----------
    widget : QWidget
        Widget, who called the callback.
        Will be used as a dialog parent.
    callback :  Callable[..., Any] | None
        Callback to be called.
        if callback is None, nothing is called, and 'NoneCallback' status is returned.
    *args : Any
        The callback arguments.
    **kwargs : Any
        The callback keyword arguments.

    Returns
    -------
    Tuple (callback_return, status). Status is 'Error' for ViewError,
    'Warning' for ViewWarning, 'Fatal' for non View Exception,
    'NoneCallback' if callback was None.
    """
    if callback is None:
        return None, 'NoneCallback'
    title: str | None = None
    status: str | None = None
    ret = None
    msg = ''
    box: Callable[..., Any]
    try:
        ret = callback(*args, **kwargs)
    except ViewError as e:
        status = 'Error'
        title = _('Error')
        msg = str(e)
        box = QMessageBox.critical
    except ViewWarning as e:
        status = 'Warning'
        title = _('Warning')
        msg = str(e)
        box = QMessageBox.warning
    except Exception:
        status = 'Fatal'
        title = _('Fatal')
        msg = traceback.format_exc()
        box = QMessageBox.critical
    if title is not None:
        box(widget, title, msg, QMessageBox.Ok)  # type: ignore[attr-defined]
    return ret, status


def partial_none(func: Callable[..., Any] | None,
                 /, *args: Any, **kwargs: Any) -> Callable[..., Any] | None:
    """
    Like standard partial(), buf with None functions support.

    Parameters
    ----------
    func : Callable[..., Any] | None
        Function, where some arguments will be passed.
    *args : Any
        Some arguments to pass to the function.
    **kwargs : Any
        Some keyword arguments to pass to the function.

    Returns
    -------
    Function, that has some arguments already passed. None if func parameter was None.
    """
    if func is None:
        return None
    return partial(func, *args, **kwargs)


class CallableWrapper():
    """
    Needed not to store <functions> as a class attribute.
    Otherwise, when making instance of this class they become methods.

    Attributes
    ----------
    func : Callable[..., Any]
        Any callable, that is wrapped into CallableWrapper object.
    """
    func: Callable[..., Any]

    def __init__(self, func: Callable[..., Any]):
        self.func = func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


class SelfUpdatableCombo(QComboBox):
    """
    QComboBox, but it can update it's contents via callback.
    Update is triggered by paintEvent.
    While updating, TextChanged signals are disconnected, not to be triggered.
    wheelEvent is disabled as it worses ux in the current app.

    Attributes
    ----------
    get_contents : Callable[[], list[str]] | None
        The callback, that returns list of available ComboBox entries.
    _prev_contents : list[str]
        Previous contents, to update only when smth changed.
    _receivers : list[Callable[[str], None]]
        Slots, connected to TextChanged signal.
        Needed to disconnect them while updating.
    """
    get_contents: Callable[[], list[str]] | None = None
    _prev_contents: list[str] = []
    _receivers: list[Callable[[str], None]] = []

    def __init__(self, callback: Callable[[], list[str]] | None,
                 *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._receivers = []
        self.get_contents = callback
        self.update_contents()

    def update_contents(self) -> None:
        """ Update the contents of the ComboBox. """
        possible_vals, err = call_callback(self, self.get_contents)
        if err is not None:
            possible_vals = []
        if possible_vals != self._prev_contents:
            for rec in self._receivers:
                self.currentTextChanged.disconnect(rec)
            old_text = self.currentText()
            self.clear()
            self.addItems(possible_vals)
            self.set_content(old_text)
            self._prev_contents = possible_vals
            for rec in self._receivers:
                self.currentTextChanged.connect(rec)

    def connect_text_changed(self, callback: Callable[[str], None]) -> None:
        """
        Connect TextChanged signal.
        Must be used instead of currentTextChanged.connect due to update logic.

        Parameters
        ----------
        callback : Callable[[str], None]
            Slot to be connected.
        """
        self.currentTextChanged.connect(callback)
        self._receivers.append(callback)

    def disconnect_text_changed(self, callback: Callable[[str], None]) -> None:
        """
        Disconnect TextChanged signal.
        Must be used instead of currentTextChanged.disconnect due to update logic.

        Parameters
        ----------
        callback : Callable[[str], None]
            Slot to be disconnected.
        """
        self.currentTextChanged.disconnect(callback)
        self._receivers.remove(callback)

    def set_content(self, content_text: str) -> None:
        """
        Find index for the content_text and set it.

        Parameters
        ----------
        content_text : str
            The text to be set.
        """
        index = self.findText(content_text)
        if index >= 0:
            self.setCurrentIndex(index)

    def paintEvent(self, event: QPaintEvent) -> None:
        self.update_contents()
        super().paintEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """ Disable wheel event for proper table scrolling """
        event.ignore()


# Mypy ignores are set, due to mypy is unable to determine dynamic
# base classes. See https://github.com/python/mypy/issues/2477
class EntriesTableWidgetMeta(type(AbstractEntries),  # type: ignore[misc]
                             type(QTableWidget)):     # type: ignore[misc]
    """
    Metaclass for correct inheritance from AbstractEntries.
    """


class EntriesTableWidget(QTableWidget, AbstractEntries[T],
                         metaclass=EntriesTableWidgetMeta):
    """
    Editable entries table widget.

    Attributes
    ----------
    annotations : dict[str, type]
        Dictionary mapping entry attribute names to their types (str in fact).
    _entry_edited : Callable[[int, T], None] | None
        Callback for 'entry is edited' event.
    _entries_delete : Callable[[list[int]], None] | None
        Callback for 'entries want to be deleted' event.
    _get_entry_attr_allowed : Callable[[str], list[str]] | None
        Callback to get list of available values for an entry attribute.
    _get_default_entry : Callable[[], T] | None
        Callback to get default entry.
    _entry_add : Callable[[T], None] | None
        Callback for 'entry is added' event.

    _context_menu : QMenu
        Context menu for the table widget.
    """

    annotations: dict[str, type]
    _cls: type[T]

    _entry_edited: Callable[[int, T], None] | None = None
    _entries_delete: Callable[[list[int]], None] | None = None
    _get_entry_attr_allowed: Callable[[str], list[str]] | None = None
    _get_default_entry: Callable[[], T] | None = None
    _entry_add: Callable[[T], None] | None = None

    _context_menu: QMenu

    def __init__(self, cls: type[T], *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.annotations = get_annotations(cls, eval_str=True)
        self._cls = cls
        self.setColumnCount(len(self.annotations))
        self.setHorizontalHeaderLabels(
            [cls.__dict__[name] for name in self.annotations.keys()])
        header = self.horizontalHeader()
        for i in range(len(self.annotations)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.verticalHeader().hide()
        self.setEditTriggers(QTableWidget.DoubleClicked)  # type: ignore[attr-defined]
        self.cellChanged.connect(self.cell_changed)

        self._context_menu = QMenu(self)

    def set_at_position(self, position: int, entry: T) -> None:
        # setting item is not editing. Editing comes from user
        self.cellChanged.disconnect(self.cell_changed)
        for j, attr_str in enumerate(self.annotations.keys()):
            item = getattr(entry, attr_str)
            possible_vals, err = call_callback(self, self._get_entry_attr_allowed,
                                               attr_str)
            if err is not None:
                possible_vals = []
            if len(possible_vals) > 0:
                qcombo = self.cellWidget(position, j)
                if isinstance(qcombo, SelfUpdatableCombo):
                    qcombo.disconnect_text_changed(self._qbox_changed)
                else:
                    get_allowed = partial_none(self._get_entry_attr_allowed, attr_str)
                    qcombo = SelfUpdatableCombo(get_allowed)
                    self.setCellWidget(position, j, qcombo)
                qcombo.update_contents()
                qcombo.set_content(item)
                qcombo.connect_text_changed(self._qbox_changed)
                continue
            qitem = self.item(position, j)
            if qitem is not None:
                qitem.setText(item)
            else:
                qitem = QTableWidgetItem(item)
                self.setItem(position, j, qitem)
        self.cellChanged.connect(self.cell_changed)

    def set_contents(self, entries: list[T]) -> None:
        self.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self.set_at_position(row, entry)

    def connect_edited(self,
                       callback: Callable[[int, T], None]) -> None:
        self._entry_edited = callback

    def connect_delete(self,
                       callback: Callable[[list[int]], None]) -> None:
        self._entries_delete = callback
        del_act = self._context_menu.addAction(_('Delete'))
        del_act.triggered.connect(self._want_delete)

    def connect_get_attr_allowed(self,
                                 callback: Callable[[str], list[str]]) -> None:
        self._get_entry_attr_allowed = callback

    def connect_get_default_entry(self,
                                  callback: Callable[[], T]) -> None:
        self._get_default_entry = callback

    def connect_add(self,
                    callback: Callable[[T], None]) -> None:
        self._entry_add = callback
        add_act = self._context_menu.addAction(_('Add'))
        add_act.triggered.connect(self.want_add)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Delete:  # type: ignore[attr-defined]
            self._want_delete()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self._context_menu.exec(event.globalPos())

    def _qbox_changed(self, newtext: str) -> None:
        self.cell_changed(self.currentRow(), self.currentColumn())

    def cell_changed(self, row: int, column: int) -> None:
        """
        Slot, what is called whenever user changes table item.

        Parameters
        ----------
        row : int
            Row of the changed item.
        column : int
            Column of the changed item.
        """
        if self._entry_edited is None:
            return
        entry = self._cls()
        for i, field in enumerate(self.annotations.keys()):
            item = self.item(row, i)
            if item is None:
                q_box = self.cellWidget(row, i)
                val = q_box.currentText()
            else:
                val = item.text()
            setattr(entry, field, val)
        call_callback(self, self._entry_edited, row, entry)

    def want_add(self) -> None:
        """ Slot, that is called whenever user adds a new entry. """
        entry, err = call_callback(self, self._get_default_entry)
        if err is not None:
            entry = self._cls()
        call_callback(self, self._entry_add, entry)

    def _want_delete(self) -> None:
        """ Slot, that is called whenever user wants to delete entries. """
        call_callback(self, self._entries_delete, [self.currentRow()])


# Expenses #


class ExpensesTableWidget(EntriesTableWidget[ExpenseEntry],
                          metaclass=EntriesTableWidgetMeta):
    """
    Entries table widget, but for Expenses.

    Attributes
    ----------
    _ExpensesAdderWidget : class(QWidget)
        Adder widget for expenses inner class.

    expenses_adder_widget : type[_ExpensesAdderWidget]
        Makes inner class definition per-object.
        Callbacks here are set, when corresponding callbacks in ExpensesTableWidget
        instance are set.
        Instances of expenses_adder_widget use class-attributes callbacks.
        That enables to 'extract' expenses_adder_widget instances from
        ExpensesTableWidget instance in a way, that setting callbacks
        will affect all the extracted widgets.
        Extracted widgets can be placed i.e. in new windows and layouts.
    """

    class _ExpensesAdderWidget(QWidget):
        """
        Optimized widget for expense addition.
        (Optimized means more user-friendly).
        Callbacks in this widget are set when initiating ExpenseTable!

        Attributes
        ----------
        entry_add : Callable[..., Any] | None
            Callback, corresponding to one in ExpenseTableWidget
        get_default_entry : Callable[..., Any] | None
            Callback, corresponding to one in ExpenseTableWidget
        get_entry_attr_allowed : Callable[..., Any] | None
            Callback, corresponding to one in ExpenseTableWidget
        edit_categories : Callable[..., Any] | None
            Callback, to start editing categories.
        _prev_cat_slot : Callable[..., Any] | None
            Helper, stores prev value of edit_categories.
        _entry : ExpenseEntry
            ExpenseEntry to add.
        cost_widget : QLineEdit
            Widget, where the user enters cost.
        category_widget : SelfUpdatableCombo
            Widget, where the user choses category.
        """
        entry_add: Callable[..., Any] | None = None
        get_default_entry: Callable[..., Any] | None = None
        get_entry_attr_allowed: Callable[..., Any] | None = None
        edit_categories: Callable[..., Any] | None = None
        _prev_cat_slot: Callable[..., Any] | None = None
        _entry: ExpenseEntry

        cost_widget: QLineEdit
        category_widget: SelfUpdatableCombo

        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            layout = QGridLayout()

            self.cost_widget = QLineEdit(self)
            self.cost_widget.textChanged.connect(self._cost_changed)
            layout.addWidget(QLabel(_('Cost'), self), 0, 0)
            layout.addWidget(self.cost_widget, 0, 1)

            self.category_widget = SelfUpdatableCombo(None, self)
            self.category_widget.connect_text_changed(self._category_changed)
            layout.addWidget(QLabel(_('Category'), self), 1, 0)
            layout.addWidget(self.category_widget, 1, 1)

            self.add_button_widget = QPushButton(_('Add'), self)
            self.add_button_widget.clicked.connect(self._want_add)
            layout.addWidget(self.add_button_widget, 2, 1)

            self.edit_cat_button_widget = QPushButton(_('Edit'), self)
            layout.addWidget(self.edit_cat_button_widget, 1, 2)

            self.setLayout(layout)

        def showEvent(self, event: QShowEvent) -> None:
            if event.spontaneous() is True:
                # filter out events caused by window system (i.e. minimize-restore)
                return
            self._entry, err = call_callback(self, self.get_default_entry)
            if err is not None:
                self._entry = ExpenseEntry()

            self.cost_widget.setText(self._entry.cost)

            get_attr_allowed = partial_none(self.get_entry_attr_allowed, 'category')
            self.category_widget.get_contents = get_attr_allowed
            self.category_widget.set_content(self._entry.category)

            if self.edit_categories is not None:
                if self._prev_cat_slot is not None:
                    self.edit_cat_button_widget.clicked.disconnect(self._prev_cat_slot)
                self.edit_cat_button_widget.clicked.connect(self.edit_categories)
                self._prev_cat_slot = self.edit_categories

            super().showEvent(event)

        def _cost_changed(self, text: str) -> None:
            self._entry.cost = text

        def _category_changed(self, text: str) -> None:
            self._entry.category = text

        def _want_add(self) -> None:
            call_callback(self, self.entry_add, self._entry)

    expenses_adder_widget: type[_ExpensesAdderWidget]

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(ExpenseEntry, *args, **kwargs)
        # make inner class per-object
        self.expenses_adder_widget = self._ExpensesAdderWidget

    def connect_get_attr_allowed(self,
                                 callback: Callable[[str], list[str]]) -> None:
        super().connect_get_attr_allowed(callback)
        self.expenses_adder_widget.get_entry_attr_allowed = CallableWrapper(callback)

    def connect_get_default_entry(self,
                                  callback: Callable[[], ExpenseEntry]) -> None:
        super().connect_get_default_entry(callback)
        self.expenses_adder_widget.get_default_entry = CallableWrapper(callback)

    def connect_add(self,
                    callback: Callable[[ExpenseEntry], None]) -> None:
        super().connect_add(callback)
        self.expenses_adder_widget.entry_add = CallableWrapper(callback)

    def connect_edit_categories(self, callback: Callable[[], None]) -> None:
        """ callback shall display categories widget """
        self.expenses_adder_widget.edit_categories = CallableWrapper(callback)


# Budgets #


class BudgetTableWidget(EntriesTableWidget[BudgetEntry],
                        metaclass=EntriesTableWidgetMeta):
    """
    Entries table widget, but for Budgets.
    """
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(BudgetEntry, *args, **kwargs)

    def set_at_position(self, position: int, entry: BudgetEntry) -> None:
        # setting item is not editing. Editing comes from user
        super().set_at_position(position, entry)
        self.cellChanged.disconnect(self.cell_changed)
        for j, attr_str in enumerate(self.annotations.keys()):
            # for special type budgets
            # forbid to change anything except cost limit
            if (entry.period in [constants.BUDGET_DAILY,
                                 constants.BUDGET_WEEKLY,
                                 constants.BUDGET_MONTHLY]
                    and attr_str not in ['cost_limit']):
                self._forbid_editing(position, j)
        self.cellChanged.connect(self.cell_changed)

    def _forbid_editing(self, row: int, column: int) -> None:
        """ Forbid editing item or widget at specified position. """
        qcombo = self.cellWidget(row, column)
        if isinstance(qcombo, SelfUpdatableCombo):
            qcombo.setEnabled(False)
        else:
            qitem = self.item(row, column)
            qitem.setFlags(qitem.flags()
                           & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]

    def color_entry(self, position: int, red: int, green: int, blue: int) -> None:
        combo_style_sheet = f'QComboBox {{ background: rgb({red}, {green}, {blue}) }}'
        item_brush = QBrush(QColor(red, green, blue))
        if (red, green, blue) == constants.RGB_RESET_COLOR:
            combo_style_sheet = ''
            item_brush = QBrush()
        for j in range(self.columnCount()):
            wid = self.cellWidget(position, j)
            if isinstance(wid, SelfUpdatableCombo):
                wid.setStyleSheet(combo_style_sheet)
            else:
                self.item(position, j).setBackground(item_brush)


# Categories #


# Mypy ignores are set, due to mypy is unable to determine dynamic
# base classes. See https://github.com/python/mypy/issues/2477
class EntriesWidgetMeta(type(AbstractEntries),  # type: ignore[misc]
                        type(QWidget)):     # type: ignore[misc]
    """
    Metaclass for correct inheritance from AbstractEntries.
    """


class CategoriesWidget(QWidget, AbstractEntries[CategoryEntry],
                       metaclass=EntriesWidgetMeta):
    """
    Categories tree view, addition and editing.

    Attributes
    ----------
    _CategoryAdderWidget : class(QWidget)
        Adder widget for categories inner class.
    adder_widget : type[_CategoryAdderWidget]
        Per-instance _CategoryAdderWidget class, see explanation in ExpensesTabWidget.
    adder : _CategoryAdderWidget
        Categories adder widget.
    tree : QTreeWidget
        QTreeWidget for displaying categories tree.
    annotations : dict[str, type]
        Dictionary mapping entry attribute names to their types (str in fact).
    _entry_edited : Callable[[int, CategoryEntry], None] | None
        Callback for 'entry is edited' event.
    _entries_delete : Callable[[list[int]], None] | None
        Callback for 'entries want to be deleted' event.
    _get_entry_attr_allowed : Callable[[str], list[str]] | None
        Callback to get list of available values for an entry attribute.
    _get_default_entry : Callable[[], CategoryEntry] | None
        Callback to get default entry.
    _entry_add : Callable[[CategoryEntry], None] | None
        Callback for 'entry is added' event.
    _tree_context_menu : QMenu
        Context menu for the tree widget.
    _item_to_position : dict[QTreeWidgetItem, int]
        Dictionary that maps tree item to position in sorted list.
    _position_to_item: dict[int, QTreeWidgetItem]
        Dictionary that maps position in sorted list to tree item.
    """

    class _CategoryAdderWidget(QWidget):
        """
        Adder widget for categories.

        Attributes
        ----------
        get_default_entry : Callable[..., Any]
            Callback, corresponding to CategoriesWidget one.
        get_entry_attr_allowed : Callable[..., Any]
            Callback, corresponding to CategoriesWidget one.
        entry_add : Callable[..., Any]
            Callback, corresponding to CategoriesWidget one.
        _entry_to_add : CategoryEntry
            Category entry to be added
        new_category_widget : QLineEdit
            Widget, where user enters name of the new category.
        parent_category_widget : SelfUpdatableCombo
            Widget, where user choses parent of the new category.
        """
        get_default_entry: Callable[..., Any]
        get_entry_attr_allowed: Callable[..., Any]
        entry_add: Callable[..., Any]
        _entry_to_add: CategoryEntry
        new_category_widget: QLineEdit
        parent_category_widget: SelfUpdatableCombo

        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            layout = QVBoxLayout()

            self.new_category_widget = QLineEdit(self)
            self.new_category_widget.textEdited.connect(self._category_changed)
            layout.addWidget(QLabel(CategoryEntry.category, self))
            layout.addWidget(self.new_category_widget)

            self.parent_category_widget = SelfUpdatableCombo(None, self)
            self.parent_category_widget.connect_text_changed(self._parent_changed)
            layout.addWidget(QLabel(CategoryEntry.parent, self))
            layout.addWidget(self.parent_category_widget)

            self.add_button_widget = QPushButton(_('Add'), self)
            self.add_button_widget.clicked.connect(self._want_add)
            layout.addWidget(self.add_button_widget)

            self.setLayout(layout)

        def showEvent(self, event: QShowEvent) -> None:
            if event.spontaneous() is True:
                # filter out events caused by window system (i.e. minimize-restore)
                return
            self._entry_to_add, err = call_callback(self, self.get_default_entry)
            if err is not None:
                self._entry_to_add = CategoryEntry()

            self.new_category_widget.setText(self._entry_to_add.category)

            get_attr_allowed = partial_none(self.get_entry_attr_allowed, 'category')
            self.parent_category_widget.get_contents = get_attr_allowed
            self.parent_category_widget.set_content(self._entry_to_add.parent)

            super().showEvent(event)

        def _parent_changed(self, text: str) -> None:
            self._entry_to_add.parent = text

        def _category_changed(self, text: str) -> None:
            self._entry_to_add.category = text

        def _want_add(self) -> None:
            call_callback(self, self.entry_add, self._entry_to_add)

    annotations: dict[str, type]

    _item_to_position: dict[QTreeWidgetItem, int]
    _position_to_item: dict[int, QTreeWidgetItem]

    _entry_edited: Callable[[int, CategoryEntry], None] | None = None
    _entries_delete: Callable[[list[int]], None] | None = None
    _get_entry_attr_allowed: Callable[[str], list[str]] | None = None
    _get_default_entry: Callable[[], CategoryEntry] | None = None
    _entry_add: Callable[[CategoryEntry], None] | None = None

    _tree_context_menu: QMenu

    adder_widget: type[_CategoryAdderWidget]

    adder: _CategoryAdderWidget
    tree: QTreeWidget

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.adder_widget = self._CategoryAdderWidget
        self._item_to_position = {}
        self._position_to_item = {}
        self.annotations = get_annotations(CategoryEntry, eval_str=True)
        layout = QHBoxLayout()
        self.adder_v_aligner = QWidget(self)
        adder_layout = QVBoxLayout()

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels([_('Categories')])
        self.tree.itemChanged.connect(self._item_changed)
        self.tree.itemActivated.connect(self._item_activated)

        self._tree_context_menu = QMenu(self.tree)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)  # type: ignore[attr-defined]
        self.tree.customContextMenuRequested.connect(self._tree_context_menu_requested)

        self.adder = self.adder_widget(self.adder_v_aligner)
        self.adder.setSizePolicy(QSizePolicy.Policy.Preferred,
                                 QSizePolicy.Policy.Fixed)
        adder_layout.addWidget(self.adder)
        adder_layout.addStretch()
        self.adder_v_aligner.setLayout(adder_layout)

        layout.addWidget(self.tree)
        layout.addWidget(self.adder_v_aligner)

        self.setLayout(layout)

    def set_contents(self, entries: list[CategoryEntry]) -> None:
        self.tree.clear()
        self._item_to_position = {}
        self._position_to_item = {}
        if len(entries) == 0:
            return
        parent_items = [QTreeWidgetItem([entries[0].parent])]
        parents = [entries[0].parent]
        i = 0
        while entries[i].parent == parents[-1]:
            item = QTreeWidgetItem([entries[i].category])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            parent_items[-1].addChild(item)
            self._item_to_position[item] = i
            self._position_to_item[i] = item
            i += 1
            if i == len(entries):
                break
            if entries[i].parent == entries[i - 1].category:
                parents.append(entries[i].parent)
                parent_items.append(item)
                continue
            while entries[i].parent != parents[-1] and len(parents) > 1:
                parents.pop(-1)
                parent_items.pop(-1)

        if i != len(entries):
            raise ValueError(f"Abnormal category sorting. i = {i}, len = {len(entries)}")

        top_items = parent_items[0].takeChildren()
        self.tree.insertTopLevelItems(0, top_items)
        self.tree.expandAll()

    def set_at_position(self, position: int, entry: CategoryEntry) -> None:
        item = self._position_to_item.get(position)
        if item is None:
            raise ValueError("position must exist (created by set_contents).")
        item.setText(0, entry.category)

    def connect_edited(self,
                       callback: Callable[[int, CategoryEntry], None]) -> None:
        self._entry_edited = callback

    def connect_delete(self,
                       callback: Callable[[list[int]], None]) -> None:
        self._entries_delete = callback
        del_act = self._tree_context_menu.addAction(_('Delete'))
        del_act.triggered.connect(self._want_delete)

    def connect_add(self,
                    callback: Callable[[CategoryEntry], None]) -> None:
        self._entry_add = callback
        self._CategoryAdderWidget.entry_add = CallableWrapper(callback)

    def connect_get_default_entry(self,
                                  callback: Callable[[], CategoryEntry]) -> None:
        self._get_default_entry = callback
        self._CategoryAdderWidget.get_default_entry = CallableWrapper(callback)

    def connect_get_attr_allowed(self,
                                 callback: Callable[[str], list[str]]) -> None:
        self._get_entry_attr_allowed = callback
        self._CategoryAdderWidget.get_entry_attr_allowed = CallableWrapper(callback)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key_Delete:  # type: ignore[attr-defined]
            self._want_delete()
            return
        super().keyPressEvent(event)

    def _tree_context_menu_requested(self, pos: QPoint) -> None:
        self._tree_context_menu.exec(self.tree.mapToGlobal(pos))

    def _item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        pos = self._item_to_position[item]
        entry = CategoryEntry()
        entry.category = item.text(0)
        entry.parent = constants.TOP_CATEGORY_NAME
        parent = item.parent()
        if parent is not None:
            entry.parent = parent.text(0)
        call_callback(self, self._entry_edited, pos, entry)

    def _item_activated(self, item: QTreeWidgetItem, column: int) -> None:
        self.adder.parent_category_widget.set_content(item.text(0))

    def _want_delete(self) -> None:
        cur_item = self.tree.currentItem()
        if cur_item is not None:
            call_callback(self, self._entries_delete, [self._item_to_position[cur_item]])


# Qt6 View #


class Qt6View(AbstractView):
    """
    Qt6 view implementation.

    Attributes
    ----------
    _expenses_widget : ExpensesTableWidget
        AbstractEntries implementation for expenses.
    _budgets_widget : BudgetTableWidget
        AbstractEntries implementation for budgets.
    _categories_widget : CategoriesWidget
        AbstractEntries implementation for categories.
    app : QApplication
        Qt Application that runs event loop.
    window : QMainWindow
        Main Window of the app.
    """
    _expenses_widget: ExpensesTableWidget
    _budgets_widget: BudgetTableWidget
    _categories_widget: CategoriesWidget

    app: QApplication
    window: QMainWindow

    def __init__(self) -> None:
        self._create_qapp()
        self.window = QMainWindow()
        self.central_widget = QWidget(self.window)
        self.central_layout = QVBoxLayout()

        self._categories_widget = CategoriesWidget()

        self.central_layout.addWidget(QLabel(_('Expenses'), self.central_widget))
        self._expenses_widget = ExpensesTableWidget(self.central_widget)
        self.central_layout.addWidget(self._expenses_widget)

        self.central_layout.addWidget(QLabel(_('Budgets'), self.central_widget))
        self._budgets_widget = BudgetTableWidget(self.central_widget)
        self._budgets_widget.setSizePolicy(QSizePolicy.Policy.Expanding,
                                           QSizePolicy.Policy.Minimum)
        adj_to_cont = QAbstractScrollArea.AdjustToContents  # type: ignore[attr-defined]
        self._budgets_widget.setSizeAdjustPolicy(adj_to_cont)
        self.central_layout.addWidget(self._budgets_widget)

        self.expenses_adder = self.expenses.expenses_adder_widget(self.central_widget)
        self._expenses_widget.connect_edit_categories(self._show_categories_widget)
        self.central_layout.addWidget(self.expenses_adder)

        self.central_widget.setLayout(self.central_layout)
        self.window.setCentralWidget(self.central_widget)
        self.window.resize(500, 400)

    def _create_qapp(self) -> None:
        """ for monkeypatching in tests """
        self.app = QApplication(sys.argv)

    def start(self) -> None:
        """ Show the main window and launch event loop. """
        self.window.show()
        self.app.exec()

    @property
    def expenses(self) -> ExpensesTableWidget:
        return self._expenses_widget

    @property
    def budgets(self) -> BudgetTableWidget:
        return self._budgets_widget

    @property
    def categories(self) -> CategoriesWidget:
        return self._categories_widget

    def _show_categories_widget(self) -> None:
        self._categories_widget.show()
