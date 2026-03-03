# Apartment JSON Validator

`src/evaluation/validate.py` validates apartment JSON files before they are
used by the three reward functions (furnishability, daylight, circulation).  It checks both structural correctness (via JSON schema) and
geometric plausibility (polygon closure, boundary proximity, area).

---

## Usage

### Command line

```bash
# Single file (array of apartments or one apartment object)
uv run python -m src.evaluation.validate tests/fixtures/apartments/hand_crafted.json

# Custom tolerance (default: 0.3 m)
uv run python -m src.evaluation.validate my_apartment.json --tol 0.5

# Explicit schema path
uv run python -m src.evaluation.validate my_apartment.json --schema path/to/schema.json
```

**Output** — one line per apartment:

```
PASS  H01
PASS  H02
FAIL  X01
      - entrance [4.0, 0.0] not on outer polygon (nearest edge 2.100 m away, tol 0.3 m)
      - door[0] [2.0, 2.0] touches only 1 room boundary/ies (need ≥ 2, tol 0.3 m)
```

Exit code `0` if every apartment passes; `1` if any fail.

### Python API

```python
from src.evaluation.validate import validate_apartment
import json

data = json.loads(Path("apartment.json").read_text())

# Single apartment dict
errors = validate_apartment(data)                # default tol=0.3 m
errors = validate_apartment(data, tol=0.5)       # looser tolerance
errors = validate_apartment(data, schema_path=Path("my_schema.json"))

if errors:
    for e in errors:
        print(e)
else:
    print("valid")
```

`validate_apartment` always returns a **list of strings** — empty means valid.
All errors are collected before returning (no fail-fast).

---

## Checks performed

Checks run in this order.  All errors are collected; the validator does not
stop at the first failure — **except** after a schema error (see check 1),
because missing required fields would cause subsequent checks to crash.

### 1 — JSON schema (structural)

Validates the apartment dict against
[`tests/fixtures/apartments/schema.json`](../../tests/fixtures/apartments/schema.json).

Catches:
- Missing required top-level fields (`id`, `apartment_type`, `entrance`,
  `outer_polygon`, `outer_is_exterior`, `doors`, `rooms`, `expected_scores`)
- Wrong field types (e.g. `entrance` is not a 2-element number array)
- Invalid enum values for `apartment_type` and `room_type`
- Arrays that are too short (`outer_polygon` and room `polygon` require ≥ 4
  points; `doors` requires ≥ 1 entry)

**If a schema error is found, the validator returns immediately** with only
the schema error.  All further checks assume required fields are present
and correctly typed.

> **Soft dependency:** `jsonschema` is not an explicit project dependency.
> If it is absent, this check is silently skipped and the geometric checks
> still run.  Install it with `uv add jsonschema` if you need schema
> validation.  It is normally available transitively via jupyter.

---

### 2 — `outer_is_exterior` length consistency

`outer_is_exterior` is a boolean flag per outer polygon **edge**.  An
`N`-point closed polyline has `N − 1` edges, so the flag list must have
exactly `N − 1` entries.

```
Error: outer_is_exterior has 3 items but outer_polygon has 4 edges (4 = len(outer_polygon) - 1)
```

This constraint cannot be expressed in JSON Schema (which cannot relate the
lengths of two sibling arrays), so it is checked explicitly.

---

### 3 — Outer polygon closure

The outer polygon must be a closed polyline: the last point must coincide
with the first point within tolerance.

```
Error: outer_polygon not closed: gap 1.000 m (tol 0.3 m)
```

The gap is `‖outer_polygon[0] − outer_polygon[−1]‖₂`.

---

### 4 — Room polygon closure

Same closure check applied to every room polygon.

```
Error: room[0] (Hallway) polygon not closed: gap 1.000 m (tol 0.3 m)
```

---

### 5 — Entrance on outer polygon boundary

The entrance point must lie on one of the outer polygon's edges, i.e.
its point-to-polyline distance must be less than `tol`.

```
Error: entrance [99.0, 99.0] not on outer polygon (nearest edge 130.115 m away, tol 0.3 m)
```

**Distance method:** for each edge `a→b`, the minimum distance from point
`p` to the segment is computed as:

```
t = clamp(dot(p-a, b-a) / |b-a|², 0, 1)
dist = |p - (a + t*(b-a))|
```

The smallest distance across all edges is reported.

---

### 6 — Each door on ≥ 2 room boundaries

Every entry in `doors` must lie on the polygon boundary of **at least two**
rooms (the rooms the door connects).  The validator counts rooms for which
`_poly_dist(door, room_polygon) < tol`.

```
Error: door[0] [99.0, 99.0] touches only 0 room boundary/ies (need ≥ 2, tol 0.3 m)
```

This catches doors that were accidentally placed off the shared wall, or
that connect to only one room (which would break BFS adjacency for
circulation scoring).

---

### 7 — Minimum room area

Each room polygon must have area ≥ 0.5 m².  Smaller rooms are considered
degenerate and indicate a drawing error or a unit mismatch (e.g. mm instead
of m).

```
Error: room[0] (Hallway) area 0.000 m² is below minimum 0.5 m²
```

Area is computed via the shoelace formula:

```
area = 0.5 * |Σ (x[i] * y[i+1] - x[i+1] * y[i])|
```

---

## Tolerance

All geometric checks use a single tolerance `tol` (default **0.3 m**).

This value was chosen to cover two sources of numerical error:

| Source | Typical offset |
|--------|---------------|
| Wall-thickness offsets from `apartment_writer.py` | up to ~0.2 m |
| Floating-point drift in Rhino/GH coordinate export | < 0.01 m |

A 0.3 m tolerance is tight enough to catch genuine geometry errors (a door
placed in the wrong room, an entrance moved to the wrong wall) while
absorbing the expected export noise.

Use `--tol 0.5` if your model uses thick structural walls (> 0.3 m offsets).
Use `--tol 0.1` for stricter validation of analytically constructed fixtures.

---

## Known limitations

The validator deliberately keeps checks simple and fast.  The following
classes of errors are **not** detected:

### Room overlap not checked

Rooms are validated in isolation.  The validator does not check whether room
polygons overlap each other or extend outside the outer boundary.  A layout
where two bedrooms occupy the same physical space will pass.

### Room containment not checked

Individual rooms are not tested for containment inside the outer polygon.
A room could be placed entirely outside the apartment boundary and still
pass.

### Door uniqueness not checked

If the same door point appears twice in `doors`, both entries are validated
independently and no duplicate warning is raised.

### Topology not checked

The validator only verifies that each door touches ≥ 2 room boundaries —
it does not build the full room adjacency graph or check whether the
apartment is connected.  A disconnected apartment (where some rooms are
reachable only through walls, with no valid door path) will pass.  The
circulation scorer (`src/evaluation/circulation.py`, Phase 12) catches
connectivity issues at scoring time.

### Winding order not enforced

CCW polygon winding is **not** required (see Decisions Log in
[`plans/08-floor-plan-representation.md`](../../plans/08-floor-plan-representation.md)).
No current evaluation algorithm needs it.  The area formula returns the
correct area regardless of winding direction.

### `expected_scores` not verified

The `expected_scores` field (`daylight`, `circulation`, `furnitability`) is
validated for type and range by the JSON schema but the validator does not
run the actual scoring functions to confirm the values are consistent with
the geometry.  This is intentional — the validator is a pre-flight check,
not a scoring engine.

### Schema check skipped without `jsonschema`

If the `jsonschema` package is not installed, structural validation (check 1)
is silently skipped.  Geometric checks still run, but type errors, missing
fields, and enum violations go undetected.

---

## File locations

| File | Role |
|------|------|
| `src/evaluation/validate.py` | Validator module + CLI |
| `tests/fixtures/apartments/schema.json` | JSON schema (structural check) |
| `tests/fixtures/apartments/hand_crafted.json` | Hand-crafted test fixtures (H01–H05) |
| `tests/test_validate.py` | Pytest self-test (5 pass + 6 fail + 1 schema) |

---

## Related

- [`tests/fixtures/apartments/README.md`](../../tests/fixtures/apartments/README.md) — fixture format spec and labelling instructions for Luyang
- [`tests/fixtures/apartments/schema.json`](../../tests/fixtures/apartments/schema.json) — full JSON schema with field descriptions
- [`SCORING.md`](../../SCORING.md) — scoring spec (daylight, circulation, composite formula)
- [`plans/08-floor-plan-representation.md`](../../plans/08-floor-plan-representation.md) — Phase 8 plan and decisions log
