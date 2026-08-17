"""LookController: orientacion de cabeza (yaw/pitch) de los bots."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Tuple

if TYPE_CHECKING:
    from bots.minecraft_bot import MinecraftBot


class LookController:
    def look_at_point(self, bots: Iterable["MinecraftBot"], x: float, y: float, z: float) -> None:
        for bot in bots:
            bot.look_at(x, y, z)

    def look_at_center(self, bots: Iterable["MinecraftBot"]) -> None:
        """Todos miran hacia el centroide del grupo actual (aproximacion
        util cuando no hay un objetivo concreto seleccionado)."""
        bots = list(bots)
        if not bots:
            return
        cx = sum(b.x for b in bots) / len(bots)
        cy = sum(b.y for b in bots) / len(bots)
        cz = sum(b.z for b in bots) / len(bots)
        self.look_at_point(bots, cx, cy, cz)

    def look_at_bot(self, bots: Iterable["MinecraftBot"], target: "MinecraftBot") -> None:
        self.look_at_point(bots, target.x, target.y, target.z)

    def sync_heads(self, bots: Iterable["MinecraftBot"], reference: Tuple[float, float, float]) -> None:
        """Todos los bots orientan la cabeza hacia el mismo punto de
        referencia, de forma que 'miren aproximadamente hacia la misma
        direccion' tal y como pide el prototipo."""
        x, y, z = reference
        self.look_at_point(bots, x, y, z)
