# Phase 9: Speed & Accuracy Trade-Off Benchmark

## Goal

Quantify the speed/accuracy trade-off between the complex ML surrogate (CNN v4, LightGBM) and the procedural furnisher it approximates. Measure both Python and Grasshopper timing so the comparison is apples-to-apples (procedural runs in GH; surrogate comparison must also include GH timing). Document the case for using the surrogate in RL training, where inference latency is critical.

**Scope note:** Testing the procedural script's validity is WP1 scope. This phase focuses solely on speed and accuracy differences that are WP2-relevant.

---

## Tasks

- [ ] 9.1 Generate synthetic test set (`tests/phase9_benchmark.json`) — 100–200 rooms, all 9 room types, stratified by area quintile, valid orthogonal polygons
- [ ] 9.2 Run surrogate timing benchmark (Python) — ms/room for CNN v4 and LightGBM; report cold-start and warm (cached model) times
- [ ] 9.3 Run procedural timing in Grasshopper (Rhino, manual) — seconds/room on a sample of 20 rooms; report median
- [ ] 9.4 Run surrogate timing in Grasshopper — run the same 20 rooms through the `surrogate_score.py` GH component; measure ms/room in Rhino; compare to Python timing
- [ ] 9.5 Build analysis notebook `notebooks/09-01_speed_accuracy.ipynb` — required graphical outputs: (1) grouped bar chart Python-LightGBM / Python-CNN / GH-LightGBM / GH-CNN / GH-Procedural on log-scale ms/room; (2) paired scatter surrogate vs procedural score (y=x line, coloured by room type); (3) speed-up factor table GH-LightGBM vs GH-Procedural and Python-LightGBM vs GH-Procedural
- [ ] 9.6 Write findings report `reports/09-01_speed-accuracy-tradeoff.ipynb` + HTML export — narrative + all figures from 9.5; per-room-type error breakdown
- [ ] 9.7 Update PLAN.md + Notion

---

## Synthetic Test Set Design

**Size:** 100–200 rooms (target 150) across 9 room types, stratified by area quintile within each room type.

**Generation approach:**
- Sample area from each quintile of the training distribution per room type
- Generate orthogonal rectangles with valid aspect ratios (AR ≤ 3:1)
- Place door at midpoint of one wall (randomize which wall)
- Sample apartment_type uniformly across 7 types
- All polygons: closed CCW, 4 vertices (simple rectangles), meters

**Why synthetic:** `tests/fixtures/test_rooms.json` has only 7 rooms — too small for a statistically meaningful speed/accuracy benchmark. The synthetic set covers the full input distribution without manual data collection.

---

## Timing Protocol

**Surrogate (Python):**
- Warm the model (1 dummy call before timing)
- Time 3 runs of the full benchmark set; report per-room median
- Measure both CNN v4 and LightGBM separately
- Include model load time (cold-start) as separate metric

**Procedural (Grasshopper):**
- Run 20 rooms manually in the existing `test.gh` file
- Record wall-clock time per room
- Report median; note whether Rhino startup time is included

**Surrogate (Grasshopper):**
- Run the same 20 rooms through `grasshopper/surrogate_score.py` GH component
- Record wall-clock time per room
- Report median for both LightGBM and CNN v4
- Compare to Python timing (overhead of GH/CPython bridge)

**Rationale for GH surrogate timing:** The procedural furnisher runs in GH. For a fair comparison, both the surrogate and the procedural must be timed in the same environment. Python timings are additional context for RL loop planning (where Python inference matters).

---

## Required Graphical Outputs

1. **Grouped bar chart** — Python-LightGBM / Python-CNN / GH-LightGBM / GH-CNN / GH-Procedural timing (log-scale ms/room). Required for the report.
2. **Paired scatter** — surrogate prediction vs procedural score (y=x line, coloured by room type). Required for the report.
3. **Speed-up factor table** — GH-LightGBM vs GH-Procedural, Python-LightGBM vs GH-Procedural, absolute and relative. Required for the report.
4. **Per-room-type error breakdown** — MAE for each of the 9 room types. Required for the report.

---

## Deliverables

| Type | Artifact | Path |
|------|----------|------|
| Dataset | Synthetic benchmark test set | `tests/phase9_benchmark.json` |
| Notebook | Speed/accuracy analysis + figures | `notebooks/09-01_speed_accuracy.ipynb` |
| Report | Findings + timing charts + scatter + error breakdown | `reports/09-01_speed-accuracy-tradeoff.ipynb` + `.html` |

---

## Decisions Log

- **Phase renamed 8 → 9** (2026-03-01): New Phase 8 (Floor Plan Representation) inserted before this phase. Renumbered accordingly.
- **GH surrogate timing added** (2026-03-01): Procedural runs in GH; surrogate comparison must include GH timing for a fair apples-to-apples comparison. Python timings remain as additional context for RL loop planning.
- **Graphical outputs required** (2026-03-01): Bar chart, paired scatter, and speed-up table are required deliverables — not optional. Report must include all figures.
- **Phase 9 rescoped: validity testing → speed/accuracy benchmark** (2026-02-28): Testing the procedural script's validity (checking hypotheses about edge cases, OOD inputs, non-orthogonal rooms) is WP1 scope. Phase 9 now documents the speed/accuracy trade-off, which is the WP2-relevant question for RL reward function selection.

---

## Key Files

| File | Role |
|------|------|
| `src/furnisher_surrogate/predict.py` | `predict_score()` inference entry point |
| `tests/fixtures/test_rooms.json` | Existing 7 test rooms — format reference |
| `grasshopper/surrogate_score.py` | GH component for surrogate inference |
| `models/baseline_lgbm.joblib` | LightGBM model checkpoint |
| `models/cnn_v4.pt` | CNN v4 model checkpoint |
| `reports/03-01_eda-findings.ipynb` | EDA: score distributions, training data boundaries |
