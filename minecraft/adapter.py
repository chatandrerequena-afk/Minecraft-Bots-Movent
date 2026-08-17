"""Adaptador de transporte entre Python y el bridge Node.js/mineflayer.

Toda la logica de alto nivel (formaciones, seguimiento, GUI, etc.) vive
en Python. Este modulo es el UNICO punto que sabe hablar el protocolo
JSON sobre WebSocket con bridge/bridge.js. Si en el futuro cambias de
tecnologia de bridge (u otra libreria distinta de mineflayer), solo
tendrias que tocar este archivo.

La conexion WebSocket corre en un hilo propio con su propio event loop
de asyncio, para que la GUI de Qt (PySide6) nunca se bloquee esperando
a la red. La comunicacion hacia la GUI se hace mediante senales Qt,
que son seguras para cruzar hilos.
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Optional

import websockets
from PySide6.QtCore import QObject, QThread, Signal

from config import config
from core.exceptions import BridgeConnectionError
from core.logger import logger


class _AsyncLoopThread(QThread):
    """Hilo que ejecuta un event loop de asyncio en segundo plano."""

    def __init__(self) -> None:
        super().__init__()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._ready = threading.Event()

    def run(self) -> None:  # noqa: D102 - override de QThread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._ready.set()
        self.loop.run_forever()
        self.loop.close()

    def wait_ready(self, timeout: float = 5.0) -> None:
        self._ready.wait(timeout)

    def stop(self) -> None:
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self.wait(3000)


class BridgeClient(QObject):
    """Cliente WebSocket hacia bridge/bridge.js.

    Uso tipico:
        bridge = BridgeClient()
        bridge.message_received.connect(mi_slot)
        bridge.start()
        bridge.send({"type": "connect", "botId": 1, ...})
    """

    message_received = Signal(dict)
    connection_state_changed = Signal(bool, str)

    def __init__(self, url: Optional[str] = None) -> None:
        super().__init__()
        self.url = url or config.bridge_url()
        self._thread = _AsyncLoopThread()
        self._ws = None
        self._connected = False

    # --- ciclo de vida -------------------------------------------------
    def start(self) -> None:
        self._thread.start()
        self._thread.wait_ready()
        if not self._thread.loop:
            raise BridgeConnectionError("No se pudo iniciar el hilo del bridge")
        asyncio.run_coroutine_threadsafe(self._connect(), self._thread.loop)

    def stop(self) -> None:
        if self._ws is not None and self._thread.loop and self._thread.loop.is_running():
            fut = asyncio.run_coroutine_threadsafe(self._safe_close(), self._thread.loop)
            try:
                fut.result(timeout=2)
            except Exception:  # noqa: BLE001
                pass
        self._thread.stop()

    async def _safe_close(self) -> None:
        try:
            await self._ws.close()
        except Exception:  # noqa: BLE001
            pass

    # --- conexion / escucha ---------------------------------------------
    async def _connect(self) -> None:
        try:
            self._ws = await websockets.connect(self.url, max_size=None, ping_interval=20)
            self._connected = True
            self.connection_state_changed.emit(True, f"Conectado al bridge en {self.url}")
            asyncio.create_task(self._listen())
        except Exception as exc:  # noqa: BLE001
            self._connected = False
            self.connection_state_changed.emit(False, str(exc))
            logger.error("No se pudo conectar al bridge (%s): %s", self.url, exc)

    async def _listen(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    logger.warning("Mensaje no-JSON recibido del bridge: %s", raw)
                    continue
                self.message_received.emit(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Conexion con el bridge finalizada: %s", exc)
        finally:
            self._connected = False
            self.connection_state_changed.emit(False, "Conexion con el bridge cerrada")

    # --- envio -----------------------------------------------------------
    def send(self, payload: dict) -> None:
        """Encola un envio de forma thread-safe. No bloquea nunca al llamador."""
        if not self._thread.loop:
            logger.warning("send() llamado antes de start(): %s", payload)
            return
        asyncio.run_coroutine_threadsafe(self._send_async(payload), self._thread.loop)

    async def _send_async(self, payload: dict) -> None:
        if not self._ws or not self._connected:
            logger.warning("Intento de enviar al bridge sin conexion activa: %s", payload)
            return
        try:
            await self._ws.send(json.dumps(payload))
        except Exception as exc:  # noqa: BLE001
            logger.error("Error enviando mensaje al bridge: %s", exc)

    def is_connected(self) -> bool:
        return self._connected
