# SpatialTimber Utility Evaluator

Reward function toolkit for RL-based apartment layout design — three evaluators (furnishability, daylight, circulation) combined into a composite score.

## Motivation

Reinforcement learning for architectural layout design needs fast, transparent reward signals across multiple utility dimensions. The SpatialTimber project evaluates apartment layouts along three axes:

- **Furnishability** — how well furniture can be placed in each room (ML surrogate, trained on a procedural Grasshopper furnisher)
- **Daylight accessibility** — whether habitable rooms have sufficient window exposure (geometric edge-overlap check)
- **Circulation accessibility** — whether all rooms are reachable from the entrance within a reasonable path length (BFS topological check)

The composite of these three functions is the primary reward signal for the WP2 RL training loop. The furnisher surrogate addresses the speed bottleneck: the procedural furnisher takes seconds per apartment, which is too slow for millions of RL evaluations. Phase 10 also studies how an area-only simplification biases the furnishability estimate relative to the full surrogate.

## Reward Functions

| Function | Method | Phase | Status |
|----------|--------|-------|--------|
| Furnishability | ML surrogate (decision tree + CNN study) | 9–10 | Planned |
| Daylight | Geometric edge-overlap check | 11 | Planned |
| Circulation | BFS topological check | 12 | Planned |
| Composite reward | Weighted mean of the three | 13 | Planned — primary WP2 deliverable |

## Training Data

Training data is stored in `apartments.jsonl` in the sibling repository (`SpatialTimber_FurnisherData`).

### Format

- **JSONL** — one JSON object per line, each representing a single apartment
- **~8,000 apartments**, each containing up to **9 rooms** in a fixed order
- ~80% standard-sized rooms, ~20% deliberately undersized to provide training diversity

### Per-Room Fields

| Field | Description |
|-------|-------------|
| `name` | Room type identifier |
| `active` | Whether the room is present in this apartment |
| `polygon` | Closed polyline outline in meters, axis-aligned, counter-clockwise winding |
| `door` | Door position (point on wall) |
| `score` | Furniture placement quality score (0–100), or `null` if room is absent |

### Room Types

Bedroom, Living room, Bathroom, WC, Kitchen, Children 1–4

### Apartment Types

Studio (combined living/bedroom), 1-Bedroom through 5-Bedroom

### Room Shapes

- **Rectangles** — most common
- **L-shapes** — single corner cut
- **Double-cuts** — U, S, or C shapes (two corner cuts)

## Score

The furnisher score quantifies how well furniture can be placed in a room on a 0–100 scale.

### How It Works

The procedural furnisher builds a tree of placement attempts. Each leaf node scores based on variant counts:
- 0 variants → 0.0
- 1 variant → 0.75
- 2+ variants → 1.0

Node scores aggregate upward through weighted averages, using option weights and level weights, to produce the final room score.

### Score Ranges

| Range | Meaning |
|-------|---------|
| 90–100 | Excellent — furniture fits comfortably |
| 70–89 | Good — acceptable placement |
| 40–69 | Problematic — tight or compromised |
| 1–39 | Poor — barely functional |
| 0 | Failed — no valid placement found |
| `null` | Room absent from apartment |

For the full scoring formula, see the [Furnisher Score documentation](https://www.notion.so/spatialtimber/Furnisher-Score-1d6b1023b22680a9a0c5c7ad80ac8df0).

## Furnishability Component

**Input:** room outline (polygon), door position, room type

**Output:** predicted score (0–100)

The furnishability reward uses a decision-tree surrogate trained on the procedural furnisher. Phase 9 benchmarks its speed/accuracy trade-off; Phase 10 distils it to interpretable area-based rules. The model predicts per-room scores, not per-apartment — each room is scored independently.

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

### Full (training + analysis)

```bash
uv sync                     # creates .venv, installs all deps (incl. PyTorch CUDA)
uv run wandb login           # paste API key from https://wandb.ai/authorize
```

Verify GPU access:
```bash
uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

### Inference only (Grasshopper / Rhino 8)

For running predictions without training dependencies:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install git+https://github.com/Bauhaus-InfAU/SpatialTimber_UtilityEval.git[inference]
```

See `grasshopper/README.md` for Rhino 8 setup details.

## Rasterized Data

Room polygons are converted into 64×64 3-channel images for CNN training. The pre-rasterized dataset is stored in `data/rooms_rasterized.npz` (gitignored — regenerate with `uv run python -m furnisher_surrogate.rasterize`).

### Channels

| Channel | Content |
|---------|---------|
| 0 | **Room mask** — 255 inside polygon, 0 outside |
| 1 | **Wall edges** — 255 on polygon boundary (1px) |
| 2 | **Door marker** — gaussian blob (sigma=2px) at door position |

Each room's longest side is scaled to 60px and centered in the 64×64 grid. Absolute size is not preserved in the image — `area` is stored separately as a numeric feature.

### `.npz` Contents

| Array | Shape | Dtype | Description |
|-------|-------|-------|-------------|
| `images` | `(45880, 3, 64, 64)` | `uint8` | Rasterized room images |
| `scores` | `(45880,)` | `float32` | Ground-truth scores (0–100) |
| `room_type_idx` | `(45880,)` | `int8` | Room type index (0–8) |
| `area` | `(45880,)` | `float32` | Room area in m² |
| `door_rel_x` | `(45880,)` | `float32` | Normalized door x position [0,1] |
| `door_rel_y` | `(45880,)` | `float32` | Normalized door y position [0,1] |
| `apartment_seeds` | `(45880,)` | `int64` | Apartment ID (for train/val/test split) |

All arrays share the same row index. Format: `(N, C, H, W)` — PyTorch convention.

## Apartment JSON Validator

Floor plan files (produced by hand or via `grasshopper/apartment_writer.py`) can
be validated before use in the evaluation module:

```bash
uv run python -m src.evaluation.validate tests/fixtures/apartments/hand_crafted.json
```

Checks: JSON schema, polygon closure, entrance on outer boundary, each door
touching ≥ 2 room boundaries, minimum room area (0.5 m²).  Default tolerance
is 0.3 m — adjustable with `--tol`.

See [`src/evaluation/VALIDATE.md`](src/evaluation/VALIDATE.md) for the full
specification, including known limitations.

## Data Location

Training data lives in the sibling repository:

```
../SpatialTimber_DesignExplorer/Furnisher/Apartment Quality Evaluation/apartments.jsonl
```
