# Phase 9: Speed & Accuracy Trade-Off Benchmark

## Goal

Quantify the speed/accuracy trade-off between the complex ML surrogate (CNN v4, LightGBM) and the procedural furnisher it approximates. Measure both Python and Grasshopper timing so the comparison is apples-to-apples (procedural runs in GH; surrogate comparison must also include GH timing). Document the case for using the surrogate in RL training, where inference latency is critical.

**Scope note:** Testing the procedural script's validity is WP1 scope. This phase focuses solely on speed and accuracy differences that are WP2-relevant.

---

## Tasks

- [x] 9.1 Generate synthetic test set (`tests/phase9_benchmark.json`) — 180 rooms (9 types × 5 quintiles × 2 shapes × 2), rect + L-shape, via `scripts/generate_benchmark_set.py`
- [x] 9.2 Run surrogate timing benchmark (Python) — ms/room for CNN v4 and LightGBM; cold-start + warm times; results in `results/phase9_python_timing.json`
- [ ] 9.3 Run procedural timing in Grasshopper (Rhino, manual) — all 180 rooms batch; record total wall-clock time
- [ ] 9.4 Run surrogate timing in Grasshopper — same 180 rooms through `surrogate_score.py` (CNN) and `surrogate_score_lgbm.py` (LightGBM) GH components; template at `results/phase9_gh_timing_template.json`
- [x] 9.5 Build analysis notebook `notebooks/09-01_speed_accuracy.ipynb` — all charts: speed bar chart (log), R² scatter, residuals, per-type MAE, error distribution, best/worst 20 galleries, speed-up table. GH speed charts use placeholders until 9.3/9.4 complete.
- [x] 9.6 Write findings report `reports/09-01_speed-accuracy-tradeoff.ipynb` — narrative + all figures; per-room-type breakdown. HTML export pending notebook execution.
- [x] 9.7 Update PLAN.md + Notion

**Blocked:** Tasks 9.3 and 9.4 require Iuliia's procedural furnisher script to run in Grasshopper. GH timing charts use placeholder values until then.

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
- **Synthetic set expanded to rect + L-shape** (2026-03-03): 180 rooms total (9 types × 5 quintiles × 2 shapes × 2 rooms). L-shapes (6 vertices, corner notch) added to test beyond simple rectangles.
- **LightGBM GH component created** (2026-03-03): `grasshopper/surrogate_score_lgbm.py` enables apples-to-apples GH timing comparison between CNN and LightGBM.
- **LightGBM outperforms CNN on test set** (2026-03-03): LightGBM MAE=7.58 vs CNN MAE=9.69 on held-out test (4,594 rooms). LightGBM also faster. Recommended as RL reward function.
- **GH timing blocked on Iuliia** (2026-03-03): Tasks 9.3–9.4 require Iuliia's procedural furnisher script to run the batch timing in Grasshopper. Python surrogate timing and accuracy analysis complete; GH speed charts use placeholder values. Report and notebook updated with all available data.

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
