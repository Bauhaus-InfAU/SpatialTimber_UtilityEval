"""Generate synthetic benchmark rooms for Phase 9 speed/accuracy evaluation.

Produces ~180 rooms: 9 room types × 5 area quintiles × 2 shapes × 2 rooms.
Shapes: rectangles (4 vertices) and L-shapes (6 vertices).
Output: tests/phase9_benchmark.json
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from furnisher_surrogate.data import (
    APT_TYPES,
    ROOM_TYPES,
    ROOM_TYPE_TO_IDX,
    load_apartments,
)
from furnisher_surrogate.features import area as compute_area, Room

# ── Configuration ────────────────────────────────────────────

SEED = 42
N_QUINTILES = 5
SHAPES = ["rect", "lshape"]
ROOMS_PER_CELL = 2  # rooms per (type, quintile, shape) combination
ASPECT_RATIO_RANGE = (1.0, 2.5)
NOTCH_FRAC_RANGE = (0.2, 0.4)  # notch size as fraction of bounding box

OUTPUT_PATH = PROJECT_ROOT / "tests" / "phase9_benchmark.json"


def _slug(room_type: str) -> str:
    """Convert room type to filename-safe slug."""
    return room_type.lower().replace(" ", "_")


def _compute_area_quintiles(
    apartments: list,
) -> dict[str, np.ndarray]:
    """Compute area quintile boundaries per room type from training data."""
    areas_by_type: dict[str, list[float]] = {rt: [] for rt in ROOM_TYPES}
    for apt in apartments:
        for room in apt.rooms:
            a = compute_area(room)
            areas_by_type[room.room_type].append(a)

    quintiles: dict[str, np.ndarray] = {}
    for rt in ROOM_TYPES:
        arr = np.array(areas_by_type[rt])
        # Quintile edges: 0%, 20%, 40%, 60%, 80%, 100%
        quintiles[rt] = np.percentile(arr, [0, 20, 40, 60, 80, 100])
    return quintiles


def _make_rectangle(target_area: float, aspect_ratio: float) -> np.ndarray:
    """Create a closed CCW rectangle at origin with given area and aspect ratio.

    aspect_ratio = width / height, always >= 1.0
    Returns (5, 2) closed polygon.
    """
    # width * height = target_area, width / height = aspect_ratio
    h = np.sqrt(target_area / aspect_ratio)
    w = aspect_ratio * h
    return np.array([
        [0.0, 0.0],
        [w, 0.0],
        [w, h],
        [0.0, h],
        [0.0, 0.0],
    ])


def _make_lshape(
    target_area: float,
    aspect_ratio: float,
    rng: random.Random,
) -> np.ndarray:
    """Create a closed CCW L-shape at origin with ~target_area.

    Removes a rectangular notch from one corner of the bounding rectangle.
    Returns (7, 2) closed polygon.
    """
    # Notch fractions
    nw_frac = rng.uniform(*NOTCH_FRAC_RANGE)
    nh_frac = rng.uniform(*NOTCH_FRAC_RANGE)

    # Bounding box area = target_area + notch_area
    # actual_area = w*h - nw*nh = w*h - (nw_frac*w)*(nh_frac*h) = w*h*(1 - nw_frac*nh_frac)
    # So w*h = target_area / (1 - nw_frac*nh_frac)
    bbox_area = target_area / (1.0 - nw_frac * nh_frac)

    h = np.sqrt(bbox_area / aspect_ratio)
    w = aspect_ratio * h
    nw = nw_frac * w
    nh = nh_frac * h

    # Pick a random corner for the notch
    corner = rng.choice(["BL", "BR", "TL", "TR"])

    if corner == "TR":
        # Notch at top-right: remove (w-nw, h-nh) to (w, h)
        pts = [
            [0.0, 0.0],
            [w, 0.0],
            [w, h - nh],
            [w - nw, h - nh],
            [w - nw, h],
            [0.0, h],
        ]
    elif corner == "TL":
        # Notch at top-left: remove (0, h-nh) to (nw, h)
        pts = [
            [0.0, 0.0],
            [w, 0.0],
            [w, h],
            [nw, h],
            [nw, h - nh],
            [0.0, h - nh],
        ]
    elif corner == "BR":
        # Notch at bottom-right: remove (w-nw, 0) to (w, nh)
        pts = [
            [0.0, 0.0],
            [w - nw, 0.0],
            [w - nw, nh],
            [w, nh],
            [w, h],
            [0.0, h],
        ]
    else:  # BL
        # Notch at bottom-left: remove (0, 0) to (nw, nh)
        pts = [
            [nw, 0.0],
            [w, 0.0],
            [w, h],
            [0.0, h],
            [0.0, nh],
            [nw, nh],
        ]

    # Close the polygon
    pts.append(pts[0])
    return np.array(pts)


def _pick_door(polygon: np.ndarray, rng: random.Random) -> np.ndarray:
    """Place door at midpoint of a randomly chosen wall segment."""
    n_edges = len(polygon) - 1
    edge_idx = rng.randint(0, n_edges - 1)
    p1 = polygon[edge_idx]
    p2 = polygon[edge_idx + 1]
    return (p1 + p2) / 2.0


def _verify_ccw(polygon: np.ndarray) -> bool:
    """Check polygon has counter-clockwise winding (positive signed area)."""
    x = polygon[:, 0]
    y = polygon[:, 1]
    signed_area = 0.5 * float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))
    return signed_area > 0


def generate_benchmark_set() -> list[dict]:
    """Generate the full synthetic benchmark set."""
    print("Loading training data for area quintile computation...")
    apartments = load_apartments()
    quintiles = _compute_area_quintiles(apartments)

    rng = random.Random(SEED)
    np.random.seed(SEED)

    rooms: list[dict] = []

    for rt in ROOM_TYPES:
        edges = quintiles[rt]
        slug = _slug(rt)

        for q in range(N_QUINTILES):
            # Target area: midpoint of quintile range
            lo, hi = edges[q], edges[q + 1]
            target_area = (lo + hi) / 2.0

            # Skip degenerate quintiles (near-zero area)
            if target_area < 0.5:
                print(f"  Skipping {rt} Q{q+1}: target area {target_area:.2f} m² too small")
                continue

            for shape in SHAPES:
                for idx in range(ROOMS_PER_CELL):
                    ar = rng.uniform(*ASPECT_RATIO_RANGE)
                    apt_type = rng.choice(APT_TYPES)

                    if shape == "rect":
                        polygon = _make_rectangle(target_area, ar)
                    else:
                        polygon = _make_lshape(target_area, ar, rng)

                    # Verify CCW winding
                    assert _verify_ccw(polygon), f"Polygon not CCW: {slug}_q{q+1}_{shape}_{idx}"

                    door = _pick_door(polygon, rng)

                    name = f"{slug}_q{q+1}_{shape}_{idx}"
                    rooms.append({
                        "name": name,
                        "polygon": np.round(polygon, 4).tolist(),
                        "door": np.round(door, 4).tolist(),
                        "room_type": rt,
                        "apartment_type": apt_type,
                        "shape": shape,
                    })

    print(f"Generated {len(rooms)} synthetic rooms")
    return rooms


def main() -> None:
    rooms = generate_benchmark_set()

    # Summary
    by_type = {}
    for r in rooms:
        by_type.setdefault(r["room_type"], 0)
        by_type[r["room_type"]] += 1
    print("\nRooms per type:")
    for rt in ROOM_TYPES:
        print(f"  {rt}: {by_type.get(rt, 0)}")

    by_shape = {}
    for r in rooms:
        by_shape.setdefault(r["shape"], 0)
        by_shape[r["shape"]] += 1
    print(f"\nBy shape: {by_shape}")

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(rooms, f, indent=2)
    print(f"\nSaved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
