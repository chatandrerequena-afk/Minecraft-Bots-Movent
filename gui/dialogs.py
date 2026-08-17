"""Dialogos auxiliares para recoger parametros de REUNIR, FORMAR, SEGUIR
y MIRAR sin saturar el panel principal de controles.

Nota sobre arquitectura: este archivo no aparecia en el arbol de
carpetas original propuesto en el prompt; se ha anyadido dentro de
gui/ porque estas ventanas son puramente de interfaz (recogen datos
del usuario) y así control_panel.py se mantiene centrado en layout y
señales, no en formularios emergentes.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)


def _coord_spinbox(default: float = 0.0) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(-30_000_000, 30_000_000)
    box.setDecimals(1)
    box.setValue(default)
    return box


class GatherDialog(QDialog):
    """REUNIR: alrededor del jugador / en coordenadas / alrededor de un bot."""

    def __init__(self, bot_names: List[Tuple[int, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reunir bots")
        self._bot_names = bot_names

        layout = QVBoxLayout(self)

        self.group = QButtonGroup(self)
        self.radio_player = QRadioButton("Alrededor del jugador")
        self.radio_coords = QRadioButton("En coordenadas")
        self.radio_bot = QRadioButton("Alrededor de un bot")
        self.radio_player.setChecked(True)
        for i, radio in enumerate((self.radio_player, self.radio_coords, self.radio_bot)):
            self.group.addButton(radio, i)
            layout.addWidget(radio)

        form = QFormLayout()
        self.player_name = QLineEdit("Steve")
        form.addRow("Jugador:", self.player_name)

        self.x = _coord_spinbox()
        self.y = _coord_spinbox(64.0)
        self.z = _coord_spinbox()
        form.addRow("X:", self.x)
        form.addRow("Y:", self.y)
        form.addRow("Z:", self.z)

        self.bot_combo = QComboBox()
        for bot_id, name in bot_names:
            self.bot_combo.addItem(name, bot_id)
        form.addRow("Bot:", self.bot_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_data(self) -> dict:
        if self.radio_player.isChecked():
            return {"mode": "player", "player": self.player_name.text().strip() or "Steve"}
        if self.radio_bot.isChecked():
            return {"mode": "bot", "bot_id": self.bot_combo.currentData()}
        return {"mode": "coords", "x": self.x.value(), "y": self.y.value(), "z": self.z.value()}


class FormationDialog(QDialog):
    """FORMAR: columnas, filas, separacion, ancla y orientacion."""

    def __init__(self, columns=6, rows=5, spacing=1.5, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Formar bots")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.columns = QSpinBox()
        self.columns.setRange(1, 30)
        self.columns.setValue(columns)
        form.addRow("Columnas:", self.columns)

        self.rows = QSpinBox()
        self.rows.setRange(1, 30)
        self.rows.setValue(rows)
        form.addRow("Filas:", self.rows)

        self.spacing = QDoubleSpinBox()
        self.spacing.setRange(0.5, 20.0)
        self.spacing.setSingleStep(0.5)
        self.spacing.setValue(spacing)
        form.addRow("Separacion:", self.spacing)

        self.orientation = QDoubleSpinBox()
        self.orientation.setRange(-360.0, 360.0)
        self.orientation.setValue(0.0)
        form.addRow("Orientacion (grados):", self.orientation)

        self.x = _coord_spinbox()
        self.y = _coord_spinbox(64.0)
        self.z = _coord_spinbox()
        form.addRow("Ancla X:", self.x)
        form.addRow("Ancla Y:", self.y)
        form.addRow("Ancla Z:", self.z)

        layout.addWidget(QLabel(f"Capacidad total = columnas x filas"))
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_data(self) -> dict:
        return {
            "columns": self.columns.value(),
            "rows": self.rows.value(),
            "spacing": self.spacing.value(),
            "orientation_deg": self.orientation.value(),
            "anchor": (self.x.value(), self.y.value(), self.z.value()),
        }


class FollowDialog(QDialog):
    """SEGUIR: jugador / bot lider / coordenadas."""

    def __init__(self, bot_names: List[Tuple[int, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seguir")
        layout = QVBoxLayout(self)

        self.group = QButtonGroup(self)
        self.radio_player = QRadioButton("Seguir a un jugador")
        self.radio_bot = QRadioButton("Seguir a un bot (lider)")
        self.radio_coords = QRadioButton("Seguir unas coordenadas fijas")
        self.radio_player.setChecked(True)
        for i, radio in enumerate((self.radio_player, self.radio_bot, self.radio_coords)):
            self.group.addButton(radio, i)
            layout.addWidget(radio)

        form = QFormLayout()
        self.player_name = QLineEdit("Steve")
        form.addRow("Jugador:", self.player_name)

        self.bot_combo = QComboBox()
        for bot_id, name in bot_names:
            self.bot_combo.addItem(name, bot_id)
        form.addRow("Bot lider:", self.bot_combo)

        self.x = _coord_spinbox()
        self.y = _coord_spinbox(64.0)
        self.z = _coord_spinbox()
        form.addRow("X:", self.x)
        form.addRow("Y:", self.y)
        form.addRow("Z:", self.z)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_data(self) -> dict:
        if self.radio_player.isChecked():
            return {"mode": "player", "player": self.player_name.text().strip() or "Steve"}
        if self.radio_bot.isChecked():
            return {"mode": "bot", "bot_id": self.bot_combo.currentData()}
        return {"mode": "coords", "x": self.x.value(), "y": self.y.value(), "z": self.z.value()}


class LookDialog(QDialog):
    """MIRAR: jugador / centro del grupo / coordenadas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mirar")
        layout = QVBoxLayout(self)

        self.group = QButtonGroup(self)
        self.radio_center = QRadioButton("Mirar al centro del grupo")
        self.radio_coords = QRadioButton("Mirar a coordenadas")
        self.radio_center.setChecked(True)
        for i, radio in enumerate((self.radio_center, self.radio_coords)):
            self.group.addButton(radio, i)
            layout.addWidget(radio)

        form = QFormLayout()
        self.x = _coord_spinbox()
        self.y = _coord_spinbox(64.0)
        self.z = _coord_spinbox()
        form.addRow("X:", self.x)
        form.addRow("Y:", self.y)
        form.addRow("Z:", self.z)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_data(self) -> dict:
        if self.radio_center.isChecked():
            return {"mode": "center"}
        return {"mode": "coords", "x": self.x.value(), "y": self.y.value(), "z": self.z.value()}
