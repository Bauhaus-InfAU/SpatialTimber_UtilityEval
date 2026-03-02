# FurnisherSurrogate — ML Strategy

Surrogate model to predict furniture placement scores (0–100) for residential rooms. Two models: tabular baseline (LightGBM) and CNN on rasterized images.

**Data**: 8,322 apartments, 45,880 active rooms | Bimodal scores: 13k zeros + 19k excellent (90–100) | Mean 62.2, median 85.0
**System**: Python 3.12, uv, RTX 4060 8GB, Rhino 8 (CPython)
**Data location**: `../SpatialTimber_DesignExplorer/Furnisher/Apartment Quality Evaluation/apartments.jsonl`

---

## Progress

| # | Phase | Tasks | Status | Plan |
|---|-------|-------|--------|------|
| 1 | **Setup** | 6/6 | `done` | [details](plans/01-setup.md) |
| 2 | **Data Pipeline** | 5/5 | `done` | [details](plans/02-data-pipeline.md) |
| 3 | **EDA** | 13/13 | `done` | [details](plans/03-eda.md) |
| 4 | **Rasterization** | 4/4 | `done` | [details](plans/04-rasterization.md) |
| 5 | **Baseline Model** | 5/5 | `done` | [details](plans/05-baseline-model.md) |
| 6 | **CNN Model** | 6/6 | `done` | [details](plans/06-cnn-model.md) |
| 7 | **Grasshopper** | 9/9 | `done` | [details](plans/07-grasshopper.md) |
| 8 | **Floor Plan Representation + Test Set** | 0/6 | `pending` | [details](plans/08-floor-plan-representation.md) |
| 9 | **Speed/Accuracy Benchmark** | 0/7 | `pending` | [details](plans/09-accuracy-benchmark.md) |
| 10 | **Simple Furnisher Surrogate** | 0/7 | `pending` | [details](plans/10-simple-surrogate.md) |
| 11 | **Daylight Accessibility** | 0/6 | `pending` | [details](plans/11-daylight.md) |
| 12 | **Circulation Accessibility** | 0/6 | `pending` | [details](plans/12-circulation.md) |
| 13 | **Combined Reward + GH Integration** | 0/7 | `pending` | [details](plans/13-combined-reward.md) |
| | **Total** | **48/85** | | |

## Documentation Strategy

Each fact lives in **one place**. See [CLAUDE.md](CLAUDE.md) for full protocol. Use `/document` to trigger updates.

| File | Owns | Updated |
|------|------|---------|
| README.md | Project description, data format, setup | At milestones |
| CLAUDE.md | Current state, findings, conventions | Each session end |
| PLAN.md + plans/ | Strategy, decisions, progress | As work progresses |
| W&B | Experiment metrics, curves, artifacts | During training |
| Notebooks | Self-contained analyses | During analysis |

## Project Structure

```
SpatialTimber_FurnisherSurrogate/
├── PLAN.md                        # This overview
├── SCORING.md                     # Score definitions, ranges, aggregation rules (Phase 8)
├── plans/                         # Detailed phase plans
├── src/furnisher_surrogate/       # Python package
│   ├── data.py                    # JSONL loading, splitting
│   ├── features.py                # Numeric feature extraction
│   ├── rasterize.py               # Polygon → 64x64 image
│   ├── models.py                  # CNN architecture
│   ├── train.py                   # Training loop
│   └── predict.py                 # Inference API
├── notebooks/                     # Jupyter notebooks (analysis, exploration)
├── reports/                       # Findings reports (narrative notebooks + HTML)
├── grasshopper/                   # GhPython components
├── models/                        # Saved artifacts (.pt, .joblib)
├── tests/                         # Pytest suite (fixtures, test_predict.py)
└── tickets/                       # Deferred features, bugs, improvements
```

## Known Limitations

1. **Axis-aligned rooms only** — current data is orthogonal. Real plans are often non-orthogonal. Future: new training data + vertex-level rotation augmentation. [details](plans/06-cnn-model.md#known-limitations)
2. **Fixed 9 room types, 7 apartment types** — adding types requires retraining
3. **Algorithm-specific** — approximates this furnisher's scoring, not objective quality

## Verification Checklist

- [x] Data loads correctly, all 45,880 active rooms parsed
- [x] Feature extraction produces valid values (no NaN, area > 0)
- [x] Rasterized images visually match original room shapes
- [x] Train/val/test split has no apartment leakage
- [x] W&B dashboard shows metrics and artifacts
- [x] Baseline MAE reported and reasonable (8.24 with apt_type, 11.02 without)
- [x] CNN MAE improves over baseline (or we understand why not) — v4 slightly beats LightGBM (8.07 vs 8.24)
- [x] predict_score() API matches manual pipeline (bit-exact, 7 fixture rooms verified)
- [x] apartment_type added across full stack (data, features, models, inference, GH component)
- [x] Grasshopper component returns predictions in Rhino 8

## Decisions Log

- **WP2 scope narrowed to furnisher surrogate** (2026-02-23): Daylight and accessibility evaluators are fast enough to remain procedural (WP1). Only furnishability needs a DNN surrogate.
- **Phase 8 revised: validity testing → speed/accuracy benchmark** (2026-02-28): Testing the procedural script's validity is WP1 scope. Phase 8 now focuses on the speed/accuracy trade-off, which is WP2-relevant.
- **WP2 scope expanded: simple reward toolkit for RL** (2026-02-28): The actual WP2 deliverable for RL training needs more than the complex surrogate. Added: simple pass/fail furnisher (decision tree), daylight check, circulation check, and combined reward API. Rationale: at the current RL stage (prove-RL-works), simple + transparent + fast rewards are more valuable than accurate + opaque ones. For daylight and circulation, simple geometric rules are sufficient — unlike furnishability, which required the full ML pipeline because no analytical model existed.
- **Phase structure revised: representation phase inserted** (2026-03-01): New Phase 8 dedicated to the shared floor plan representation, test set specification, and scoring documentation. Phases 9–13 renumbered from old 8–12. Test set outsourced to Luyang (existing cleaned floor plan database) plus 5 hand-crafted fixtures to unblock development. Combined reward (Phase 13) expanded to include GH integration.
