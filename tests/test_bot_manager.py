import pytest

from bots.bot_state import BotState
from core.exceptions import BotNotFoundError, InvalidCommandError


def test_create_bots_respects_max_30(manager):
    manager.create_bots(50)  # se pide mas de 30, debe recortarse
    assert len(manager.all_bots()) == 30


def test_create_bots_names_use_prefix(manager):
    manager.create_bots(3, prefix="Bot_")
    names = sorted(b.name for b in manager.all_bots())
    assert names == ["Bot_01", "Bot_02", "Bot_03"]


def test_get_bot_returns_correct_bot(manager):
    manager.create_bots(5)
    bot = manager.get_bot(3)
    assert bot.id == 3
    assert bot.name == "Bot_03"


def test_get_bot_missing_raises(manager):
    manager.create_bots(2)
    with pytest.raises(BotNotFoundError):
        manager.get_bot(99)


def test_initial_state_is_disconnected(manager):
    manager.create_bots(4)
    for bot in manager.all_bots():
        assert bot.state == BotState.DISCONNECTED


def test_connect_all_sends_one_connect_per_bot_without_delay(manager):
    manager.create_bots(30)
    manager.connect_all()

    connect_messages = [m for m in manager.bridge.sent if m["type"] == "connect"]
    assert len(connect_messages) == 30
    sent_ids = sorted(m["botId"] for m in connect_messages)
    assert sent_ids == list(range(1, 31))

    for bot in manager.all_bots():
        assert bot.state == BotState.CONNECTING


def test_connect_bot_uses_configured_host_and_port(manager, test_config):
    manager.create_bots(1)
    manager.connect_bot(1)
    msg = manager.bridge.sent[-1]
    assert msg["host"] == test_config.minecraft_host
    assert msg["port"] == test_config.minecraft_port


def test_disconnect_bot_sends_disconnect_and_updates_state(manager):
    manager.create_bots(1)
    manager.connect_bot(1)
    manager.disconnect_bot(1)
    assert manager.get_bot(1).state == BotState.DISCONNECTED
    types = [m["type"] for m in manager.bridge.sent]
    assert "disconnect" in types


def test_broadcast_chat_reaches_every_bot(manager):
    manager.create_bots(5)
    manager.broadcast_chat("Hola a todos")
    chat_messages = [m for m in manager.bridge.sent if m["type"] == "chat"]
    assert len(chat_messages) == 5
    assert all(m["message"] == "Hola a todos" for m in chat_messages)


def test_broadcast_command_reaches_every_bot(manager):
    manager.create_bots(4)
    manager.broadcast_command("/spawn")
    command_messages = [m for m in manager.bridge.sent if m["type"] == "command"]
    assert len(command_messages) == 4
    assert all(m["command"] == "/spawn" for m in command_messages)


def test_send_chat_targets_single_bot(manager):
    manager.create_bots(3)
    manager.send_chat(2, "solo para bot 2")
    chat_messages = [m for m in manager.bridge.sent if m["type"] == "chat"]
    assert len(chat_messages) == 1
    assert chat_messages[0]["botId"] == 2


def test_dispatch_input_distinguishes_chat_and_command(manager):
    manager.create_bots(2)

    manager.dispatch_input("Hola", target="ALL")
    manager.dispatch_input("/tp 100 64 -200", target="ALL")

    chat_msgs = [m for m in manager.bridge.sent if m["type"] == "chat"]
    cmd_msgs = [m for m in manager.bridge.sent if m["type"] == "command"]
    assert any(m["message"] == "Hola" for m in chat_msgs)
    assert any(m["command"] == "/tp 100 64 -200" for m in cmd_msgs)


def test_dispatch_input_bots_shortcut_forces_all(manager):
    manager.create_bots(6)
    parsed = manager.dispatch_input("!bots /say Hola", target=3)
    assert parsed.force_all is True
    cmd_msgs = [m for m in manager.bridge.sent if m["type"] == "command"]
    assert len(cmd_msgs) == 6


def test_dispatch_input_empty_raises(manager):
    manager.create_bots(1)
    with pytest.raises(InvalidCommandError):
        manager.dispatch_input("   ", target="ALL")


def test_selection_of_bots_via_group(manager):
    manager.create_bots(10)
    group = manager.make_group([2, 4, 6], name="grupo_prueba")
    assert len(group) == 3
    group.broadcast_chat("hola grupo")
    chat_msgs = [m for m in manager.bridge.sent if m["type"] == "chat"]
    assert {m["botId"] for m in chat_msgs} == {2, 4, 6}


def test_bridge_status_message_updates_bot_state(manager):
    manager.create_bots(1)
    manager._on_bridge_message({"type": "status", "botId": 1, "state": "CONNECTED"})
    assert manager.get_bot(1).state == BotState.CONNECTED


def test_bridge_error_message_sets_error_state(manager):
    manager.create_bots(1)
    manager._on_bridge_message({"type": "error", "botId": 1, "message": "boom"})
    bot = manager.get_bot(1)
    assert bot.state == BotState.ERROR
    assert bot.last_error == "boom"


def test_bridge_position_message_updates_coordinates(manager):
    manager.create_bots(1)
    manager._on_bridge_message(
        {"type": "position", "botId": 1, "x": 10.5, "y": 64.0, "z": -3.2, "yaw": 1.0, "pitch": 0.0}
    )
    bot = manager.get_bot(1)
    assert bot.position == (10.5, 64.0, -3.2)
