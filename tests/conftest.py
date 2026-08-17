"""Fixtures compartidas para los tests.

Los tests NO abren conexiones de red reales: usan un DummyBridge que
implementa la misma interfaz que minecraft.adapter.BridgeClient
(metodo send()) pero solo guarda los mensajes en una lista, para poder
comprobar que BotManager/controllers generan los payloads correctos
sin necesitar el bridge Node.js ni un servidor de Minecraft.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import Config  # noqa: E402


class DummyBridge:
    """Sustituye a BridgeClient en los tests: no abre sockets."""

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self._connected = True

    def send(self, payload: dict) -> None:
        self.sent.append(payload)

    def is_connected(self) -> bool:
        return self._connected

    # Las siguientes señales existen en BridgeClient real (QObject);
    # aqui basta con no fallar si algo intenta usarlas en tests futuros.
    class _FakeSignal:
        def connect(self, *_args, **_kwargs):
            return None

    message_received = _FakeSignal()
    connection_state_changed = _FakeSignal()

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass


@pytest.fixture
def test_config() -> Config:
    return Config(
        minecraft_host="127.0.0.1",
        minecraft_port=25565,
        bot_count=30,
        bot_prefix="Bot_",
        formation_columns=6,
        formation_rows=5,
        formation_spacing=1.5,
        bridge_host="127.0.0.1",
        bridge_port=8765,
    )


@pytest.fixture
def dummy_bridge() -> DummyBridge:
    return DummyBridge()


@pytest.fixture
def manager(test_config, dummy_bridge, qtbot):
    from bots.bot_manager import BotManager

    m = BotManager(app_config=test_config, bridge=dummy_bridge)
    return m
