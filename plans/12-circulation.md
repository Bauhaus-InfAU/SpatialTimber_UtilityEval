# Phase 12: Circulation Accessibility

## Goal

Check whether every room in an apartment is accessible from the apartment entrance via the hallway. Hallway IS a room type in the RL representation. Uses a room adjacency graph derived from door positions on shared walls.

**Why topological rules are sufficient:** Circulation accessibility is a graph reachability problem — no ML needed. The RL floor plan generator produces a pixel-grid layout (0.6m grid) where rooms are polygons and doors are points on walls. A simple graph traversal fully captures the design intent.

**Depends on:** Phase 8 — `ApartmentLayout`, `RoomLayout`, `WallSegment` dataclasses and test apartments must exist before implementation.

---

## Tasks

- [ ] 12.1 Implement room adjacency graph builder — door-in-shared-wall detection (door of room A lies on a wall edge of room B, within tolerance)
- [ ] 12.2 Implement entrance-hallway connection check — entrance point lies on a wall of the hallway room
- [ ] 12.3 Implement `circulation_score(apartment: ApartmentLayout) → dict` — per-room reachability + aggregate 0–100
- [ ] 12.4 Write pytest tests — ≥6 cases: fully connected, isolated room, no hallway, multiple hallways
- [ ] 12.5 Build verification notebook `notebooks/12-01_circulation_verification.ipynb`
- [ ] 12.6 Write report `reports/12-01_circulation.ipynb` + HTML; update PLAN.md + Notion

---

## Check Logic

**Step 1 — Room adjacency graph:**
- Two rooms A and B are adjacent if: the door of A lies on a wall edge of B (within tolerance), OR the door of B lies on a wall edge of A
- Edge in graph: (room_A, room_B) — undirected

**Step 2 — Entrance-hallway connection:**
- Identify hallway room(s) (room_type = "Hallway")
- The hallway is connected to the entrance if: `apartment.entrance` lies on a wall edge of the hallway polygon (within tolerance)
- If no hallway exists: all non-entrance rooms are unreachable → circulation_score = 0

**Step 3 — Graph reachability:**
- Start BFS/DFS from hallway node(s)
- A room is reachable if it can be reached from hallway via door connections
- Hallway always counts as reachable (it IS the circulation node)

**Score output:**
```python
{
    "rooms": {
        "Bedroom": 100,       # 100 = reachable, 0 = not reachable
        "Living room": 100,
        "Hallway": 100,       # always 100
        "Kitchen": 0,         # isolated — no door to hallway
    },
    "total_rooms": 4,
    "reachable_rooms": 3,
    "circulation_score": 75.0   # (3/4) × 100
}
```

**Tolerance:** 0.05m (5cm) default for door-on-wall detection. Larger than daylight tolerance because door placement may have small numerical errors in the RL generator.

---

## Edge Cases

| Case | Handling |
|------|---------|
| No hallway room | circulation_score = 0; all rooms except entrance-adjacent unreachable |
| Multiple hallway rooms | treat as connected if they share a door; BFS starts from all hallways |
| Room with door but no shared wall with any other room | isolated, score = 0 |
| Entrance opens directly into a non-hallway room | that room is reachable; others only via its doors |

---

## Test Cases (≥6)

| ID | Description | Expected |
|----|-------------|---------|
| T1 | All rooms connected via hallway | circulation_score=100 |
| T2 | One room has no door to hallway | circulation_score < 100 |
| T3 | No hallway room present | circulation_score=0 |
| T4 | Hallway not connected to entrance | circulation_score=0 (or partial if rooms connect to hallway directly) |
| T5 | Two hallway rooms (corridor split) | both count as reachable; BFS explores both |
| T6 | Room connects to another room but not hallway (indirect path) | NOT counted as reachable (must go through hallway) |

---

## Deliverables

| Type | Artifact | Path |
|------|----------|------|
| Tool | Circulation evaluation function | `src/evaluation/circulation.py` |
| Notebook | Verification + graph visualization | `notebooks/12-01_circulation_verification.ipynb` |
| Report | Findings | `reports/12-01_circulation.ipynb` + `.html` |

---

## Decisions Log

- **Phase renamed 11 → 12** (2026-03-01): New Phase 8 (Floor Plan Representation) inserted. Renumbered accordingly.

---

## Key Files

| File | Role |
|------|------|
| `src/evaluation/apartment.py` | Phase 8 deliverable — `ApartmentLayout`, `RoomLayout` |
| `src/evaluation/daylight.py` | Phase 11 deliverable — edge-overlap utility (reuse for door-on-wall detection) |
| `tests/fixtures/apartments/hand_crafted.json` | Phase 8 hand-crafted fixtures |
| `tests/test_daylight.py` | Test pattern to follow |
