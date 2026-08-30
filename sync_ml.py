#!/usr/bin/env python3
"""
sync_ml.py

Keeps the backend's bundled inference code (backend/app/ml) in sync with the
canonical ML source (ml/src). Run after editing ml/src/feature_engineering.py
or ml/src/predict.py, and after retraining (ml/src/train.py writes the bundle).

    python sync_ml.py

It copies the runtime-only inference modules the API needs. Training-only
modules (preprocessing, train, generate_dataset, etc.) are intentionally not
copied - the backend never runs training.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "ml" / "src"
DST = ROOT / "backend" / "app" / "ml"

# Runtime modules required by the API's prediction_service.
FILES = ["feature_engineering.py", "predict.py"]

if __name__ == "__main__":
    (DST / "__init__.py").parent.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src, dst = SRC / name, DST / name
        if not src.exists():
            raise FileNotFoundError(f"Missing source module: {src}")
        shutil.copy2(src, dst)
        print(f"synced {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")
    print("Done. Re-build/re-deploy the backend for changes to take effect.")
