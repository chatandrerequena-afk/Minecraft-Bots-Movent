from config import Config


def test_default_formation_is_6x5():
    cfg = Config()
    assert cfg.formation_columns == 6
    assert cfg.formation_rows == 5
    assert cfg.formation_columns * cfg.formation_rows == 30


def test_max_bots_is_30():
    cfg = Config()
    assert cfg.max_bots == 30


def test_bridge_url_format():
    cfg = Config(bridge_host="127.0.0.1", bridge_port=8765)
    assert cfg.bridge_url() == "ws://127.0.0.1:8765"


def test_config_is_frozen():
    cfg = Config()
    try:
        cfg.bot_count = 5  # type: ignore[misc]
        assert False, "Config deberia ser inmutable (frozen dataclass)"
    except Exception:
        pass
