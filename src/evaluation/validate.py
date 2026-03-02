"""Apartment JSON validator — structure and geometry checks.

Validates an apartment JSON file (single object or array) against:

1. JSON schema  (`tests/fixtures/apartments/schema.json`) — type errors,
   missing required fields, enum violations.
2. ``outer_is_exterior`` length consistency with ``outer_polygon`` edge count.
3. Polygon closure — outer polygon and every room polygon must have
   ``|first − last| < tol``.
4. Entrance on outer polygon boundary — point-to-polyline distance < tol.
5. Each door on ≥ 2 room polygon boundaries — counts rooms whose boundary
   is within *tol* of the door; must be ≥ 2.
6. Minimum room area — each room polygon must have area ≥ 0.5 m².

All geometric checks use a configurable tolerance (default 0.3 m) to
accommodate wall-thickness offsets and floating-point drift from exported
Rhino/GH models.

Public API
----------
``validate_apartment(data, tol=0.3, schema_path=None) -> list[str]``
    Returns a list of error strings.  Empty list means the apartment is valid.

CLI
---
``python -m src.evaluation.validate path/to/file.json [--tol 0.5]``

Accepts JSON files containing either a single apartment object or an array
of apartment objects.  Prints PASS/FAIL per apartment; exits with code 0
only if all apartments pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

# ── Optional jsonschema import ────────────────────────────────────────────────
# jsonschema is not listed as an explicit project dependency but is normally
# available transitively via jupyter.  We degrade gracefully if absent so that
# the geometric checks still work without it.
try:
    import jsonschema as _jsonschema
except ImportError:  # pragma: no cover
    _jsonschema = None  # type: ignore[assignment]

# Default schema path: tests/fixtures/apartments/schema.json (repo root).
_DEFAULT_SCHEMA: Path = (
    Path(__file__).parent.parent.parent
    / "tests"
    / "fixtures"
    / "apartments"
    / "schema.json"
)

# Minimum room area in m² — below this the room is considered degenerate.
_MIN_ROOM_AREA_M2: float = 0.5


# ── Geometry helpers ──────────────────────────────────────────────────────────


def _seg_dist(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """Minimum distance from point *p* to segment *a→b*.

    Parameters
    ----------
    p, a, b:
        Shape ``(2,)`` float arrays.

    Returns
    -------
    float
        Euclidean distance from *p* to the nearest point on segment *a→b*.
    """
    ab = b - a
    len_sq = float(np.dot(ab, ab))
    if len_sq == 0.0:
        # Degenerate segment: a == b.
        return float(np.linalg.norm(p - a))
    t = float(np.dot(p - a, ab)) / len_sq
    t = max(0.0, min(1.0, t))
    proj = a + t * ab
    return float(np.linalg.norm(p - proj))


def _poly_dist(p: np.ndarray, poly: np.ndarray) -> float:
    """Minimum distance from point *p* to any edge of closed polyline *poly*.

    Parameters
    ----------
    p:
        Shape ``(2,)`` float array.
    poly:
        Shape ``(N, 2)`` float array.  Must be a closed polyline
        (``poly[0] ≈ poly[-1]``).

    Returns
    -------
    float
        Minimum over all N-1 edges of the segment-to-point distance.
    """
    return min(
        _seg_dist(p, poly[i], poly[i + 1]) for i in range(len(poly) - 1)
    )


def _poly_area(poly: np.ndarray) -> float:
    """Polygon area via the shoelace formula.

    Parameters
    ----------
    poly:
        Shape ``(N, 2)`` float array (closed polyline).

    Returns
    -------
    float
        Area in m² (always non-negative).
    """
    x = poly[:, 0]
    y = poly[:, 1]
    return 0.5 * abs(float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])))


# ── Validator ─────────────────────────────────────────────────────────────────


def validate_apartment(
    data: dict[str, Any],
    tol: float = 0.3,
    schema_path: Path | None = None,
) -> list[str]:
    """Validate one apartment dict (parsed JSON).

    Runs all structural and geometric checks and collects every error — it
    does **not** stop at the first failure (except after a schema error, which
    would leave required fields absent and cause later checks to crash).

    Parameters
    ----------
    data:
        Apartment dict as returned by ``json.loads`` / ``json.load``.
    tol:
        Geometric proximity tolerance in metres (default 0.3 m).
        Covers wall-thickness offsets and exported floating-point drift.

        * A door or entrance is considered *on* an edge if its distance to
          the nearest point on that edge is less than *tol*.
        * A polygon is considered *closed* if ``|first − last| < tol``.
    schema_path:
        Path to the JSON schema file.  Defaults to
        ``tests/fixtures/apartments/schema.json`` (resolved from this
        module's location).  Pass ``None`` to use the default.

    Returns
    -------
    list[str]
        Error strings.  An empty list means the apartment is fully valid.
    """
    errors: list[str] = []

    # ── 1. JSON schema validation ─────────────────────────────────────────
    resolved_schema = schema_path if schema_path is not None else _DEFAULT_SCHEMA

    if _jsonschema is None:  # pragma: no cover
        # jsonschema is an optional dependency; skip silently.  The geometric
        # checks below still run and catch most common errors.
        pass
    elif not resolved_schema.exists():  # pragma: no cover
        # Schema file missing — cannot validate structure; continue with geometry.
        pass
    else:
        schema = json.loads(resolved_schema.read_text(encoding="utf-8"))
        try:
            _jsonschema.validate(instance=data, schema=schema)
        except _jsonschema.ValidationError as exc:
            errors.append(f"schema: {exc.message}")
            # Return early — subsequent checks rely on required fields being
            # present and having the correct types.
            return errors

    # ── Extract fields (schema passed, so these exist with correct types) ─
    outer_polygon = np.array(data["outer_polygon"], dtype=float)
    outer_is_exterior: list[bool] = data["outer_is_exterior"]
    entrance = np.array(data["entrance"], dtype=float)
    doors_raw: list[list[float]] = data["doors"]
    rooms_raw: list[dict] = data["rooms"]

    # ── 2. outer_is_exterior length consistency ───────────────────────────
    n_edges = len(outer_polygon) - 1
    if len(outer_is_exterior) != n_edges:
        errors.append(
            f"outer_is_exterior has {len(outer_is_exterior)} items but "
            f"outer_polygon has {n_edges} edges ({n_edges} = len(outer_polygon) - 1)"
        )

    # ── 3. Outer polygon closure ──────────────────────────────────────────
    gap = float(np.linalg.norm(outer_polygon[0] - outer_polygon[-1]))
    if gap >= tol:
        errors.append(
            f"outer_polygon not closed: gap {gap:.3f} m (tol {tol} m)"
        )

    # ── 4. Room polygon closure  7. Degenerate room area ─────────────────
    room_polys: list[np.ndarray] = []
    for i, room in enumerate(rooms_raw):
        rtype = room.get("room_type", f"room[{i}]")
        poly = np.array(room["polygon"], dtype=float)
        room_polys.append(poly)

        # Closure
        gap = float(np.linalg.norm(poly[0] - poly[-1]))
        if gap >= tol:
            errors.append(
                f"room[{i}] ({rtype}) polygon not closed: gap {gap:.3f} m (tol {tol} m)"
            )

        # Minimum area
        area = _poly_area(poly)
        if area < _MIN_ROOM_AREA_M2:
            errors.append(
                f"room[{i}] ({rtype}) area {area:.3f} m² is below minimum "
                f"{_MIN_ROOM_AREA_M2} m²"
            )

    # ── 5. Entrance on outer polygon boundary ─────────────────────────────
    entrance_dist = _poly_dist(entrance, outer_polygon)
    if entrance_dist >= tol:
        errors.append(
            f"entrance [{entrance[0]}, {entrance[1]}] not on outer polygon "
            f"(nearest edge {entrance_dist:.3f} m away, tol {tol} m)"
        )

    # ── 6. Each door on ≥ 2 room polygon boundaries ───────────────────────
    for j, door_raw in enumerate(doors_raw):
        door = np.array(door_raw, dtype=float)
        n_touching = sum(
            1 for rp in room_polys if _poly_dist(door, rp) < tol
        )
        if n_touching < 2:
            errors.append(
                f"door[{j}] [{door[0]}, {door[1]}] touches only "
                f"{n_touching} room boundary/ies (need ≥ 2, tol {tol} m)"
            )

    return errors


# ── CLI ───────────────────────────────────────────────────────────────────────


def _main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate apartment JSON files — checks schema structure and geometry. "
            "Accepts a JSON file containing either one apartment object or an array "
            "of apartment objects."
        )
    )
    parser.add_argument("file", type=Path, help="Path to the JSON file to validate.")
    parser.add_argument(
        "--tol",
        type=float,
        default=0.3,
        metavar="M",
        help="Geometric proximity tolerance in metres (default: 0.3).",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Path to the JSON schema file "
            "(default: tests/fixtures/apartments/schema.json)."
        ),
    )
    args = parser.parse_args()

    raw = json.loads(args.file.read_text(encoding="utf-8"))
    apartments: list[dict] = raw if isinstance(raw, list) else [raw]

    all_pass = True
    for apt in apartments:
        apt_id = apt.get("id", "<no id>")
        errs = validate_apartment(apt, tol=args.tol, schema_path=args.schema)
        if errs:
            all_pass = False
            print(f"FAIL  {apt_id}")
            for e in errs:
                print(f"      - {e}")
        else:
            print(f"PASS  {apt_id}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    _main()
