# Phase 10: Simple Furnisher Surrogate — Decision Tree

## Goal

Build a transparent, interpretable pass/fail model for furnishability that serves as the primary RL reward for furnishability. The model must be auditable — a researcher can trace any prediction back to a rule and adjust thresholds without retraining.

**Why a decision tree:** Area thresholds from EDA already explain most of the pass/fail pattern. A depth-4 decision tree on (area, room_type, apartment_type) will capture this cleanly and can be exported as Python if/else rules — no sklearn at inference.

---

## Tasks

- [ ] 10.1 Binarize scores in training/test splits — fail (score=0) → 0, pass (score>0) → 1
- [ ] 10.2 Train decision tree (depth ≤4) + cross-validate — sklearn DecisionTreeClassifier, class_weight="balanced"
- [ ] 10.3 Evaluate: precision/recall/F1 per room type, confusion matrix
- [ ] 10.4 Benchmark vs complex surrogate (LightGBM + CNN v4 as binary classifiers) on same test set
- [ ] 10.5 Export tree as `src/furnisher_surrogate/simple_surrogate.py` — standalone Python rules function
- [ ] 10.6 Visualize tree as a graphical diagram (graphviz export to PNG/SVG) + decision boundary plots per room type — these are **deliverables**, included in the report
- [ ] 10.7 Write report `reports/10-01_simple-surrogate.ipynb` + HTML; update PLAN.md + Notion

---

## Model Specification

**Target:** binary classification — fail (score=0) vs pass (score>0)
- Class imbalance: ~28.6% fail, ~71.4% pass (from EDA)
- Use class_weight="balanced" to handle imbalance

**Features (3):**
- `area` (m²) — continuous, strongest predictor (r=+0.37 with score)
- `room_type_idx` — integer 0–8, encodes room type
- `apartment_type_idx` — integer 0–6, encodes apartment type

**Why only 3 features:** The simple surrogate is meant to be transparent and auditable. Area + room type + apartment type are all geometrically meaningful. Door position and polygon vertex details add complexity without much interpretability benefit.

**Model:** sklearn `DecisionTreeClassifier`
- `max_depth=4` (starts with 4; test 3 and 5 as alternatives)
- `class_weight="balanced"`
- No pruning (keep it simple; depth constraint handles overfitting)

---

## Export Format (`simple_surrogate.py`)

The exported function must be pure Python, no sklearn dependency:

```python
def predict_furnishable(area: float, room_type_idx: int, apartment_type_idx: int) -> int:
    """
    Returns 1 (pass) or 0 (fail) based on decision tree rules.
    Exported from decision tree trained YYYY-MM-DD. Test F1: 0.XX.
    """
    if area <= X.XX:
        ...  # depth-4 if/else tree
    return 1
```

The function docstring must include training date and test F1 for traceability.

---

## Benchmark Against Complex Models

Compare on binary classification (same test split as Phases 5 & 6):
- Decision tree (this phase)
- LightGBM 21f → threshold predictions at score>0
- CNN v4 → threshold predictions at score>0

Metrics: precision, recall, F1 (macro and per room type), AUC-ROC.

**Expected outcome:** Decision tree will have slightly lower AUC than LightGBM/CNN, but will be far faster and transparent. If F1 gap > 5 points, investigate why and consider depth=5.

---

## Deliverables

| Type | Artifact | Path |
|------|----------|------|
| Tool | Simple surrogate (Python rules) | `src/furnisher_surrogate/simple_surrogate.py` |
| Notebook | Training + benchmark analysis | `notebooks/10-01_simple_surrogate.ipynb` |
| Report | Findings + model card | `reports/10-01_simple-surrogate.ipynb` + `.html` |
| Visualization | Decision tree diagram (graphviz) | `reports/10-01_simple-surrogate.png` |
| Visualization | Decision boundary plots (per room type) | embedded in notebook/report |

---

## Decisions Log

- **Phase renamed 9 → 10** (2026-03-01): New Phase 8 (Floor Plan Representation) inserted before the benchmark (Phase 9). Renumbered accordingly.
- **Decision tree visualization is a required deliverable** (2026-03-01): Graphviz export to PNG/SVG and per-room-type decision boundary plots are required in the report, not optional exploratory output.

---

## Key Files

| File | Role |
|------|------|
| `src/furnisher_surrogate/data.py` | `load_apartments()`, split functions |
| `src/furnisher_surrogate/features.py` | Feature extraction (area, room_type_idx, apt_type_idx) |
| `models/baseline_lgbm.joblib` | LightGBM benchmark model |
| `models/cnn_v4.pt` | CNN v4 benchmark model |
| `reports/03-01_eda-findings.ipynb` | Area thresholds, score distribution, failure analysis |
| `reports/03-03_apartment_type_eda.ipynb` | Apartment type effects on failure rates |
