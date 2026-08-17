import math

import pytest

from controllers.formation_controller import Formation, FormationController
from core.exceptions import FormationError


def test_formation_6x5_has_30_slots():
    formation = Formation(columns=6, rows=5, spacing=1.5)
    slots = formation.local_slots()
    assert len(slots) == 30
    assert formation.capacity == 30


def test_formation_slots_are_evenly_spaced():
    formation = Formation(columns=6, rows=5, spacing=1.5)
    slots = formation.local_slots()
    xs = sorted({round(dx, 3) for dx, _ in slots})
    assert len(xs) == 6
    diffs = [round(b - a, 3) for a, b in zip(xs, xs[1:])]
    assert all(abs(d - 1.5) < 1e-6 for d in diffs)


def test_formation_is_generic_not_hardcoded_to_30():
    for columns, rows in [(5, 6), (3, 10), (10, 3), (1, 1), (30, 1)]:
        formation = Formation(columns=columns, rows=rows, spacing=2.0)
        assert len(formation.local_slots()) == columns * rows


def test_world_slots_offset_from_anchor():
    formation = Formation(columns=2, rows=1, spacing=2.0)
    world = formation.world_slots(anchor_x=100.0, anchor_z=200.0)
    assert len(world) == 2
    # el centro de los dos huecos debe coincidir con el ancla
    avg_x = sum(x for x, _ in world) / 2
    avg_z = sum(z for _, z in world) / 2
    assert math.isclose(avg_x, 100.0, abs_tol=1e-6)
    assert math.isclose(avg_z, 200.0, abs_tol=1e-6)


def test_invalid_formation_raises():
    with pytest.raises(FormationError):
        Formation(columns=0, rows=5)
    with pytest.raises(FormationError):
        Formation(columns=5, rows=5, spacing=0)


def test_compute_positions_matches_capacity():
    positions = FormationController.compute_positions(columns=6, rows=5, spacing=1.5)
    assert len(positions) == 30
    for x, y, z in positions:
        assert isinstance(x, float) and isinstance(y, float) and isinstance(z, float)


def test_formation_controller_form_moves_all_bots(manager):
    manager.create_bots(30)
    bots = manager.all_bots()
    manager.formation.form(bots, columns=6, rows=5, spacing=1.5, anchor=(0.0, 64.0, 0.0))

    move_messages = [m for m in manager.bridge.sent if m["type"] == "move_to"]
    assert len(move_messages) == 30
    target_ids = {m["botId"] for m in move_messages}
    assert target_ids == {b.id for b in bots}
