"""Panel BOTS: tabla con el estado en vivo de cada bot."""

from __future__ import annotations

from typing import Dict

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bots.bot_manager import BotManager

COLUMNS = ["Estado", "Bot", "X", "Y", "Z", "Vida", "Hambre", "Tarea"]


class BotPanel(QWidget):
    def __init__(self, manager: BotManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self._row_by_bot_id: Dict[int, int] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("BOTS")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setObjectName("BotTable")
        layout.addWidget(self.table)

    def rebuild(self) -> None:
        self.table.setRowCount(0)
        self._row_by_bot_id.clear()
        for bot in self.manager.all_bots():
            self._ensure_row(bot.id)
            self.refresh_bot(bot.id)

    def _ensure_row(self, bot_id: int) -> int:
        if bot_id in self._row_by_bot_id:
            return self._row_by_bot_id[bot_id]
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col in range(len(COLUMNS)):
            self.table.setItem(row, col, QTableWidgetItem(""))
        self._row_by_bot_id[bot_id] = row
        return row

    def selected_bot_ids(self) -> list[int]:
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        id_by_row = {row: bot_id for bot_id, row in self._row_by_bot_id.items()}
        return [id_by_row[r] for r in rows if r in id_by_row]

    @Slot(int)
    def refresh_bot(self, bot_id: int) -> None:
        if not self.manager.has_bot(bot_id):
            return
        bot = self.manager.get_bot(bot_id)
        row = self._ensure_row(bot_id)

        values = [
            f"{bot.state.emoji()} {bot.state.value}",
            bot.name,
            f"{bot.x:.1f}",
            f"{bot.y:.1f}",
            f"{bot.z:.1f}",
            f"{bot.health:.0f}",
            f"{bot.food:.0f}",
            bot.task_status if not bot.last_error else f"error: {bot.last_error}",
        ]
        for col, value in enumerate(values):
            item = self.table.item(row, col)
            if item is None:
                item = QTableWidgetItem()
                self.table.setItem(row, col, item)
            item.setText(value)
            item.setTextAlignment(Qt.AlignCenter if col != 7 else Qt.AlignLeft | Qt.AlignVCenter)
