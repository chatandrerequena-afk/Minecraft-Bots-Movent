"""Panel de SERVIDOR + CONTROL: conexion, reunir, formar, seguir,
movimiento, salto y mirar."""

from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from bots.bot_manager import BotManager
from config import config as default_config
from gui.dialogs import FollowDialog, FormationDialog, GatherDialog, LookDialog


class ControlPanel(QWidget):
    def __init__(self, manager: BotManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.manager = manager
        self.get_selected_ids: Callable[[], List[int]] = lambda: []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._build_server_group())
        layout.addWidget(self._build_control_group())
        layout.addWidget(self._build_movement_group())

    # ------------------------------------------------------------------
    def _build_server_group(self) -> QGroupBox:
        box = QGroupBox("SERVIDOR")
        grid = QGridLayout(box)

        grid.addWidget(QLabel("IP:"), 0, 0)
        self.ip_input = QLineEdit(default_config.minecraft_host)
        grid.addWidget(self.ip_input, 0, 1)

        grid.addWidget(QLabel("Puerto:"), 0, 2)
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(default_config.minecraft_port)
        grid.addWidget(self.port_input, 0, 3)

        grid.addWidget(QLabel("Bots:"), 0, 4)
        self.bot_count_input = QSpinBox()
        self.bot_count_input.setRange(1, default_config.max_bots)
        self.bot_count_input.setValue(default_config.bot_count)
        grid.addWidget(self.bot_count_input, 0, 5)

        self.btn_connect_all = QPushButton("\U0001F7E2 CONECTAR TODOS")
        self.btn_connect_all.setObjectName("PrimaryButton")
        self.btn_connect_all.clicked.connect(self._on_connect_all)
        grid.addWidget(self.btn_connect_all, 1, 0, 1, 3)

        self.btn_disconnect_all = QPushButton("\U0001F534 DESCONECTAR TODOS")
        self.btn_disconnect_all.setObjectName("DangerButton")
        self.btn_disconnect_all.clicked.connect(self.manager.disconnect_all)
        grid.addWidget(self.btn_disconnect_all, 1, 3, 1, 3)

        return box

    def _build_control_group(self) -> QGroupBox:
        box = QGroupBox("CONTROL")
        row = QHBoxLayout(box)

        btn_gather = QPushButton("\U0001F4CD REUNIR")
        btn_gather.clicked.connect(self._on_gather)
        row.addWidget(btn_gather)

        btn_form = QPushButton("\U0001F6E1 FORMAR")
        btn_form.clicked.connect(self._on_form)
        row.addWidget(btn_form)

        btn_follow = QPushButton("\U0001F463 SEGUIR")
        btn_follow.clicked.connect(self._on_follow)
        row.addWidget(btn_follow)

        btn_stop = QPushButton("\u270B DETENER")
        btn_stop.setObjectName("DangerButton")
        btn_stop.clicked.connect(self._on_stop)
        row.addWidget(btn_stop)

        return box

    def _build_movement_group(self) -> QGroupBox:
        box = QGroupBox("MOVIMIENTO / CABEZA")
        layout = QVBoxLayout(box)

        move_row = QHBoxLayout()
        btn_forward = QPushButton("\u2191 ADELANTE")
        btn_back = QPushButton("\u2193 ATRAS")
        btn_left = QPushButton("\u2190 IZQUIERDA")
        btn_right = QPushButton("\u2192 DERECHA")
        btn_jump = QPushButton("\u23EB SALTAR")

        btn_forward.clicked.connect(lambda: self._move("forward"))
        btn_back.clicked.connect(lambda: self._move("back"))
        btn_left.clicked.connect(lambda: self._move("left"))
        btn_right.clicked.connect(lambda: self._move("right"))
        btn_jump.clicked.connect(self._on_jump)

        for btn in (btn_forward, btn_back, btn_left, btn_right, btn_jump):
            move_row.addWidget(btn)
        layout.addLayout(move_row)

        look_row = QHBoxLayout()
        btn_look = QPushButton("\U0001F441 MIRAR")
        btn_sync = QPushButton("\U0001F504 SINCRONIZAR CABEZAS")
        btn_look.clicked.connect(self._on_look)
        btn_sync.clicked.connect(lambda: self.manager.sync_heads(self._target_bots()))
        look_row.addWidget(btn_look)
        look_row.addWidget(btn_sync)
        layout.addLayout(look_row)

        return box

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _target_bots(self):
        ids = self.get_selected_ids()
        if ids:
            return [self.manager.get_bot(i) for i in ids if self.manager.has_bot(i)]
        return self.manager.all_bots()

    def apply_server_config_to_bots(self) -> None:
        self.manager.config = self.manager.config.__class__(
            minecraft_host=self.ip_input.text().strip() or "127.0.0.1",
            minecraft_port=self.port_input.value(),
            minecraft_version=self.manager.config.minecraft_version,
            minecraft_auth=self.manager.config.minecraft_auth,
            bot_count=self.bot_count_input.value(),
            bot_prefix=self.manager.config.bot_prefix,
            formation_columns=self.manager.config.formation_columns,
            formation_rows=self.manager.config.formation_rows,
            formation_spacing=self.manager.config.formation_spacing,
            bridge_host=self.manager.config.bridge_host,
            bridge_port=self.manager.config.bridge_port,
        )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_connect_all(self) -> None:
        self.apply_server_config_to_bots()
        self.manager.create_bots(self.bot_count_input.value())
        if hasattr(self.window(), "bot_panel"):
            self.window().bot_panel.rebuild()
        self.manager.connect_all()

    def _on_gather(self) -> None:
        names = [(b.id, b.name) for b in self.manager.all_bots()]
        dialog = GatherDialog(names, parent=self)
        if dialog.exec() != GatherDialog.Accepted:
            return
        data = dialog.result_data()
        bots = self._target_bots()
        if data["mode"] == "coords":
            anchor = (data["x"], data["y"], data["z"])
        elif data["mode"] == "bot":
            leader = self.manager.get_bot(data["bot_id"])
            anchor = (leader.x, leader.y, leader.z)
        else:  # player: sin tracking de posicion de jugador en Python,
            # se pide al bridge que centre la reunion en el jugador via
            # coordenadas actuales del primer bot como fallback visible,
            # y ademas se emite un "follow" corto hacia el jugador.
            self.manager.follow(bots, "player", data["player"])
            return
        self.manager.gather(bots, anchor)

    def _on_form(self) -> None:
        dialog = FormationDialog(
            columns=self.manager.config.formation_columns,
            rows=self.manager.config.formation_rows,
            spacing=self.manager.config.formation_spacing,
            parent=self,
        )
        if dialog.exec() != FormationDialog.Accepted:
            return
        data = dialog.result_data()
        bots = self._target_bots()
        self.manager.form(
            bots,
            columns=data["columns"],
            rows=data["rows"],
            spacing=data["spacing"],
            anchor=data["anchor"],
            orientation_deg=data["orientation_deg"],
        )

    def _on_follow(self) -> None:
        names = [(b.id, b.name) for b in self.manager.all_bots()]
        dialog = FollowDialog(names, parent=self)
        if dialog.exec() != FollowDialog.Accepted:
            return
        data = dialog.result_data()
        bots = self._target_bots()
        if data["mode"] == "player":
            self.manager.follow(bots, "player", data["player"])
        elif data["mode"] == "bot":
            self.manager.follow(bots, "bot", data["bot_id"])
        else:
            self.manager.follow(bots, "coords", (data["x"], data["y"], data["z"]))

    def _on_stop(self) -> None:
        self.manager.stop_bots(self._target_bots())

    def _on_jump(self) -> None:
        self.manager.jump_all(self._target_bots())

    def _move(self, direction: str) -> None:
        self.manager.move_direction(self._target_bots(), direction)

    def _on_look(self) -> None:
        dialog = LookDialog(parent=self)
        if dialog.exec() != LookDialog.Accepted:
            return
        data = dialog.result_data()
        bots = self._target_bots()
        if data["mode"] == "center":
            self.manager.look_at_center(bots)
        else:
            self.manager.look_at(bots, data["x"], data["y"], data["z"])
