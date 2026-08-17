"""Representacion en Python de un bot de Minecraft.

MinecraftBot es un objeto de ESTADO + una fachada comoda para pedirle
acciones. La ejecucion real (mineflayer) vive al otro lado del bridge
Node.js; este objeto nunca habla directamente con el bridge, siempre
lo hace a traves de la referencia a BotManager, que es quien conoce el
BridgeClient. Esto mantiene MinecraftBot facil de testear sin red.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, Tuple

from bots.bot_state import BotState

if TYPE_CHECKING:  # evita import circular en tiempo de ejecucion
    from bots.bot_manager import BotManager


@dataclass
class MinecraftBot:
    id: int
    name: str
    manager: "BotManager"

    state: BotState = BotState.DISCONNECTED
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    pitch: float = 0.0
    health: float = 20.0
    food: float = 20.0

    current_goal: Optional[str] = None
    task_status: str = "idle"
    last_error: Optional[str] = None

    # --- helpers de estado -------------------------------------------------
    @property
    def position(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @property
    def is_connected(self) -> bool:
        return self.state not in (BotState.DISCONNECTED, BotState.CONNECTING, BotState.ERROR)

    def apply_status(self, state: BotState, error: Optional[str] = None) -> None:
        self.state = state
        self.last_error = error
        if state == BotState.ERROR:
            self.task_status = "error"
        elif state == BotState.DISCONNECTED:
            self.task_status = "idle"
            self.current_goal = None

    def apply_position(self, x: float, y: float, z: float, yaw: float, pitch: float) -> None:
        self.x, self.y, self.z = x, y, z
        self.yaw, self.pitch = yaw, pitch

    def apply_health(self, health: float, food: float) -> None:
        self.health, self.food = health, food

    # --- API de alto nivel: delega en el manager/bridge ---------------------
    def connect(self) -> None:
        self.manager.connect_bot(self.id)

    def disconnect(self) -> None:
        self.manager.disconnect_bot(self.id)

    def jump(self) -> None:
        self.manager.bridge.send({"type": "jump", "botId": self.id})

    def look_at(self, x: float, y: float, z: float) -> None:
        self.manager.bridge.send({"type": "look_at", "botId": self.id, "x": x, "y": y, "z": z})

    def move_to(self, x: float, y: float, z: float) -> None:
        self.current_goal = f"move_to({x:.1f},{y:.1f},{z:.1f})"
        self.state = BotState.MOVING
        self.task_status = "moving"
        self.manager.bridge.send({"type": "move_to", "botId": self.id, "x": x, "y": y, "z": z})

    def stop(self) -> None:
        self.current_goal = None
        self.task_status = "idle"
        self.manager.bridge.send({"type": "stop", "botId": self.id})

    def send_chat(self, message: str) -> None:
        self.manager.bridge.send({"type": "chat", "botId": self.id, "message": message})

    def send_command(self, command: str) -> None:
        self.manager.bridge.send({"type": "command", "botId": self.id, "command": command})

    def __repr__(self) -> str:  # pragma: no cover - solo depuracion
        return f"<MinecraftBot #{self.id} {self.name} state={self.state.value}>"
