"""EventBus muy simple (patron publish/subscribe).

No depende de Qt para que pueda usarse tambien desde codigo Python
puro (tests, scripts, futuras clases del usuario). La integracion con
la GUI se hace reenviando estos eventos a senales Qt thread-safe.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict, List

Callback = Callable[..., None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[Callback]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callback) -> None:
        self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callback) -> None:
        if callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)

    def emit(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        for callback in list(self._subscribers.get(event_name, [])):
            try:
                callback(*args, **kwargs)
            except Exception:  # noqa: BLE001
                from core.logger import logger

                logger.exception("Error en listener de evento '%s'", event_name)


event_bus = EventBus()
