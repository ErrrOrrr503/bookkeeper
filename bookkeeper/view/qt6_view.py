"""
Pyside6 view implementation.
"""
from inspect import get_annotations
from typing import Callable, Any
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QMenu
from PySide6.QtCore import QEvent, Qt

from bookkeeper.view.abstract_view import ExpenseEntry, AbstractExpenses


# Mypy ignores are set, due to mypy is unable to determine dynamic
# base classes. See https://github.com/python/mypy/issues/2477
class ExpensesTableWidgetMeta(type(AbstractExpenses),  # type: ignore[misc]
                              type(QTableWidget)):     # type: ignore[misc]
    """
    Metaclass for correct inheritance of ExpensesTableWidget from AbstractExpenses.
    """


class ExpensesTableWidget(QTableWidget, AbstractExpenses,
                          metaclass=ExpensesTableWidgetMeta):
    """
    Editable expenses table widget
    """

    _annotations: dict[str, type]

    _entry_edited: Callable[[int, ExpenseEntry], None] | None = None
    _entries_delete: Callable[[list[int]], None] | None = None
    _get_expense_attr_allowed: Callable[[str], list[str]] | None = None
    _entry_add: Callable[[], None] | None = None

    _context_menu: QMenu

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._annotations = get_annotations(ExpenseEntry, eval_str=True)

        self.setColumnCount(len(self._annotations))
        self.setHorizontalHeaderLabels(
            [ExpenseEntry.__dict__[name] for name in self._annotations.keys()])
        header = self.horizontalHeader()
        for i in range(len(self._annotations)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.verticalHeader().hide()
        # QTableWidget.DoubleClicked does exist, but mypy doesn't recognize it
        self.setEditTriggers(QTableWidget.DoubleClicked)  # type: ignore[attr-defined]
        self.cellChanged.connect(self._cell_changed)

        self._context_menu = QMenu(self)

    def set_at_position(self, position: int, entry: ExpenseEntry) -> None:
        # setting item is not editing. Editing comes from user
        self.cellChanged.disconnect(self._cell_changed)
        for j, attr_str in enumerate(self._annotations.keys()):
            item = getattr(entry, attr_str)
            if self._get_expense_attr_allowed is not None:
                possible_vals = self._get_expense_attr_allowed(attr_str)
                if len(possible_vals) > 0:
                    prev_widget = self.cellWidget(position, j)
                    if isinstance(prev_widget, QComboBox):
                        prev_widget.currentTextChanged.disconnect(self._qbox_changed)
                    qcombo = QComboBox()
                    qcombo.addItems(possible_vals)
                    index = qcombo.findText(item)
                    if index >= 0:
                        qcombo.setCurrentIndex(index)
                    self.setCellWidget(position, j, qcombo)
                    qcombo.currentTextChanged.connect(self._qbox_changed)
                    continue
            qitem = QTableWidgetItem(item)
            self.setItem(position, j, qitem)
        self.cellChanged.connect(self._cell_changed)

    def set_contents(self, entries: list[ExpenseEntry]) -> None:
        self.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self.set_at_position(row, entry)

    def connect_edited(self,
                       callback: Callable[[int, ExpenseEntry], None]) -> None:
        self._entry_edited = callback

    def connect_delete(self,
                       callback: Callable[[list[int]], None]) -> None:
        self._entries_delete = callback
        del_act = self._context_menu.addAction("Delete")
        del_act.triggered.connect(self._want_delete)

    def connect_get_attr_allowed(self,
                                 callback: Callable[[str], list[str]]) -> None:
        self._get_expense_attr_allowed = callback

    def connect_add(self,
                    callback: Callable[[], None]) -> None:
        self._entry_add = callback
        add_act = self._context_menu.addAction("Add")
        add_act.triggered.connect(self._want_add)

    def keyPressEvent(self, event: QEvent) -> None:
        if event.key() == Qt.Key_Delete:
            self._want_delete()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        self._context_menu.exec(event.globalPos())

    def _qbox_changed(self, newtext: str) -> None:
        self._cell_changed(self.currentRow(), self.currentColumn())

    def _cell_changed(self, row: int, column: int) -> None:
        if self._entry_edited is None:
            return
        entry = ExpenseEntry()
        for i, field in enumerate(self._annotations.keys()):
            item = self.item(row, i)
            if item is None:
                q_box = self.cellWidget(row, i)
                val = q_box.currentText()
            else:
                val = item.text()
            setattr(entry, field, val)
        if self._entry_edited is not None:
            self._entry_edited(row, entry)

    def _want_add(self) -> None:
        if self._entry_add is not None:
            self._entry_add()

    def _want_delete(self) -> None:
        if self._entries_delete is not None:
            self._entries_delete([self.currentRow()])