"""Punto de entrada de la aplicacion.

IMPORTANTE: antes de ejecutar este archivo, el bridge Node.js debe
estar corriendo (ver README, seccion "Instalacion" y "Ejecutar"):

    cd bridge
    npm install
    npm start

Ese bridge escucha WebSocket en BRIDGE_HOST:BRIDGE_PORT (por defecto
127.0.0.1:8765) y es quien realmente habla el protocolo de Minecraft
via mineflayer. Este main.py solo levanta la GUI de Python y la
conecta a ese bridge.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from bots.bot_manager import BotManager
from config import config
from core.logger import logger
from gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Minecraft Bot Control")

    manager = BotManager(config)
    manager.create_bots(config.bot_count)

    window = MainWindow(manager)
    window.bot_panel.rebuild()
    window.show()

    logger.info("Iniciando conexion con el bridge en %s", config.bridge_url())
    manager.start_bridge()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
