"""BotGroup: subconjunto de bots sobre el que se pueden aplicar
las mismas operaciones de broadcast que ofrece BotManager, pero
limitadas a un grupo (por ejemplo, para el selector "GRUPO" del
panel de comandos, o para futuras escuadras/equipos).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List

if TYPE_CHECKING:
    from bots.bot_manager import BotManager
    from bots.minecraft_bot import MinecraftBot


class BotGroup:
    def __init__(self, manager: "BotManager", bot_ids: Iterable[int], name: str = "group"):
        self.manager = manager
        self.name = name
        self.bot_ids: List[int] = list(bot_ids)

    def bots(self) -> List["MinecraftBot"]:
        return [self.manager.get_bot(bid) for bid in self.bot_ids if self.manager.has_bot(bid)]

    def add(self, bot_id: int) -> None:
        if bot_id not in self.bot_ids:
            self.bot_ids.append(bot_id)

    def remove(self, bot_id: int) -> None:
        if bot_id in self.bot_ids:
            self.bot_ids.remove(bot_id)

    def broadcast_chat(self, message: str) -> None:
        for bot in self.bots():
            bot.send_chat(message)

    def broadcast_command(self, command: str) -> None:
        for bot in self.bots():
            bot.send_command(command)

    def stop_all(self) -> None:
        for bot in self.bots():
            bot.stop()

    def __len__(self) -> int:
        return len(self.bot_ids)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<BotGroup {self.name} ids={self.bot_ids}>"
