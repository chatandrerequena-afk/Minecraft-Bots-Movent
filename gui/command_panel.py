"""Panel CHAT / COMANDOS: caja de texto + selector "Enviar a"."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bots.bot_manager import BotManager
from core.exceptions import InvalidCommandError


class CommandPanel(QWidget):
    def __init__(self, manager: BotManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager

        box = QGroupBox("CHAT / COMANDOS")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(box)
        layout = QVBoxLayout(box)

        row = QHBoxLayout()
        row.addWidget(QLabel("Enviar a:"))
        self.target_combo = QComboBox()
        self.target_combo.addItem("TODOS", "ALL")
        self.target_combo.addItem("GRUPO (seleccion)", "GROUP")
        row.addWidget(self.target_combo)
        layout.addLayout(row)

        input_row = QHBoxLayout()
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText(
            "Escribe un mensaje, /comando, o usa !bots <mensaje|/comando> para todos..."
        )
        self.text_input.returnPressed.connect(self._on_send)
        input_row.addWidget(self.text_input)

        self.send_button = QPushButton("ENVIAR")
        self.send_button.setObjectName("PrimaryButton")
        self.send_button.clicked.connect(self._on_send)
        input_row.addWidget(self.send_button)
        layout.addLayout(input_row)

        example = QLabel(
            "Ejemplos:  Hola a todos   |   /spawn   |   /tp 100 64 -200   |   !bots /say Hola"
        )
        example.setObjectName("HintLabel")
        layout.addWidget(example)

        self.get_selected_ids = lambda: []

    def refresh_bot_targets(self) -> None:
        current = self.target_combo.currentData()
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem("TODOS", "ALL")
        self.target_combo.addItem("GRUPO (seleccion)", "GROUP")
        for bot in self.manager.all_bots():
            self.target_combo.addItem(bot.name, bot.id)
        idx = self.target_combo.findData(current)
        self.target_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.target_combo.blockSignals(False)

    def _on_send(self) -> None:
        text = self.text_input.text()
        if not text.strip():
            return
        target = self.target_combo.currentData()
        try:
            parsed = self.manager.dispatch_input(
                text, target=target, group_ids=self.get_selected_ids()
            )
        except InvalidCommandError as exc:
            self.manager.log_message.emit("WARN", str(exc))
            return

        kind_label = "comando" if parsed.kind == "command" else "chat"
        destino = "TODOS" if (target == "ALL" or parsed.force_all) else str(target)
        self.manager.log_message.emit("INFO", f"Enviado {kind_label} a {destino}: {parsed.payload}")
        self.text_input.clear()
