"""Pytest self-test for src/evaluation/validate.py.

Two groups of tests
-------------------
Pass tests:  every hand-crafted fixture (H01–H05) must return [] from
             validate_apartment().

Fail tests:  each test mutates one field of an in-memory copy of a fixture
             and asserts that validate_apartment() returns at least one error
             whose text matches the expected substring(s).

Geometric tolerance
-------------------
All fail tests use the default tol=0.3 m.  Mutations that place a point
far from a polygon boundary (e.g. [99, 99]) or open a gap ≥ 1 m are safely
outside this tolerance.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.evaluation.validate import validate_apartment

# ── Fixture loading ───────────────────────────────────────────────────────────

_FIXTURE_PATH = Path("tests/fixtures/apartments/hand_crafted.json")
_APARTMENTS: list[dict] = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _get(apt_id: str) -> dict:
    """Return a deep copy of the fixture with the given id."""
    match = next((a for a in _APARTMENTS if a["id"] == apt_id), None)
    if match is None:
        raise KeyError(f"No fixture with id '{apt_id}'")
    return copy.deepcopy(match)


# ── Pass tests ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("apt", _APARTMENTS, ids=lambda a: a["id"])
def test_hand_crafted_passes(apt: dict) -> None:
    """All hand-crafted fixtures must validate without errors."""
    assert validate_apartment(apt) == []


# ── Fail tests ────────────────────────────────────────────────────────────────


def test_outer_is_exterior_wrong_length() -> None:
    """Removing one flag from outer_is_exterior must trigger a length error."""
    apt = _get("H01")
    apt["outer_is_exterior"].pop()
    errs = validate_apartment(apt)
    assert any("outer_is_exterior has" in e for e in errs), errs


def test_outer_polygon_not_closed() -> None:
    """Shifting the last outer_polygon vertex by 1 m must trigger a closure error."""
    apt = _get("H01")
    # Shift the closing point 1 m in X — well above the default 0.3 m tolerance.
    apt["outer_polygon"][-1][0] += 1.0
    errs = validate_apartment(apt)
    assert any("outer_polygon not closed" in e for e in errs), errs


def test_room_polygon_not_closed() -> None:
    """Shifting the last room polygon vertex by 1 m must trigger a closure error."""
    apt = _get("H01")
    apt["rooms"][0]["polygon"][-1][0] += 1.0
    errs = validate_apartment(apt)
    assert any("polygon not closed" in e for e in errs), errs


def test_entrance_off_boundary() -> None:
    """Placing the entrance far from the outer polygon must trigger a boundary error."""
    apt = _get("H01")
    apt["entrance"] = [99.0, 99.0]
    errs = validate_apartment(apt)
    assert any("entrance" in e and "not on outer polygon" in e for e in errs), errs


def test_door_only_one_room() -> None:
    """Moving a door far from all room boundaries must trigger a room-count error."""
    apt = _get("H01")
    apt["doors"][0] = [99.0, 99.0]
    errs = validate_apartment(apt)
    assert any("touches only" in e for e in errs), errs


def test_degenerate_room() -> None:
    """Shrinking a room to 0.01 × 0.01 m must trigger an area error."""
    apt = _get("H01")
    # Replace Hallway polygon with a 1 cm × 1 cm square (area = 0.0001 m² < 0.5 m²).
    apt["rooms"][0]["polygon"] = [
        [0.0, 0.0],
        [0.01, 0.0],
        [0.01, 0.01],
        [0.0, 0.01],
        [0.0, 0.0],
    ]
    errs = validate_apartment(apt)
    assert any("area" in e and "below minimum" in e for e in errs), errs


def test_schema_violation() -> None:
    """Removing a required field must trigger a schema validation error."""
    jsonschema = pytest.importorskip(
        "jsonschema", reason="jsonschema not installed — schema check cannot run"
    )
    apt = _get("H01")
    del apt["apartment_type"]
    errs = validate_apartment(apt)
    assert len(errs) > 0, "Expected at least one schema error, got none"
    assert any("schema:" in e for e in errs), errs
