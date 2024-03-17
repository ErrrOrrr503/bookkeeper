"""
Pyside6 view implementation.
"""
from inspect import get_annotations
from typing import Callable
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox

from bookkeeper.view.abstract_view import ExpenseEntry, AbstractExpenses

class ExpensesTableWidget(QTableWidget):
    """
    Editable expenses table widget
    """

    _annotations: dict[str, type]
    _expense_edited: Callable[[int, ExpenseEntry], None] | None = None
    _get_expense_attr_allowed: Callable[[str], list[str]] | None = None

    def __init__(self, *args, **kwargs):
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

        self.setEditTriggers(QAbstractItemView.DoubleClicked)

    def set_at_position(self, position: int, entry: ExpenseEntry) -> None:
        for j, attr_str in enumerate(self._annotations.keys()):
            item = getattr(entry, attr_str)
            if self._get_expense_attr_allowed is not None:
                possible_vals = self._get_expense_attr_allowed(attr_str)
                if len(possible_vals) > 0:
                    QCombo = QComboBox()
                    QCombo.addItems(possible_vals)
                    index = QCombo.findText(item)
                    if index >= 0:
                        QCombo.setCurrentIndex(index)
                    self.setCellWidget(position, j, QCombo)
                    continue
            QItem = QTableWidgetItem(item)
            self.setItem(position, j, QItem)


    def set_contents(self, entries: list[ExpenseEntry]) -> None:
        self.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self.set_at_position(row, entry)

    def connect_expense_edited(self, callback: Callable[[int, ExpenseEntry], None]):
        self._expense_edited = callback

    def connect_get_expense_attr_allowed(self, callback: Callable[[str], list[str]]):
        self._get_expense_attr_allowed = callback