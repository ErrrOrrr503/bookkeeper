"""
Pyside6 view implementation.
"""
from inspect import get_annotations
from typing import Callable, Any
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QComboBox
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
    _expense_edited: Callable[[int, ExpenseEntry], None] | None = None
    _entries_deleted: Callable[[list[int]], None] | None = None
    _get_expense_attr_allowed: Callable[[str], list[str]] | None = None

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

    def connect_expense_edited(self,
                               callback: Callable[[int, ExpenseEntry], None]) -> None:
        self._expense_edited = callback

    def connect_expense_delete(self,
                               callback: Callable[[list[int]], None]) -> None:
        self._entries_deleted = callback

    def connect_get_expense_attr_allowed(self,
                                         callback: Callable[[str], list[str]]) -> None:
        self._get_expense_attr_allowed = callback

    def keyPressEvent(self, event: QEvent) -> None:
        if event.key() == Qt.Key_Delete and self._entries_deleted is not None:
            self._entries_deleted([self.currentRow()])
            return
        super().keyPressEvent(event)

    def _qbox_changed(self, newtext: str) -> None:
        self._cell_changed(self.currentRow(), self.currentColumn())

    def _cell_changed(self, row: int, column: int) -> None:
        if self._expense_edited is None:
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
        if self._expense_edited is not None:
            self._expense_edited(row, entry)
