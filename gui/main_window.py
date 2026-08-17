"""Ventana principal: ensambla SERVIDOR/CONTROL, BOTS, CHAT/COMANDOS y LOG."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QSplitter, QVBoxLayout, QWidget

from bots.bot_manager import BotManager
from config import config
from gui.bot_panel import BotPanel
from gui.command_panel import CommandPanel
from gui.control_panel import ControlPanel
from gui.log_panel import LogPanel

DARK_STYLE = """
QWidget {
    background-color: #1e1f29;
    color: #f8f8f2;
    font-family: 'Segoe UI', 'Cantarell', sans-serif;
    font-size: 13px;
}
QMainWindow { background-color: #191a21; }
QGroupBox {
    border: 1px solid #383a4a;
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #bd93f9;
}
QLabel#SectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #bd93f9;
    padding: 4px 0;
}
QLabel#HintLabel { color: #6272a4; font-style: italic; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #282a36;
    border: 1px solid #44475a;
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: #6272a4;
}
QPushButton {
    background-color: #44475a;
    border: none;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover { background-color: #565a72; }
QPushButton:pressed { background-color: #6272a4; }
QPushButton#PrimaryButton { background-color: #50fa7b; color: #191a21; }
QPushButton#PrimaryButton:hover { background-color: #6bffb1; }
QPushButton#DangerButton { background-color: #ff5555; color: #191a21; }
QPushButton#DangerButton:hover { background-color: #ff7b7b; }
QTableWidget {
    background-color: #282a36;
    gridline-color: #383a4a;
    border: 1px solid #383a4a;
    border-radius: 6px;
}
QHeaderView::section {
    background-color: #343646;
    color: #bd93f9;
    padding: 6px;
    border: none;
    font-weight: 700;
}
QPlainTextEdit#LogView {
    background-color: #10111a;
    border: 1px solid #383a4a;
    border-radius: 6px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}
QSplitter::handle { background-color: #191a21; }
"""


class MainWindow(QMainWindow):
    def __init__(self, manager: BotManager) -> None:
        super().__init__()
        self.manager = manager
        self.setWindowTitle("MINECRAFT BOT CONTROL")
        self.resize(1180, 900)
        self.setStyleSheet(DARK_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        header = QLabel("MINECRAFT BOT CONTROL")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 22px; font-weight: 800; color: #f8f8f2; padding: 6px;")
        outer.addWidget(header)

        self.control_panel = ControlPanel(manager)
        outer.addWidget(self.control_panel)

        self.command_panel = CommandPanel(manager)
        outer.addWidget(self.command_panel)

        splitter = QSplitter(Qt.Vertical)
        self.bot_panel = BotPanel(manager)
        self.log_panel = LogPanel()
        splitter.addWidget(self.bot_panel)
        splitter.addWidget(self.log_panel)
        splitter.setSizes([500, 300])
        outer.addWidget(splitter, stretch=1)

        # Selecciones de la tabla de bots alimentan a control/comandos
        self.control_panel.get_selected_ids = self.bot_panel.selected_bot_ids
        self.command_panel.get_selected_ids = self.bot_panel.selected_bot_ids

        # Senales del manager -> GUI (siempre via signals, thread-safe)
        self.manager.bot_updated.connect(self.bot_panel.refresh_bot)
        self.manager.bot_updated.connect(self._on_any_bot_updated)
        self.manager.log_message.connect(self.log_panel.append_log)
        self.manager.bridge_state_changed.connect(self._on_bridge_state_changed)

        self.log_panel.append_log("INFO", "Interfaz iniciada. Configura el servidor y pulsa CONECTAR TODOS.")

    def _on_any_bot_updated(self, _bot_id: int) -> None:
        self.command_panel.refresh_bot_targets()

    def _on_bridge_state_changed(self, connected: bool, detail: str) -> None:
        state = "conectado" if connected else "desconectado"
        self.setWindowTitle(f"MINECRAFT BOT CONTROL — bridge {state}")

    def closeEvent(self, event) -> None:  # noqa: N802 - override Qt
        self.manager.shutdown()
        super().closeEvent(event)
