import json

# Inference modules are bundled inside the backend app (app/ml/*) so the API
# is self-contained and deployable without the ml/ source tree being present.
# The files are kept in lockstep with ml/src/* via a sync script.
from app.ml.predict import predict_one, load_bundle  # noqa: E402

from sqlalchemy.orm import Session
from app.database.db import PredictionHistory


def run_prediction(payload: dict) -> dict:
    return predict_one(payload)


def save_prediction(db: Session, payload: dict, result: dict, user_id: int = None) -> PredictionHistory:
    record = PredictionHistory(
        user_id=user_id,
        content_type=payload.get("content_type"),
        creator_category=payload.get("creator_category"),
        account_type=payload.get("account_type"),
        input_json=json.dumps(payload),
        performance_score=result["performance_score"],
        performance_category=result["performance_category"],
        expected_views=result["expected_views"],
        expected_engagement_rate=result["expected_engagement_rate"],
        result_json=json.dumps(result),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_model_info() -> dict:
    bundle = load_bundle()
    return {
        "best_model_names": bundle["best_model_names"],
        "test_metrics": bundle["test_metrics"],
        "top_feature_importance": [
            {"feature": f, "importance": float(i)} for f, i in bundle["top_feature_importance"]
        ],
        "feature_columns": bundle["feature_columns"],
        "random_state": bundle["random_state"],
        "data_quality": bundle.get("data_quality"),
    }
