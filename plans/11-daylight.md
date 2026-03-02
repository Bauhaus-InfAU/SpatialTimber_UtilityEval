# Phase 11: Daylight Accessibility

## Goal

Implement the daylight accessibility check: does a habitable room have at least one exterior wall (facade access)?

**Why geometric rules are sufficient here:** Unlike furnishability, daylight accessibility has a clear geometric definition — a room has daylight if it touches the apartment's facade. Simple edge-overlap detection is fully sufficient at the current RL development stage.

**Depends on:** Phase 8 — `ApartmentLayout`, `RoomLayout`, `WallSegment` dataclasses and test apartments must exist before implementation.

---

## Tasks

- [ ] 11.1 Write exterior wall detection utility — geometric edge-overlap test with tolerance (wall segment ↔ room edge); add to `src/evaluation/daylight.py`
- [ ] 11.2 Implement `daylight_score(apartment: ApartmentLayout) → dict` — per-room binary + aggregate 0–100
- [ ] 11.3 Write pytest tests for daylight function — ≥6 test cases using Phase 8 hand-crafted fixtures + Luyang's apartments: fully-lit, zero-lit, partial, edge cases
- [ ] 11.4 Build verification notebook `notebooks/11-01_daylight_verification.ipynb`
- [ ] 11.5 Write report `reports/11-01_daylight.ipynb` + HTML
- [ ] 11.6 Update PLAN.md + Notion

---

## Daylight Check Logic

**Definition:** A room "has daylight" if ≥1 of its wall edges overlaps with an exterior wall segment of the apartment.

**Exterior wall detection:**
1. For each edge of the room polygon (consecutive vertex pairs)
2. Check if the edge lies on (or within tolerance of) an exterior `WallSegment` in `apartment.walls`
3. Overlap test: both endpoints of the room edge must be within `tolerance` (default 0.01m) of the wall segment's infinite line, AND the projections fall within the segment's extent

**Habitable rooms requiring daylight:** Bedroom, Living room, Kitchen, Children 1–4. Not: WC, Bathroom, Hallway.

**Score output:**
```python
{
    "rooms": {
        "Bedroom": 100,     # 100 = has daylight, 0 = no daylight
        "Living room": 0,
        ...
    },
    "habitable_rooms": 3,
    "rooms_with_daylight": 2,
    "daylight_score": 66.7   # (2/3) × 100
}
```

**Tolerance:** 0.01m (1cm) default. Parameterizable for testing.

---

## Test Cases (≥6)

| ID | Description | Expected |
|----|-------------|---------|
| T1 | All habitable rooms touch facade | daylight_score=100 |
| T2 | No habitable room touches facade | daylight_score=0 |
| T3 | 2 of 3 habitable rooms touch facade | daylight_score=66.7 |
| T4 | WC and Bathroom only — no habitable rooms | daylight_score=100 (vacuously all habitable rooms pass) |
| T5 | Room edge partially overlaps facade (within tolerance) | counted as daylight |
| T6 | Room edge near but not touching facade (outside tolerance) | not counted |
| T7 | Apartment with no exterior walls specified | raise ValueError |

---

## Deliverables

| Type | Artifact | Path |
|------|----------|------|
| Tool | Daylight evaluation function | `src/evaluation/daylight.py` |
| Notebook | Verification + visual checks | `notebooks/11-01_daylight_verification.ipynb` |
| Report | Findings | `reports/11-01_daylight.ipynb` + `.html` |

---

## Decisions Log

- **Phase renamed 10 → 11** (2026-03-01): New Phase 8 (Floor Plan Representation) inserted. Renumbered accordingly.
- **Representation task removed** (2026-03-01): `ApartmentLayout` dataclasses moved to Phase 8 (task 8.1). Phase 11 now has 6 tasks instead of 7.

---

## Key Files

| File | Role |
|------|------|
| `src/evaluation/apartment.py` | Phase 8 deliverable — `ApartmentLayout`, `RoomLayout`, `WallSegment` |
| `tests/fixtures/apartments/hand_crafted.json` | Phase 8 hand-crafted fixtures |
| `src/furnisher_surrogate/data.py` | Existing dataclass pattern to follow |
| `reports/03-01_eda-findings.ipynb` | Polygon format, room type definitions |
