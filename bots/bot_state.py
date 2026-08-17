"""Estados posibles de un MinecraftBot."""

from __future__ import annotations

from enum import Enum


class BotState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    SPAWNED = "SPAWNED"
    MOVING = "MOVING"
    FORMING = "FORMING"
    FOLLOWING = "FOLLOWING"
    ERROR = "ERROR"

    def emoji(self) -> str:
        return {
            BotState.DISCONNECTED: "⚫",
            BotState.CONNECTING: "🟡",
            BotState.CONNECTED: "🟢",
            BotState.SPAWNED: "🟢",
            BotState.MOVING: "🔵",
            BotState.FORMING: "🔵",
            BotState.FOLLOWING: "🔵",
            BotState.ERROR: "❌",
        }[self]
