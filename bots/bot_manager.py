"""BotManager: administra hasta N bots de Minecraft.

Es el punto central de la arquitectura:
  - Crea y guarda las instancias de MinecraftBot.
  - Posee el BridgeClient (conexion WebSocket al bridge Node.js) y es
    el UNICO objeto que escucha sus mensajes.
  - Traduce esos mensajes en actualizaciones de estado de cada bot y
    emite senales Qt (bot_updated, log_message) para que la GUI se
    refresque sin bloquear.
  - Expone la API de alto nivel en Python que se pide en el prompt:
        manager.start_all()
        manager.stop_all()
        manager.get_bot(1)
        manager.get_bot(1).jump()
        manager.broadcast_chat(...)
        manager.broadcast_command(...)
        manager.follow(...)
        manager.form(...)
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

from PySide6.QtCore import QObject, Signal

from bots.bot_group import BotGroup
from bots.bot_state import BotState
from bots.minecraft_bot import MinecraftBot
from config import Config, config as default_config
from controllers.command_controller import CommandController
from controllers.follow_controller import FollowController
from controllers.formation_controller import FormationController
from controllers.look_controller import LookController
from controllers.movement_controller import MovementController
from core.exceptions import BotNotFoundError
from core.logger import logger
from minecraft.adapter import BridgeClient


class BotManager(QObject):
    # bot_id afectado -> la GUI relee el estado actual del bot desde el manager
    bot_updated = Signal(int)
    log_message = Signal(str, str)  # nivel, mensaje
    bridge_state_changed = Signal(bool, str)

    def __init__(self, app_config: Optional[Config] = None, bridge: Optional[BridgeClient] = None):
        super().__init__()
        self.config = app_config or default_config
        self.bots: Dict[int, MinecraftBot] = {}

        self.bridge = bridge or BridgeClient(self.config.bridge_url())
        self.bridge.message_received.connect(self._on_bridge_message)
        self.bridge.connection_state_changed.connect(self._on_bridge_state_changed)

        self.movement = MovementController()
        self.formation = FormationController(self.movement)
        self.follow_controller = FollowController()
        self.look = LookController()
        self.commands = CommandController()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def start_bridge(self) -> None:
        self.bridge.start()

    def shutdown(self) -> None:
        try:
            self.stop_all()
            self.disconnect_all()
        finally:
            self.bridge.stop()

    # ------------------------------------------------------------------
    # Creacion / consulta de bots
    # ------------------------------------------------------------------
    def create_bots(self, count: int, prefix: Optional[str] = None) -> None:
        count = max(0, min(count, self.config.max_bots))
        prefix = prefix or self.config.bot_prefix
        self.bots.clear()
        for i in range(1, count + 1):
            name = f"{prefix}{i:02d}"
            self.bots[i] = MinecraftBot(id=i, name=name, manager=self)
        self.log_message.emit("INFO", f"Creados {count} bots ({prefix}01..{prefix}{count:02d})")

    def get_bot(self, bot_id: int) -> MinecraftBot:
        if bot_id not in self.bots:
            raise BotNotFoundError(bot_id)
        return self.bots[bot_id]

    def has_bot(self, bot_id: int) -> bool:
        return bot_id in self.bots

    def all_bots(self) -> List[MinecraftBot]:
        return list(self.bots.values())

    def make_group(self, bot_ids: Sequence[int], name: str = "group") -> BotGroup:
        return BotGroup(self, bot_ids, name=name)

    # ------------------------------------------------------------------
    # Conexion (concurrente: sin esperas artificiales entre bots)
    # ------------------------------------------------------------------
    def start_all(self) -> None:
        self.connect_all()

    def connect_all(self) -> None:
        if not self.bots:
            self.log_message.emit("WARN", "No hay bots creados todavia")
            return
        self.log_message.emit(
            "INFO", f"Conectando {len(self.bots)} bots simultaneamente a "
                    f"{self.config.minecraft_host}:{self.config.minecraft_port}..."
        )
        for bot in self.bots.values():
            self.connect_bot(bot.id)

    def connect_bot(self, bot_id: int) -> None:
        bot = self.get_bot(bot_id)
        bot.apply_status(BotState.CONNECTING)
        self.bot_updated.emit(bot_id)
        self.bridge.send(
            {
                "type": "connect",
                "botId": bot.id,
                "name": bot.name,
                "host": self.config.minecraft_host,
                "port": self.config.minecraft_port,
                "version": self.config.minecraft_version,
                "auth": self.config.minecraft_auth,
            }
        )

    def stop_all(self) -> None:
        for bot in self.bots.values():
            bot.stop()

    def disconnect_all(self) -> None:
        for bot in self.bots.values():
            self.disconnect_bot(bot.id)

    def disconnect_bot(self, bot_id: int) -> None:
        bot = self.get_bot(bot_id)
        self.bridge.send({"type": "disconnect", "botId": bot_id})
        bot.apply_status(BotState.DISCONNECTED)
        self.bot_updated.emit(bot_id)

    # ------------------------------------------------------------------
    # Chat / comandos
    # ------------------------------------------------------------------
    def broadcast_chat(self, message: str) -> None:
        for bot in self.bots.values():
            bot.send_chat(message)

    def broadcast_command(self, command: str) -> None:
        for bot in self.bots.values():
            bot.send_command(command)

    def send_chat(self, bot_id: int, message: str) -> None:
        self.get_bot(bot_id).send_chat(message)

    def send_command(self, bot_id: int, command: str) -> None:
        self.get_bot(bot_id).send_command(command)

    def dispatch_input(self, raw_text: str, target="ALL", group_ids: Optional[list] = None):
        return self.commands.dispatch(self, raw_text, target=target, group_ids=group_ids)

    # ------------------------------------------------------------------
    # Reunir / Formar / Seguir / Mirar
    # ------------------------------------------------------------------
    def gather(self, bots: Sequence[MinecraftBot], anchor: tuple, spacing: float = 1.5) -> None:
        """REUNIR: agrupa a los bots en una pequenya cuadricula compacta
        alrededor del ancla (jugador, coordenadas o bot seleccionado),
        reutilizando la misma matematica que FormationController para
        que el codigo no se duplique."""
        n = len(bots)
        if n == 0:
            return
        columns = max(1, math.ceil(math.sqrt(n)))
        rows = max(1, math.ceil(n / columns))
        for bot in bots:
            bot.state = BotState.MOVING
        self.formation.form(bots, columns=columns, rows=rows, spacing=spacing, anchor=anchor)
        self.log_message.emit("INFO", f"REUNIR: {n} bots convergiendo en {anchor}")

    def form(
        self,
        bots: Sequence[MinecraftBot],
        columns: int,
        rows: int,
        spacing: float = 1.5,
        anchor: tuple = (0.0, 64.0, 0.0),
        orientation_deg: float = 0.0,
    ) -> None:
        for bot in bots:
            bot.state = BotState.FORMING
        self.formation.form(bots, columns=columns, rows=rows, spacing=spacing, anchor=anchor, orientation_deg=orientation_deg)
        self.log_message.emit("INFO", f"FORMAR: {len(bots)} bots en formacion {columns}x{rows}")

    def follow(self, bots: Sequence[MinecraftBot], target_type: str, target) -> None:
        if target_type == "player":
            self.follow_controller.follow_player(bots, target)
        elif target_type == "bot":
            leader = target if isinstance(target, MinecraftBot) else self.get_bot(int(target))
            self.follow_controller.follow_bot(bots, leader)
        elif target_type == "coords":
            x, y, z = target
            self.follow_controller.follow_coordinates(bots, x, y, z)
        else:
            raise ValueError(f"target_type desconocido: {target_type}")
        self.log_message.emit("INFO", f"SEGUIR: {len(bots)} bots -> {target_type}:{target}")

    def look_at(self, bots: Sequence[MinecraftBot], x: float, y: float, z: float) -> None:
        self.look.look_at_point(bots, x, y, z)

    def look_at_center(self, bots: Sequence[MinecraftBot]) -> None:
        self.look.look_at_center(bots)

    def sync_heads(self, bots: Sequence[MinecraftBot]) -> None:
        if not bots:
            return
        reference = (bots[0].x, bots[0].y, bots[0].z)
        self.look.sync_heads(bots, reference)

    def jump_all(self, bots: Optional[Sequence[MinecraftBot]] = None) -> None:
        target_bots = list(bots) if bots is not None else self.all_bots()
        self.movement.jump(target_bots)
        self.log_message.emit("INFO", f"SALTAR: {len(target_bots)} bots saltando de forma coordinada")

    def move_direction(self, bots: Sequence[MinecraftBot], direction: str, step: float = 3.0) -> None:
        self.movement.move_direction(bots, direction, step=step)

    def stop_bots(self, bots: Sequence[MinecraftBot]) -> None:
        self.movement.stop(bots)

    # ------------------------------------------------------------------
    # Mensajes entrantes del bridge
    # ------------------------------------------------------------------
    def _on_bridge_state_changed(self, connected: bool, detail: str) -> None:
        level = "INFO" if connected else "WARN"
        self.bridge_state_changed.emit(connected, detail)
        self.log_message.emit(level, detail)

    def _on_bridge_message(self, data: dict) -> None:
        msg_type = data.get("type")
        bot_id = data.get("botId")

        if msg_type == "status":
            self._handle_status(bot_id, data)
        elif msg_type == "position":
            self._handle_position(bot_id, data)
        elif msg_type == "health":
            self._handle_health(bot_id, data)
        elif msg_type == "chat":
            self._handle_chat(bot_id, data)
        elif msg_type == "spawn":
            self._handle_spawn(bot_id)
        elif msg_type == "goal_reached":
            self._handle_goal_reached(bot_id)
        elif msg_type == "error":
            self._handle_error(bot_id, data)
        elif msg_type == "bridge_log":
            self.log_message.emit(data.get("level", "INFO"), str(data.get("message", "")))
        else:
            logger.debug("Mensaje de bridge no reconocido: %s", data)

    def _handle_status(self, bot_id: int, data: dict) -> None:
        if not self.has_bot(bot_id):
            return
        bot = self.get_bot(bot_id)
        state_str = data.get("state", "ERROR")
        try:
            new_state = BotState(state_str)
        except ValueError:
            new_state = BotState.ERROR
        error = data.get("error")
        bot.apply_status(new_state, error=error)
        self.bot_updated.emit(bot_id)

        name = bot.name
        if new_state == BotState.CONNECTED or new_state == BotState.SPAWNED:
            self.log_message.emit("INFO", f"{name} conectado correctamente")
        elif new_state == BotState.ERROR:
            self.log_message.emit("ERROR", f"{name} fallo: {error}")
        elif new_state == BotState.DISCONNECTED:
            self.log_message.emit("INFO", f"{name} desconectado")

    def _handle_position(self, bot_id: int, data: dict) -> None:
        if not self.has_bot(bot_id):
            return
        bot = self.get_bot(bot_id)
        bot.apply_position(
            data.get("x", bot.x),
            data.get("y", bot.y),
            data.get("z", bot.z),
            data.get("yaw", bot.yaw),
            data.get("pitch", bot.pitch),
        )
        self.bot_updated.emit(bot_id)

    def _handle_health(self, bot_id: int, data: dict) -> None:
        if not self.has_bot(bot_id):
            return
        bot = self.get_bot(bot_id)
        bot.apply_health(data.get("health", bot.health), data.get("food", bot.food))
        self.bot_updated.emit(bot_id)

    def _handle_chat(self, bot_id: int, data: dict) -> None:
        name = self.get_bot(bot_id).name if self.has_bot(bot_id) else f"bot#{bot_id}"
        self.log_message.emit("CHAT", f"{name}: {data.get('message', '')}")

    def _handle_spawn(self, bot_id: int) -> None:
        if not self.has_bot(bot_id):
            return
        bot = self.get_bot(bot_id)
        bot.apply_status(BotState.SPAWNED)
        self.bot_updated.emit(bot_id)
        self.log_message.emit("INFO", f"{bot.name} ha aparecido (spawn) en el mundo")

    def _handle_goal_reached(self, bot_id: int) -> None:
        if not self.has_bot(bot_id):
            return
        bot = self.get_bot(bot_id)
        if bot.state in (BotState.MOVING, BotState.FORMING):
            bot.apply_status(BotState.SPAWNED)
            bot.task_status = "idle"
            bot.current_goal = None
            self.bot_updated.emit(bot_id)

    def _handle_error(self, bot_id: int, data: dict) -> None:
        message = data.get("message", "error desconocido")
        if self.has_bot(bot_id):
            bot = self.get_bot(bot_id)
            bot.apply_status(BotState.ERROR, error=message)
            self.bot_updated.emit(bot_id)
            self.log_message.emit("ERROR", f"{bot.name}: {message}")
        else:
            self.log_message.emit("ERROR", f"bot#{bot_id}: {message}")
