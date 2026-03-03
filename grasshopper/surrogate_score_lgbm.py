#! python 3
# r: numpy, joblib, lightgbm, scikit-learn
"""LightGBM surrogate score predictor — GhPython component for Rhino 8.

Dependencies auto-installed via ``# r:`` above: numpy, joblib, lightgbm,
scikit-learn. The furnisher_surrogate package must be installed manually
once — see grasshopper/README.md for instructions.

Inputs (set in Grasshopper component):
    polygon : Polyline  — room boundary (closed polyline)
    door    : Point3d   — door position on wall
    room_type : str     — one of: Bedroom, Living room, Bathroom, WC,
                          Kitchen, Children 1-4
    apartment_type : str — one of: Studio (bedroom), Studio (living),
                           1-Bedroom, 2-Bedroom, 3-Bedroom, 4-Bedroom,
                           5-Bedroom
    model_path : str    — full path to .joblib model file

Output:
    score : float — predicted furniture placement score (0-100)
"""

import numpy as np
import joblib

from furnisher_surrogate.data import Room, ROOM_TYPE_TO_IDX, APT_TYPE_TO_IDX
from furnisher_surrogate.features import extract_features

# Convert Rhino Polyline → numpy (N, 2) array
poly_np = np.array(
    [[pt.X, pt.Y] for pt in polygon],
    dtype=np.float64,
)

# Ensure closed polyline
if not np.allclose(poly_np[0], poly_np[-1]):
    poly_np = np.vstack([poly_np, poly_np[0:1]])

# Convert Rhino Point3d → numpy (2,) array
door_np = np.array([door.X, door.Y], dtype=np.float64)

# Resolve apartment type
apt = apartment_type if apartment_type else "2-Bedroom"

# Build Room dataclass for feature extraction
room = Room(
    polygon=poly_np,
    door=door_np,
    room_type=room_type,
    room_type_idx=ROOM_TYPE_TO_IDX[room_type],
    score=None,
    apartment_type=apt,
    apartment_type_idx=APT_TYPE_TO_IDX[apt],
)

# Extract features and predict
features = extract_features(room).reshape(1, -1)
model = joblib.load(model_path)
raw_score = model.predict(features)[0]
score = float(np.clip(raw_score, 0.0, 100.0))
