"""Excepciones propias del proyecto minecraft_bot."""


class MinecraftBotError(Exception):
    """Excepcion base para todos los errores del proyecto."""


class BridgeConnectionError(MinecraftBotError):
    """Error al conectar o comunicarse con el bridge Node.js."""


class BotNotFoundError(MinecraftBotError):
    """Se solicito un bot que no existe en el BotManager."""

    def __init__(self, bot_id: int):
        super().__init__(f"No existe ningun bot con id={bot_id}")
        self.bot_id = bot_id


class InvalidCommandError(MinecraftBotError):
    """El texto introducido por el usuario no es un comando/mensaje valido."""


class FormationError(MinecraftBotError):
    """Error al calcular o aplicar una formacion."""
