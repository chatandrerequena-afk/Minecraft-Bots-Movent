"""FollowController: hace que un conjunto de bots sigan a un jugador,
a otro bot, o a unas coordenadas fijas.

El seguimiento continuo (recalcular la posicion objetivo mientras se
mueve) se delega en el bridge Node.js, porque alli es donde vive la
posicion en tiempo real de jugadores y entidades (mineflayer la
actualiza por paquete). Este controlador solo decide QUE bots siguen a
QUE objetivo y se lo comunica al bridge; Python sigue siendo el que
decide "quien sigue a quien", cumpliendo con que la logica de alto
nivel resida en Python.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Union

from bots.bot_state import BotState
from core.exceptions import InvalidCommandError

if TYPE_CHECKING:
    from bots.minecraft_bot import MinecraftBot

Target = Union[str, int, tuple]


class FollowController:
    def follow_player(self, bots: Iterable["MinecraftBot"], player_name: str) -> None:
        for bot in bots:
            self._start_follow(bot, "player", player_name)

    def follow_bot(self, bots: Iterable["MinecraftBot"], leader: "MinecraftBot") -> None:
        for bot in bots:
            if bot.id == leader.id:
                continue  # un bot no se sigue a si mismo
            self._start_follow(bot, "bot", leader.id)

    def follow_coordinates(self, bots: Iterable["MinecraftBot"], x: float, y: float, z: float) -> None:
        for bot in bots:
            self._start_follow(bot, "coords", {"x": x, "y": y, "z": z})

    def stop(self, bots: Iterable["MinecraftBot"]) -> None:
        for bot in bots:
            bot.stop()

    def _start_follow(self, bot: "MinecraftBot", target_type: str, target) -> None:
        if target_type not in ("player", "bot", "coords"):
            raise InvalidCommandError(f"Tipo de objetivo de seguimiento invalido: {target_type}")
        bot.state = BotState.FOLLOWING
        bot.current_goal = f"follow:{target_type}:{target}"
        bot.task_status = "following"
        bot.manager.bridge.send(
            {
                "type": "follow",
                "botId": bot.id,
                "targetType": target_type,
                "target": target,
            }
        )
