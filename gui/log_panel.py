"""Panel de LOG: muestra los mensajes del sistema con color segun nivel."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget, QLabel

_LEVEL_COLORS = {
    "INFO": "#8be9fd",
    "WARN": "#f1fa8c",
    "ERROR": "#ff5555",
    "CHAT": "#50fa7b",
    "DEBUG": "#6272a4",
}


class LogPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("LOG")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMaximumBlockCount(2000)
        self.text_edit.setObjectName("LogView")
        layout.addWidget(self.text_edit)

    @Slot(str, str)
    def append_log(self, level: str, message: str) -> None:
        color = _LEVEL_COLORS.get(level.upper(), "#f8f8f2")
        timestamp = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:#6272a4">[{timestamp}]</span> ' \
               f'<span style="color:{color}; font-weight:bold">[{level.upper()}]</span> ' \
               f'<span style="color:#f8f8f2">{message}</span>'
        self.text_edit.appendHtml(html)
        scrollbar = self.text_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
