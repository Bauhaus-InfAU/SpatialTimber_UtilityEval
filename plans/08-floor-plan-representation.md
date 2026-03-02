# Phase 8: Floor Plan Representation + Test Set + Scoring Spec

## Goal

Define the shared input format for all 3 reward functions (furnishability, daylight, circulation). Specify exactly what test data Luyang needs to provide. Create the single scoring specification document.

**Why here:** All three reward functions require the same apartment representation. Defining it once, right after Phase 7 (GH integration establishes the Python patterns), avoids duplication and gives Luyang time to prepare test data while Phases 9–10 proceed.

---

## Tasks

- [ ] 8.1 Create `src/evaluation/` package; define `ApartmentLayout`, `RoomLayout`, `WallSegment` frozen dataclasses in `src/evaluation/apartment.py`
- [ ] 8.2 Create `SCORING.md` at repo root — single source of truth for all score definitions, ranges, applicable rooms, aggregation rules, and composite formula
- [ ] 8.3 Write test set specification (`tests/fixtures/apartments/README.md`) — exact JSON format and labeled cases Luyang must provide
- [ ] 8.4 Create JSON schema for apartment format (`tests/fixtures/apartments/schema.json`)
- [ ] 8.5 Create 5 minimal hand-crafted pytest fixtures covering edge cases (no hallway, no exterior walls, fully connected) — unblocks Phases 11–12 before Luyang's data arrives
- [ ] 8.6 Update PLAN.md + Notion

---

## Apartment Representation Spec

New module: `src/evaluation/apartment.py`

```python
from dataclasses import dataclass
import numpy as np

ROOM_TYPES = ["Bedroom", "Living room", "Bathroom", "WC", "Kitchen",
              "Children 1", "Children 2", "Children 3", "Children 4", "Hallway"]

APT_TYPES = ["Studio (bedroom)", "Studio (living)", "1-Bedroom",
             "2-Bedroom", "3-Bedroom", "4-Bedroom", "5-Bedroom"]

HABITABLE_ROOM_TYPES = {"Bedroom", "Living room", "Kitchen",
                         "Children 1", "Children 2", "Children 3", "Children 4"}

@dataclass(frozen=True)
class WallSegment:
    start: tuple[float, float]
    end: tuple[float, float]
    is_exterior: bool          # True if this wall faces outside/facade

@dataclass(frozen=True)
class RoomLayout:
    room_type: str             # one of ROOM_TYPES
    polygon: np.ndarray        # (N, 2) closed CCW polyline, meters
    door: np.ndarray           # (2,) point on wall, meters

@dataclass(frozen=True)
class ApartmentLayout:
    apartment_type: str        # one of APT_TYPES
    entrance: np.ndarray       # (2,) point on outer wall
    outer_polygon: np.ndarray  # (N, 2) apartment boundary polygon
    walls: tuple[WallSegment, ...]  # all walls with is_exterior flag
    rooms: tuple[RoomLayout, ...]
```

**Frozen dataclasses** — consistent with existing `Room`/`Apartment` in `data.py`.

**`np.ndarray` in frozen dataclasses** — numpy arrays are not hashable; use `__hash__ = None` override or wrap in tuple. Document this in the module.

---

## Test Set Specification (what Luyang provides)

Luyang's database has cleaned floor plans. We need **~25 labeled apartments** covering:

**Daylight cases (10 apartments):**
| ID | Description | Expected daylight_score |
|----|-------------|------------------------|
| D01 | All habitable rooms on facade | 100 |
| D02 | No habitable rooms on facade | 0 |
| D03 | 1 of 3 habitable rooms on facade | 33 |
| D04 | Apartment with only WC+Bathroom (no habitable rooms) | 100 |
| D05 | Bedroom touches facade at corner only (NOT a full edge) | 0 |
| D06–D10 | Typical 1–5 bedroom apartments, natural facade distribution | varies |

**Circulation cases (10 apartments):**
| ID | Description | Expected circulation_score |
|----|-------------|---------------------------|
| C01 | All rooms connected via hallway | 100 |
| C02 | One bedroom isolated (no door to hallway) | <100 |
| C03 | No hallway room | 0 |
| C04 | Two hallway segments connected via door | 100 |
| C05 | Entrance opens into living room (no hallway) | depends on adjacency |
| C06–C10 | Typical 1–5 bedroom apartments, fully connected | 100 |

**Format for each apartment:**
```json
{
  "id": "D01",
  "apartment_type": "2-Bedroom",
  "entrance": [x, y],
  "outer_polygon": [[x1,y1], "..."],
  "walls": [
    {"start": [x,y], "end": [x,y], "is_exterior": true},
    "..."
  ],
  "rooms": [
    {
      "room_type": "Bedroom",
      "polygon": [[x1,y1], "..."],
      "door": [x, y]
    },
    "..."
  ],
  "expected_scores": {
    "daylight": 100,
    "circulation": 100,
    "furnitability": null
  }
}
```

Notes for Luyang:
- All coordinates in meters, CCW polygon winding
- `is_exterior: true` = wall faces outside (facade)
- `expected_scores.furnitability` = null (computed by model, not manually labeled)
- At least 25 apartments; ~10 edge-case labeled + ~15 typical

---

## Hand-Crafted Fixtures (5 minimal cases, unblocks dev)

| ID | Description | daylight | circulation |
|----|-------------|---------|-------------|
| H01 | 2-bed, 2 rooms on facade, all connected | 100 | 100 |
| H02 | 2-bed, no rooms on facade | 0 | 100 |
| H03 | No hallway room | 0 | 0 |
| H04 | One bedroom isolated from hallway | 100 | <100 |
| H05 | Only WC+Bathroom (no habitable rooms) | 100 | 100 |

---

## Deliverables

| Type | Artifact | Path |
|------|----------|------|
| Tool | Apartment representation dataclasses | `src/evaluation/apartment.py` |
| Config | Package init | `src/evaluation/__init__.py` |
| Config | Scoring specification | `SCORING.md` |
| Config | Apartment JSON schema | `tests/fixtures/apartments/schema.json` |
| Config | Test set specification for Luyang | `tests/fixtures/apartments/README.md` |
| Dataset | Hand-crafted test fixtures | `tests/fixtures/apartments/hand_crafted.json` |

---

## Decisions Log

- **Representation phase inserted before benchmark** (2026-03-01): All three reward functions (furnishability, daylight, circulation) share the same `ApartmentLayout` input format. Defining it once in Phase 8 avoids duplication across Phases 11–13 and gives Luyang time to prepare labeled test data while Phases 9–10 run in parallel.
- **Hand-crafted fixtures (Option B)** (2026-03-01): 5 minimal hand-crafted fixtures created in Phase 8 to unblock development of Phases 11–13. Luyang provides ~25 labeled apartments for comprehensive testing. Her data supplements rather than replaces the hand-crafted cases.

---

## Key Files

| File | Role |
|------|------|
| `src/furnisher_surrogate/data.py` | Existing frozen dataclass pattern to follow |
| `tests/fixtures/test_rooms.json` | Existing fixture format — reference for JSON conventions |
| `reports/03-01_eda-findings.ipynb` | Polygon format, room type definitions, CCW winding |
| `grasshopper/surrogate_score.py` | Phase 7 GH component — Python/GH integration pattern |
