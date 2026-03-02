# Phase 13: Combined Reward Function + GH Integration

## Goal

Integrate all 3 evaluation functions into a single Python API for the RL training loop. Implement and test the combined reward as a Grasshopper component. Produces a structured result at room, apartment, and aggregate level — this is the primary WP2 deliverable for RL training.

**Design principle:** Pure Python, no PyTorch, no sklearn at inference. The decision tree is exported as if/else rules (Phase 10). Target: <5ms per apartment on CPU.

---

## Tasks

- [ ] 13.1 Implement `src/evaluation/reward.py` — `compute_reward()` combining all 3 functions (furnishability, daylight, circulation)
- [ ] 13.2 Write integration tests in `tests/test_reward.py` — full apartment round-trip using Phase 8 test apartments (hand-crafted + Luyang's labeled cases with known expected scores)
- [ ] 13.3 Benchmark reward function speed — target <5ms per apartment on CPU; report ms/apartment; profile if target is missed
- [ ] 13.4 Build GH component `grasshopper/reward_score.py` — takes apartment layout JSON string, returns per-room scores + all aggregates
- [ ] 13.5 Test GH component in Rhino 8 with Phase 8 test apartments (labeled expected scores); verify outputs match Python API
- [ ] 13.6 Write report `reports/13-01_combined-reward.ipynb` + HTML
- [ ] 13.7 Update PLAN.md + Notion + README + SCORING.md (if any adjustments from implementation)

---

## API Design

```python
from src.evaluation.reward import compute_reward
from src.evaluation.apartment import ApartmentLayout

result = compute_reward(apartment, weights=(1/3, 1/3, 1/3))
# → ApartmentScore
```

### Data Classes

```python
@dataclass
class RoomScore:
    room_type: str
    furnitability: float   # 0 or 100 (from simple surrogate, Phase 10)
    daylight: float        # 0 or 100 (Phase 11)
    circulation: float     # 0 or 100 (Phase 12)

@dataclass
class ApartmentScore:
    rooms: tuple[RoomScore, ...]
    furnitability: float   # aggregate 0–100 (mean over applicable rooms)
    daylight: float        # aggregate 0–100
    circulation: float     # aggregate 0–100
    score: float           # single composite: weighted mean of 3 aggregates
```

### `compute_reward` Signature

```python
def compute_reward(
    apartment: ApartmentLayout,
    weights: tuple[float, float, float] = (1/3, 1/3, 1/3)
) -> ApartmentScore:
    """
    Compute combined reward for an apartment layout.

    Weights: (furnitability_weight, daylight_weight, circulation_weight).
    Default: equal weight (1/3 each). Must sum to 1.0.
    """
```

---

## GH Component Spec (`grasshopper/reward_score.py`)

**Input:** apartment layout as JSON string (matching Phase 8 schema)
**Output:**
- `room_scores` — list of dicts (room_type, furnitability, daylight, circulation)
- `furnitability` — aggregate float 0–100
- `daylight` — aggregate float 0–100
- `circulation` — aggregate float 0–100
- `score` — composite float 0–100

**Implementation:** Parses JSON → builds `ApartmentLayout` → calls `compute_reward()` → serializes output. Uses the same `compute_reward()` call as the Python API (no duplicate logic).

**Testing in Rhino 8:** Load Phase 8 test apartments (at least H01–H05 hand-crafted + D01–D05 daylight cases + C01–C05 circulation cases) as JSON; verify GH outputs match Python API outputs exactly.

---

## Aggregation Rules

| Component | Applies to | Aggregate formula |
|-----------|------------|-------------------|
| Furnitability | All rooms with `room_type` in ROOM_TYPES (Phase 10 covers all 9 types) | mean(per-room scores) |
| Daylight | Habitable rooms only (Bedroom, Living room, Kitchen, Children 1–4) | (rooms_with_daylight / habitable_rooms) × 100; if no habitable rooms: 100 |
| Circulation | All rooms | (reachable_rooms / total_rooms) × 100 |

**Composite score:** `score = w1 × furnitability + w2 × daylight + w3 × circulation`

---

## Integration Test Structure

```python
def test_full_apartment_round_trip():
    """Create a valid apartment, compute reward, check all fields populated."""
    apt = make_test_apartment(...)  # fixture: 2-bed, 4 rooms, all connected
    result = compute_reward(apt)
    assert 0 <= result.score <= 100
    assert 0 <= result.furnitability <= 100
    assert 0 <= result.daylight <= 100
    assert 0 <= result.circulation <= 100
    assert len(result.rooms) == 4

def test_labeled_apartments():
    """Verify outputs match expected scores for Phase 8 labeled test cases."""
    for apt_json in load_labeled_test_apartments():
        apt = parse_apartment_layout(apt_json)
        result = compute_reward(apt)
        assert abs(result.daylight - apt_json["expected_scores"]["daylight"]) < 1.0
        assert abs(result.circulation - apt_json["expected_scores"]["circulation"]) < 1.0
```

---

## Speed Benchmark Protocol

- Create 100 synthetic `ApartmentLayout` objects (3–5 rooms each)
- Time 10 runs of `compute_reward` over all 100 apartments; report median ms/apartment
- Target: <5ms per apartment (allows >200 reward evaluations/second in RL loop)
- Run on CPU only (no GPU dependency)
- Profile if target is missed: identify which sub-function dominates

---

## Deliverables

| Type | Artifact | Path |
|------|----------|------|
| Tool | Combined reward function | `src/evaluation/reward.py` |
| Config | Updated package init | `src/evaluation/__init__.py` |
| Component | Grasshopper reward component | `grasshopper/reward_score.py` |
| Report | Integration + speed benchmark + GH verification | `reports/13-01_combined-reward.ipynb` + `.html` |

---

## Decisions Log

- **Phase renamed 12 → 13** (2026-03-01): New Phase 8 (Floor Plan Representation) inserted. Renumbered accordingly.
- **GH integration added to Phase 13** (2026-03-01): The combined reward is the primary RL deliverable. It must be implemented and tested in Grasshopper (where the RL environment runs) — not just as a Python API. GH component uses same `compute_reward()` call; no logic duplication.
- **Simple surrogate used for furnitability** (2026-02-28): The combined reward uses the decision-tree simple surrogate (Phase 10) for furnitability, not CNN v4. Speed is critical in RL — the CNN adds ~10ms/room while the decision tree adds <0.1ms. The Phase 9 benchmark confirms the speed differential. Accuracy loss is acceptable for the "prove RL works" stage.

---

## Key Files

| File | Role |
|------|------|
| `src/furnisher_surrogate/simple_surrogate.py` | Phase 10 deliverable — furnishability rules |
| `src/evaluation/daylight.py` | Phase 11 deliverable — daylight check |
| `src/evaluation/circulation.py` | Phase 12 deliverable — circulation check |
| `src/evaluation/apartment.py` | Phase 8 deliverable — shared input format |
| `tests/fixtures/apartments/hand_crafted.json` | Phase 8 hand-crafted fixtures (labeled) |
| `grasshopper/surrogate_score.py` | Phase 7 GH pattern to follow |
| `SCORING.md` | Score definitions, ranges, aggregation rules |
