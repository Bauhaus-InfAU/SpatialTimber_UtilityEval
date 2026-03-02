# Phase 8: Floor Plan Representation + Test Set + Scoring Spec

## Goal

Define the shared input format for all 3 reward functions (furnishability, daylight, circulation). Specify exactly what test data Luyang needs to provide. Create the single scoring specification document.

**Why here:** All three reward functions require the same apartment representation. Defining it once, right after Phase 7 (GH integration establishes the Python patterns), avoids duplication and gives Luyang time to prepare test data while Phases 9–10 proceed.

---

## Tasks

- [x] 8.1 Create `src/evaluation/` package; define `ApartmentLayout`, `RoomLayout`, `WallSegment` frozen dataclasses in `src/evaluation/apartment.py`
- [x] 8.2 Create `SCORING.md` at repo root — single source of truth for all score definitions, ranges, applicable rooms, aggregation rules, and composite formula
- [x] 8.3 Create JSON schema (`tests/fixtures/apartments/schema.json`) — derived from the dataclasses in 8.1; must be consistent with them
- [x] 8.4 Write test set specification (`tests/fixtures/apartments/README.md`) — references schema.json; labeling instructions and required cases for Luyang
- [x] 8.5 Create 5 minimal hand-crafted pytest fixtures covering edge cases (no hallway, no exterior walls, fully connected) — unblocks Phases 11–12 before Luyang's data arrives
- [x] 8.6 Update PLAN.md + Notion
- [x] 8.7 Create two GhPython utilities: apartment_reader.py (JSON→GH geometry for
  visual inspection) and apartment_writer.py (GH geometry→JSON for Luyang's export)
- [x] 8.8 Visual verification + H06 via writer
  - [x] a) Scripts are functional — verified by H02 reader→writer round-trip
    (2026-03-02): loaded H02 via apartment_reader.py, fed all outputs directly into
    apartment_writer.py, toggled write=True. Output JSON matches source exactly.
    Only cosmetic difference: Rhino coerces integer coordinates to floats
    (`[0,0]` → `[0.0, 0.0]`; `0` → `0.0`) — semantically identical, both valid JSON.
    Saved to `tests/fixtures/apartments/08_write test 1.json`.
  - [x] b) Drew H06 in Rhino, wired into apartment_writer.py, exported JSON and
    appended to hand_crafted.json. (2026-03-03)
- [x] 8.9 Create apartment JSON validator (`src/evaluation/validate.py`) + pytest self-test

---

## Apartment Representation Spec

New module: `src/evaluation/apartment.py` *(implemented)*

```python
ROOM_TYPES = ["Bedroom", "Living room", "Bathroom", "WC", "Kitchen",
              "Children 1", "Children 2", "Children 3", "Children 4", "Hallway"]

APT_TYPES = ["Studio (bedroom)", "Studio (living)", "1-Bedroom",
             "2-Bedroom", "3-Bedroom", "4-Bedroom", "5-Bedroom"]

# No HABITABLE_ROOM_TYPES constant — habitable/non-habitable distinction
# lives in src/evaluation/rules/daylight.json, not hardcoded in Python.

@dataclass(frozen=True)
class WallSegment:
    start: tuple[float, float]
    end: tuple[float, float]
    is_exterior: bool

@dataclass(frozen=True)
class RoomLayout:
    room_type: str
    polygon: np.ndarray   # (N, 2) closed CCW polyline, meters
    door: np.ndarray      # (2,) point on wall, meters
    __hash__ = None       # ndarray not hashable; raise TypeError on hash attempt

@dataclass(frozen=True)
class ApartmentLayout:
    id: str               # unique identifier (e.g. "H01", "D03")
    apartment_type: str
    entrance: np.ndarray  # (2,) point on outer wall
    outer_polygon: np.ndarray
    walls: tuple[WallSegment, ...]
    rooms: tuple[RoomLayout, ...]
    __hash__ = None       # ndarray not hashable
```

**Frozen dataclasses** — consistent with existing `Room`/`Apartment` in `data.py`.

**`np.ndarray` in frozen dataclasses** — `__hash__ = None` set explicitly; raises `TypeError` if you attempt to hash, rather than silently returning a wrong value.

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
| C01 | All rooms within BFS distance threshold from Hallway entry room | 100 |
| C02 | One bedroom isolated (no shared door, cannot be reached by BFS) | <100 |
| C03 | No hallway room; entrance in Living room; all other rooms within threshold | 100 |
| C04 | Bedroom at BFS distance 2 from entrance (max for Bedroom = 1) | <100 |
| C05 | Two Hallway segments; entry Hallway at dist=0 passes, second at dist=1 fails (max=0) | <100 |
| C06–C10 | Typical 1–5 bedroom apartments, fully connected within distance thresholds | 100 |

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
| H01 | 2-bed, 2 rooms on facade, Hallway at entrance; all rooms at BFS dist ≤ max | 100 | 100 |
| H02 | 2-bed, no rooms on facade, Hallway at entrance | 0 | 100 |
| H03 | Studio (no Hallway); entrance in Living room; Bedroom at dist=1 | 0 | 100 |
| H04 | Hallway + Living room + Bedroom in a chain; Bedroom at dist=2 (max=1) | 100 | 66.7 |
| H05 | Only WC + Bathroom (no habitable rooms) — vacuous daylight pass | 100 | 100 |

---

## Deliverables

| Type | Artifact | Path |
|------|----------|------|
| Tool | Apartment representation dataclasses + `load_rules()` | `src/evaluation/apartment.py` |
| Config | Package init | `src/evaluation/__init__.py` |
| Config | Circulation scoring rules | `src/evaluation/rules/circulation.json` |
| Config | Daylight scoring rules | `src/evaluation/rules/daylight.json` |
| Config | Furnishability scoring rules | `src/evaluation/rules/furnishability.json` |
| Config | Composite score weights | `src/evaluation/rules/composite.json` |
| Config | Scoring specification | `SCORING.md` |
| Config | Apartment JSON schema (derived from 8.1 dataclasses) | `tests/fixtures/apartments/schema.json` |
| Config | Test set specification for Luyang (references schema) | `tests/fixtures/apartments/README.md` |
| Dataset | Hand-crafted test fixtures | `tests/fixtures/apartments/hand_crafted.json` |
| Component | JSON → GH geometry reader | `grasshopper/apartment_reader.py` |
| Component | GH geometry → JSON writer | `grasshopper/apartment_writer.py` |
| Tool | Apartment JSON validator (schema + geometry) + CLI | `src/evaluation/validate.py` |
| Doc | Validator documentation (checks, tolerance, limitations) | `src/evaluation/VALIDATE.md` |
| Test | Pytest self-test for validator (pass + fail cases) | `tests/test_validate.py` |

---

## Decisions Log

- **Representation phase inserted before benchmark** (2026-03-01): All three reward functions (furnishability, daylight, circulation) share the same `ApartmentLayout` input format. Defining it once in Phase 8 avoids duplication across Phases 11–13 and gives Luyang time to prepare labeled test data while Phases 9–10 run in parallel.
- **Hand-crafted fixtures (Option B)** (2026-03-01): 5 minimal hand-crafted fixtures created in Phase 8 to unblock development of Phases 11–13. Luyang provides ~25 labeled apartments for comprehensive testing. Her data supplements rather than replaces the hand-crafted cases.
- **Schema before README** (2026-03-02): Task order corrected — JSON schema (8.3) must be written before the README spec for Luyang (8.4), since the README references the schema and Luyang needs the schema to know what to export. Both are derived from the dataclasses in 8.1.
- **Scoring rules in JSON, not Python** (2026-03-02): Implemented design change from original plan — no `HABITABLE_ROOM_TYPES` set or `CIRCULATION_MAX_DISTANCE` dict hardcoded in Python. All rule parameters live in `src/evaluation/rules/*.json` (4 files: circulation, daylight, furnishability, composite). Loaded lazily via `load_rules(domain)`. This allows per-experiment rule swaps without code changes.
- **Polygon winding order requirement dropped** (2026-03-02): The original spec required CCW winding. Requirement removed because none of the planned algorithms (daylight edge-overlap, circulation point-on-boundary, surrogate rasterizer) need it — they treat edges as undirected line segments. Any algorithm that does need inside/outside information must use an orientation-agnostic method (e.g. ray casting) and must not assume consistent winding across fixtures or user-supplied data.
- **Apartment-level doors list replaces per-room door field** (2026-03-02): `room.door` removed; replaced by `apartment.doors: [[x,y], ...]` — a flat list of all interior door openings. Motivation: (1) a Hallway has multiple doors and a single point made no sense; (2) rooms with two doors (e.g. Living room connecting to both Hallway and Kitchen) could not be encoded; (3) door positions for BFS adjacency and for the surrogate are different concerns — BFS adjacency is now derived from which rooms share a door point on their polygon boundary; the surrogate picks the door point that lies on a given room's boundary. `RoomLayout.door` field removed; `ApartmentLayout.doors` tuple added. Schema, fixtures, GH reader/writer, circulation.json all updated.
- **H03 expected scores revised** (2026-03-02): Original plan had H03 as "no hallway → circulation=0". Revised to Studio with entrance in Living room → BFS starts from Living room → Bedroom at dist=1 passes → circulation=100. The distance-based model handles the no-hallway case correctly via the entrance-room fallback.

---

## Key Files

| File | Role |
|------|------|
| `src/furnisher_surrogate/data.py` | Existing frozen dataclass pattern followed |
| `src/evaluation/rules/*.json` | All scoring rule parameters — no hardcoded dicts in Python |
| `src/evaluation/validate.py` | Apartment JSON validator (schema + geometry checks) |
| `src/evaluation/VALIDATE.md` | Validator documentation — checks, tolerance rationale, known limitations |
| `tests/fixtures/test_rooms.json` | Existing fixture format — reference for JSON conventions |
| `reports/03-01_eda-findings.ipynb` | Polygon format, room type definitions, CCW winding |
| `grasshopper/surrogate_score.py` | Phase 7 GH component — Python/GH integration pattern |
