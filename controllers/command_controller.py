"""CommandController: interpreta el texto escrito en el panel de
chat/comandos y decide si es un mensaje de chat o un comando de
servidor, y a quien va dirigido.

Reglas:
  - Si el texto empieza por "/"                -> es un COMANDO de servidor.
  - En caso contrario                          -> es un mensaje de CHAT.
  - Si el texto empieza por "!bots "            -> es un atajo que SIEMPRE
    se envia a TODOS los bots, sin importar el selector "Enviar a".
    Ejemplos: "!bots Hola" -> chat "Hola" a todos.
              "!bots /spawn" -> comando "/spawn" a todos.

Este modulo no ejecuta nada por si mismo contra Minecraft: solo decide
qué se envía y a quién, y delega el envío real en BotManager /
BotGroup / MinecraftBot. No intenta evadir permisos del servidor: si un
bot no tiene permisos para un comando, el servidor lo rechazara y el
bridge reportara el resultado tal cual (ver bridge/bridge.js).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Union

from core.exceptions import InvalidCommandError

if TYPE_CHECKING:
    from bots.bot_manager import BotManager

BOTS_SHORTCUT_PREFIX = "!bots "

TargetSpec = Union[str, int]  # "ALL" | "GROUP" | bot_id


@dataclass
class ParsedInput:
    kind: str          # "chat" | "command"
    payload: str        # mensaje o comando (sin el prefijo "!bots ")
    force_all: bool      # True si venia con el atajo "!bots "


class CommandController:
    def parse(self, raw_text: str) -> ParsedInput:
        text = raw_text.strip()
        if not text:
            raise InvalidCommandError("El mensaje/comando esta vacio")

        force_all = False
        if text.startswith(BOTS_SHORTCUT_PREFIX):
            text = text[len(BOTS_SHORTCUT_PREFIX):].strip()
            force_all = True
            if not text:
                raise InvalidCommandError("El mensaje/comando esta vacio tras '!bots '")

        kind = "command" if text.startswith("/") else "chat"
        return ParsedInput(kind=kind, payload=text, force_all=force_all)

    def dispatch(
        self,
        manager: "BotManager",
        raw_text: str,
        target: TargetSpec = "ALL",
        group_ids: Optional[list] = None,
    ) -> ParsedInput:
        """Envia el texto ya interpretado al destino indicado.

        target puede ser:
          - "ALL"   -> todos los bots
          - "GROUP" -> bots en group_ids
          - int     -> un unico bot_id
        """
        parsed = self.parse(raw_text)
        effective_target: TargetSpec = "ALL" if parsed.force_all else target

        if effective_target == "ALL":
            bot_ids = list(manager.bots.keys())
        elif effective_target == "GROUP":
            bot_ids = list(group_ids or [])
        elif isinstance(effective_target, int):
            bot_ids = [effective_target]
        else:
            raise InvalidCommandError(f"Destino invalido: {effective_target}")

        for bot_id in bot_ids:
            if not manager.has_bot(bot_id):
                continue
            bot = manager.get_bot(bot_id)
            if parsed.kind == "chat":
                bot.send_chat(parsed.payload)
            else:
                bot.send_command(parsed.payload)

        return parsed
