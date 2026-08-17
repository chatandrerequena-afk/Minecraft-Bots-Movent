"""MovementController: abstraccion de movimiento de alto nivel.

En esta primera version el movimiento fisico real (caminar hasta un
punto) lo ejecuta mineflayer del lado del bridge (ver bridge/bridge.js,
funcion moveTo), que empuja al bot hacia el objetivo sin usar
teletransporte. Este controlador SOLO decide "a donde debe ir cada
bot" y llama a bot.move_to(x, y, z).

Cuando en el futuro quieras integrar un pathfinder real (Baritone-like,
mineflayer-pathfinder, etc.), este es el unico sitio que tendrias que
sustituir: el resto del programa (formaciones, seguimiento, GUI) solo
conoce esta interfaz.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Iterable, Tuple

if TYPE_CHECKING:
    from bots.minecraft_bot import MinecraftBot

# Direcciones relativas simples en el plano XZ. No dependen del yaw del
# bot: son relativas al mundo, que es lo mas predecible para un
# prototipo controlado desde una GUI.
_DIRECTIONS = {
    "forward": (0, 0, -1),
    "back": (0, 0, 1),
    "left": (-1, 0, 0),
    "right": (1, 0, 0),
}

DEFAULT_STEP = 3.0


class MovementController:
    """Movimiento colectivo o individual de bots."""

    def move_direction(self, bots: Iterable["MinecraftBot"], direction: str, step: float = DEFAULT_STEP) -> None:
        if direction not in _DIRECTIONS:
            raise ValueError(f"Direccion desconocida: {direction}")
        dx, _, dz = _DIRECTIONS[direction]
        for bot in bots:
            target_x = bot.x + dx * step
            target_z = bot.z + dz * step
            bot.move_to(target_x, bot.y, target_z)

    def move_to(self, bots: Iterable["MinecraftBot"], x: float, y: float, z: float) -> None:
        for bot in bots:
            bot.move_to(x, y, z)

    def move_to_offsets(self, bots_with_targets: Iterable[Tuple["MinecraftBot", float, float, float]]) -> None:
        """Envia cada bot a unas coordenadas absolutas distintas (usado
        por FormationController y GatherController)."""
        for bot, x, y, z in bots_with_targets:
            bot.move_to(x, y, z)

    def stop(self, bots: Iterable["MinecraftBot"]) -> None:
        for bot in bots:
            bot.stop()

    def jump(self, bots: Iterable["MinecraftBot"]) -> None:
        for bot in bots:
            bot.jump()

    @staticmethod
    def distance(bot: "MinecraftBot", x: float, y: float, z: float) -> float:
        return math.dist((bot.x, bot.y, bot.z), (x, y, z))
