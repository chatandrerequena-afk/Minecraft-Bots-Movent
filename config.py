"""Configuracion centralizada del proyecto.

Lee variables de entorno (desde .env si existe, usando python-dotenv)
y expone un objeto Config inmutable con valores por defecto sensatos.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:  # python-dotenv es opcional pero recomendado
    pass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Config:
    # Servidor de Minecraft
    minecraft_host: str = field(default_factory=lambda: _env_str("MINECRAFT_HOST", "127.0.0.1"))
    minecraft_port: int = field(default_factory=lambda: _env_int("MINECRAFT_PORT", 25565))
    minecraft_version: str = field(default_factory=lambda: _env_str("MINECRAFT_VERSION", "1.20.4"))
    minecraft_auth: str = field(default_factory=lambda: _env_str("MINECRAFT_AUTH", "offline"))

    # Bots
    bot_count: int = field(default_factory=lambda: _env_int("BOT_COUNT", 30))
    bot_prefix: str = field(default_factory=lambda: _env_str("BOT_PREFIX", "Bot_"))
    max_bots: int = 30

    # Formacion por defecto
    formation_columns: int = field(default_factory=lambda: _env_int("FORMATION_COLUMNS", 6))
    formation_rows: int = field(default_factory=lambda: _env_int("FORMATION_ROWS", 5))
    formation_spacing: float = field(default_factory=lambda: _env_float("FORMATION_SPACING", 1.5))

    # Bridge Node.js <-> Python
    bridge_host: str = field(default_factory=lambda: _env_str("BRIDGE_HOST", "127.0.0.1"))
    bridge_port: int = field(default_factory=lambda: _env_int("BRIDGE_PORT", 8765))

    def bridge_url(self) -> str:
        return f"ws://{self.bridge_host}:{self.bridge_port}"


config = Config()
