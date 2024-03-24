"""
Pyside6 view implementation.
"""
from inspect import get_annotations
from typing import Callable, Any, Tuple
from functools import partial
from PySide6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMenu, QMessageBox, QGridLayout, QHBoxLayout, QVBoxLayout, QLineEdit, QLabel, QPushButton, QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QContextMenuEvent, QPaintEvent, QShowEvent

from bookkeeper.view.abstract_view import T, AbstractEntries, ExpenseEntry, BudgetEntry, CallbackError, CallbackWarning, CategoryEntry


def call_callback(widget: QWidget, callback: Callable[..., Any] | None, *args: Any, **kwargs: Any) -> Tuple[Any, str | None]:
    """ helper function to call callbacks and handle exceptions """
    if callback is None:
        return None, 'NoneCallback'
    title: str | None = None
    ret = None
    msg = ''
    box: Callable[..., Any]
    try:
        ret = callback(*args, **kwargs)
    except CallbackError as e:
        title = 'Error'
        msg = str(e)
        box = QMessageBox.critical
    except CallbackWarning as e:
        title = 'Warning'
        msg = str(e)
        box = QMessageBox.warning
    except Exception as e:
        title = 'Fatal'
        msg = repr(e)
        box = QMessageBox.critical
    if title is not None:
        box(widget, title, msg, QMessageBox.Ok)  # type: ignore[attr-defined]
    return ret, title

def partial_none(func: Callable[..., Any] | None,
                 /, *args: Any, **kwargs: Any) -> Callable[..., Any] | None:
    if func is None:
        return None
    return partial(func, *args, **kwargs)


class CallableWrapper():
    """
    Needed not to store <functions> as a class attribute.
    Otherwise, when making instance of this class they become methods.
    """
    func: Callable[..., Any]

    def __init__(self, func: Callable[..., Any]) -> None:
        self.func = func

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


class SelfUpdatableCombo(QComboBox):
    get_contents: Callable[[], list[str]] | None
    _prev_contents: list[str] = []

    def __init__(self, callback: Callable[[], list[str]] | None, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.get_contents = callback
        self.update_contents()

    def update_contents(self) -> None:
        possible_vals, err = call_callback(self, self.get_contents)
        if err is not None:
            possible_vals = []
        if possible_vals != self._prev_contents:
            old_text = self.currentText()
            self.clear()
            self.addItems(possible_vals)
            self.set_content(old_text)
            self._prev_contents = possible_vals

    def set_content(self, content_text: str) -> None:
        index = self.findText(content_text)
        if index >= 0:
            self.setCurrentIndex(index)

    def paintEvent(self, event: QPaintEvent) -> None:
        self.update_contents()
        super().paintEvent(event)


# Mypy ignores are set, due to mypy is unable to determine dynamic
# base classes. See https://github.com/python/mypy/issues/2477
class EntriesTableWidgetMeta(type(AbstractEntries),  # type: ignore[misc]
                             type(QTableWidget)):     # type: ignore[misc]
    """
    Metaclass for correct inheritance of ExpensesTableWidget from AbstractExpenses.
    """


class EntriesTableWidget(QTableWidget, AbstractEntries[T],
                          metaclass=EntriesTableWidgetMeta):
    """
    Editable expenses table widget
    """

    annotations: dict[str, type]
    _cls: type[T]

    _entry_edited: Callable[[int, T], None] | None = None
    _entries_delete: Callable[[list[int]], None] | None = None
    _get_entry_attr_allowed: Callable[[str], list[str]] | None = None
    _get_default_entry: Callable[[], T] | None = None
    _entry_add: Callable[[T], None] | None = None

    _context_menu: QMenu

    def __init__(self, cls: type[T], *args: Any, **kwargs: Any) -> None:
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
        # QTableWidget.DoubleClicked does exist, but mypy doesn't recognize it
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
                prev_widget = self.cellWidget(position, j)
                if isinstance(prev_widget, QComboBox):
                    prev_widget.currentTextChanged.disconnect(self._qbox_changed)
                get_allowed = partial_none(self._get_entry_attr_allowed, attr_str)
                qcombo = SelfUpdatableCombo(get_allowed)
                qcombo.set_content(item)
                self.setCellWidget(position, j, qcombo)
                qcombo.currentTextChanged.connect(self._qbox_changed)
                continue
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
        del_act = self._context_menu.addAction("Delete")
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
        add_act = self._context_menu.addAction("Add")
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
        entry, err = call_callback(self, self._get_default_entry)
        if err is not None:
            entry = self._cls()
        call_callback(self, self._entry_add, entry)

    def _want_delete(self) -> None:
        call_callback(self, self._entries_delete, [self.currentRow()])


#### Expenses #####


class ExpensesTableWidget(EntriesTableWidget[ExpenseEntry],
                          metaclass=EntriesTableWidgetMeta):
    class _ExpensesAdderWidget(QWidget):
        """
        Optimized widget for expense addition.
        (Optimized means more user-friendly).
        Callbacks in this widget are defined when initing ExpenseTable!
        Needed in fact for proper exception handling, as modals depend on self.
        """
        entry_add: Callable[..., Any] | None = None
        get_default_entry: Callable[..., Any] | None = None
        get_entry_attr_allowed: Callable[..., Any] | None = None
        edit_categories: Callable[..., Any] | None = None
        _entry: ExpenseEntry

        def showEvent(self, event: QShowEvent) -> None:
            self._entry, err = call_callback(self, self.get_default_entry)
            if err is not None:
                self._entry = ExpenseEntry()
            layout = QGridLayout()

            self.cost_widget = QLineEdit(self._entry.cost, self)
            self.cost_widget.textChanged.connect(self._cost_changed)
            layout.addWidget(QLabel('Cost', self), 0, 0)
            layout.addWidget(self.cost_widget, 0, 1)

            get_attr_allowed = partial_none(self.get_entry_attr_allowed, 'category')
            self.category_widget = SelfUpdatableCombo(get_attr_allowed, self)
            self.category_widget.set_content(self._entry.category)
            self.category_widget.currentTextChanged.connect(self._category_changed)
            layout.addWidget(QLabel('Category', self), 1, 0)
            layout.addWidget(self.category_widget, 1, 1)

            self.add_button_widget = QPushButton('Add', self)
            self.add_button_widget.clicked.connect(self._want_add)
            layout.addWidget(self.add_button_widget, 2, 1)

            self.edit_cat_button_widget = QPushButton('Edit', self)
            if self.edit_categories is not None:
                self.edit_cat_button_widget.clicked.connect(self.edit_categories)
            layout.addWidget(self.edit_cat_button_widget, 1, 2)

            self.setLayout(layout)
            super().showEvent(event)

        def _cost_changed(self, text: str) -> None:
            self._entry.cost = text

        def _category_changed(self, text: str) -> None:
            self._entry.category = text

        def _want_add(self) -> None:
            call_callback(self, self.entry_add, self._entry)


    expenses_adder_widget: type[_ExpensesAdderWidget]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
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

    def connect_edit_categories(self, callback: Callable[[QWidget | None], None]) -> None:
        self.expenses_adder_widget.edit_categories = CallableWrapper(callback)


#### Budgets #####


class BudgetTableWidget(EntriesTableWidget[BudgetEntry],
                        metaclass=EntriesTableWidgetMeta):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(BudgetEntry, *args, **kwargs)

    def set_at_position(self, position: int, entry: BudgetEntry) -> None:
        # setting item is not editing. Editing comes from user
        super().set_at_position(position, entry)
        self.cellChanged.disconnect(self.cell_changed)
        for j, attr_str in enumerate(self.annotations.keys()):
            if attr_str not in ['category', 'cost_limit']:
                qitem = self.item(position, j)
                qitem.setFlags(qitem.flags() & ~Qt.ItemIsEditable)  # type: ignore[attr-defined]
        self.cellChanged.connect(self.cell_changed)


#### Categories #####


# Mypy ignores are set, due to mypy is unable to determine dynamic
# base classes. See https://github.com/python/mypy/issues/2477
class CategoriesWidgetMeta(type(AbstractEntries),  # type: ignore[misc]
                           type(QWidget)):     # type: ignore[misc]
    """
    Metaclass for correct inheritance of ExpensesTableWidget from AbstractExpenses.
    """

class CategoriesWidget(QWidget, AbstractEntries[CategoryEntry],
                       metaclass=CategoriesWidgetMeta):
    """ categories tree view and editing """

    class _CategoryAdderWidget(QWidget):

        get_default_entry: Callable[..., Any]
        get_entry_attr_allowed: Callable[..., Any]
        entry_add: Callable[..., Any]
        entry_to_add: CategoryEntry

        def showEvent(self, event: QShowEvent) -> None:
            layout = QVBoxLayout()

            self.entry_to_add, err = call_callback(self, self.get_default_entry)
            if err is not None:
                self.entry_to_add = CategoryEntry()

            self.new_category_widget = QLineEdit(self.entry_to_add.category, self)
            self.new_category_widget.textEdited.connect(self._category_changed)
            layout.addWidget(QLabel(CategoryEntry.category, self))
            layout.addWidget(self.new_category_widget)

            get_attr_allowed = partial_none(self.get_entry_attr_allowed, 'category')
            self.parent_category_widget = SelfUpdatableCombo(get_attr_allowed, self)
            self.parent_category_widget.set_content(self.entry_to_add.parent)
            self.parent_category_widget.currentTextChanged.connect(self._parent_changed)
            layout.addWidget(QLabel(CategoryEntry.parent, self))
            layout.addWidget(self.parent_category_widget)

            self.add_button_widget = QPushButton('Add', self)
            self.add_button_widget.clicked.connect(self._want_add)
            layout.addWidget(self.add_button_widget)

            self.setLayout(layout)
            super().showEvent(event)

        def _parent_changed(self, text: str):
            self.entry_to_add.parent = text

        def _category_changed(self, text: str):
            self.entry_to_add.category = text

        def _want_add(self):
            call_callback(self, self.entry_add, self.entry_to_add)


    annotations: dict[str, type]

    _item_to_position: dict[QTreeWidgetItem, int]
    _position_to_item: dict[int, QTreeWidgetItem]

    _entry_edited: Callable[[int, CategoryEntry], None] | None = None
    _entries_delete: Callable[[list[int]], None] | None = None
    _get_entry_attr_allowed: Callable[[str], list[str]] | None = None
    _get_default_entry: Callable[[], CategoryEntry] | None = None
    _entry_add: Callable[[CategoryEntry], None] | None = None

    adder_widget: type[_CategoryAdderWidget]

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.adder_widget = self._CategoryAdderWidget
        self._item_to_position = {}
        self._position_to_item = {}
        self.annotations = get_annotations(CategoryEntry, eval_str=True)
        layout = QHBoxLayout()

        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["Categories"])
        self.tree.itemChanged.connect(self._item_changed)
        self.adder = self.adder_widget(self)
        layout.addWidget(self.tree)
        layout.addWidget(self.adder)

        self.setLayout(layout)

    def set_contents(self, entries: list[CategoryEntry]) -> None:
        if len(entries) == 0:
            return
        parent_items = [ QTreeWidgetItem([entries[0].parent]) ]
        parents = [ entries[0].parent ]
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

    def _item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        pos = self._item_to_position[item]
        entry = CategoryEntry()
        entry.category = item.text(0)
        entry.parent = '-'
        parent = item.parent()
        if parent is not None:
            entry.parent = parent.text(0)
        call_callback(self, self._entry_edited, pos, entry)