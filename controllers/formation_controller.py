"""FormationController: calculo y aplicacion de formaciones en cuadricula.

La formacion NO esta escrita especificamente para 30 bots: funciona
matematicamente para cualquier combinacion de columns x rows y para
cualquier cantidad de bots (si sobran o faltan bots respecto a
columns*rows, simplemente se reparten en la cuadricula por orden).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Sequence, Tuple

from core.exceptions import FormationError
from core.logger import logger

if TYPE_CHECKING:
    from bots.minecraft_bot import MinecraftBot
    from controllers.movement_controller import MovementController


@dataclass
class Formation:
    columns: int = 6
    rows: int = 5
    spacing: float = 1.5
    orientation_deg: float = 0.0  # rotacion de la cuadricula alrededor del ancla

    def __post_init__(self) -> None:
        if self.columns <= 0 or self.rows <= 0:
            raise FormationError("columns y rows deben ser mayores que 0")
        if self.spacing <= 0:
            raise FormationError("spacing debe ser mayor que 0")

    @property
    def capacity(self) -> int:
        return self.columns * self.rows

    def local_slots(self) -> List[Tuple[float, float]]:
        """Devuelve las posiciones (dx, dz) de cada hueco de la formacion,
        centradas en (0, 0), en orden fila a fila (igual que el diagrama
        BOT BOT BOT... del prompt: primero se rellena la fila 0)."""
        slots: List[Tuple[float, float]] = []
        half_w = (self.columns - 1) / 2.0
        half_d = (self.rows - 1) / 2.0
        for row in range(self.rows):
            for col in range(self.columns):
                dx = (col - half_w) * self.spacing
                dz = (row - half_d) * self.spacing
                slots.append((dx, dz))
        return slots

    def world_slots(self, anchor_x: float, anchor_z: float) -> List[Tuple[float, float]]:
        angle = math.radians(self.orientation_deg)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        result = []
        for dx, dz in self.local_slots():
            rx = dx * cos_a - dz * sin_a
            rz = dx * sin_a + dz * cos_a
            result.append((anchor_x + rx, anchor_z + rz))
        return result


class FormationController:
    def __init__(self, movement_controller: "MovementController") -> None:
        self.movement = movement_controller
        self.current: Optional[Formation] = None

    def form(
        self,
        bots: Sequence["MinecraftBot"],
        columns: int,
        rows: int,
        spacing: float = 1.5,
        anchor: Tuple[float, float, float] = (0.0, 64.0, 0.0),
        orientation_deg: float = 0.0,
    ) -> Formation:
        formation = Formation(columns=columns, rows=rows, spacing=spacing, orientation_deg=orientation_deg)
        self.current = formation

        if len(bots) > formation.capacity:
            logger.warning(
                "La formacion %sx%s solo tiene %s huecos pero hay %s bots; "
                "los bots sobrantes se quedaran donde estan.",
                columns, rows, formation.capacity, len(bots),
            )

        anchor_x, anchor_y, anchor_z = anchor
        slots = formation.world_slots(anchor_x, anchor_z)

        for bot, (x, z) in zip(bots, slots):
            bot.move_to(x, anchor_y, z)

        return formation

    @staticmethod
    def compute_positions(
        columns: int, rows: int, spacing: float, anchor: Tuple[float, float, float] = (0.0, 64.0, 0.0)
    ) -> List[Tuple[float, float, float]]:
        """Utilidad pura (sin bots) para tests y para previsualizar la
        formacion en la GUI antes de aplicarla."""
        formation = Formation(columns=columns, rows=rows, spacing=spacing)
        anchor_x, anchor_y, anchor_z = anchor
        return [(x, anchor_y, z) for x, z in formation.world_slots(anchor_x, anchor_z)]
