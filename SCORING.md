# WP2 Reward Scoring System

> **Status:** Stub — full content implemented in Phase 8 (task 8.2).
> This file is the single source of truth for all score definitions, ranges, and aggregation rules.
> Update this file during Phase 8 implementation and Phase 13 if any adjustments arise.

---

## Score Domains (3 total)

### 1. Furnishability
Per-room: 0 (fail) or 100 (pass) — decision tree surrogate (area, room_type, apt_type)
Applicable rooms: all 9 room types (Bedroom, Living room, Bathroom, WC, Kitchen, Children 1–4)
Apartment aggregate: mean(per-room) across all rooms

### 2. Daylight Accessibility
Per-room: 0 (no exterior wall edge) or 100 (≥1 exterior wall edge)
Applicable rooms: Bedroom, Living room, Kitchen, Children 1–4
Not applicable: WC, Bathroom, Hallway
Apartment aggregate: (rooms_with_daylight / habitable_rooms) × 100
Edge case: if no habitable rooms → apartment score = 100

### 3. Circulation Accessibility
Per-room: 0 (not reachable from entrance via hallway) or 100 (reachable)
Applicable rooms: all rooms; Hallway always = 100
Apartment aggregate: (reachable_rooms / total_rooms) × 100
Edge case: no hallway → all rooms score 0; apartment score = 0

---

## Composite Apartment Score

```
score = w1 × furnitability + w2 × daylight + w3 × circulation
```

Default weights: w1 = w2 = w3 = 1/3 (configurable)
Range: 0–100

---

## Output Structure (`ApartmentScore`)

```python
rooms: tuple[RoomScore(room_type, furnitability, daylight, circulation), ...]
furnitability: float   # 0–100, aggregate
daylight: float        # 0–100, aggregate
circulation: float     # 0–100, aggregate
score: float           # 0–100, composite
```

---

## Applicable Room Types

| Room type | Furnishability | Daylight | Circulation |
|-----------|---------------|----------|-------------|
| Bedroom | ✓ | ✓ | ✓ |
| Living room | ✓ | ✓ | ✓ |
| Kitchen | ✓ | ✓ | ✓ |
| Children 1–4 | ✓ | ✓ | ✓ |
| Bathroom | ✓ | — | ✓ |
| WC | ✓ | — | ✓ |
| Hallway | ✓ | — | always 100 |

---

## Score Ranges

| Score | Meaning |
|-------|---------|
| 90–100 | Excellent |
| 70–89 | Good |
| 40–69 | Problematic |
| 1–39 | Poor |
| 0 | Failed / absent |
| null | Room not present in apartment |
