"""
predict.py

Loads the trained model bundle and exposes a single `predict_one(payload)`
function that:
  1. builds a 1-row DataFrame from the input
  2. applies the SAME feature engineering used at train time
  3. transforms with the SAME fitted preprocessor
  4. gets predictions from all three models
  5. derives a 0-100 performance score + category
  6. computes per-prediction "important factors" (local explanation)
  7. generates recommendations

IMPORTANT: this bundle was trained on a dataset where no feature showed a
measurable relationship with any target (see bundle["data_quality"] and the
README "Dataset"/"Limitations" sections). The final models are therefore
baseline (mean / class-prior) predictors, not learned ones. This module
still runs the full pipeline honestly - it surfaces bundle["data_quality"]
in every response and adjusts the "important factors" and recommendations
sections accordingly, rather than inventing false confidence.

This module has no FastAPI/Pydantic dependency so it can be unit tested or
reused from a notebook/CLI directly.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

_THIS_DIR = Path(__file__).resolve().parent
sys_path_added = str(_THIS_DIR)
import sys
if sys_path_added not in sys.path:
    sys.path.insert(0, sys_path_added)

from feature_engineering import add_engineered_features, ALL_FEATURES  # noqa: E402

_BUNDLE = None


def _bundle_path() -> Path:
    # Prefer the copy shipped with the backend; fall back to ml/models/
    candidates = [
        _THIS_DIR.parent.parent / "backend" / "models" / "content_performance_bundle.joblib",
        _THIS_DIR.parent / "models" / "content_performance_bundle.joblib",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        "content_performance_bundle.joblib not found. Run `python ml/src/train.py` first."
    )


def load_bundle(force_reload: bool = False):
    global _BUNDLE
    if _BUNDLE is None or force_reload:
        _BUNDLE = joblib.load(_bundle_path())
    return _BUNDLE


def _display_label(clean_name: str) -> str:
    # Human-readable labels for the raw (possibly one-hot dummy) feature names
    # surfaced by permutation importance, e.g. "content_type_reel" -> "Content Type".
    label_map = {
        "historical_engagement_score": "Historical Engagement Score",
        "historical_engagement_rate": "Historical Engagement Rate",
        "followers": "Follower Count",
        "historical_avg_views": "Historical Average Views",
        "follower_normalized_performance": "Follower-Normalized Performance",
        "creator_experience_score": "Creator Experience Score",
        "account_age_months": "Account Age",
        "posting_hour": "Posting Hour",
        "hashtag_density": "Hashtag Density",
        "has_call_to_action": "Call-to-Action",
        "is_weekend": "Weekend Post",
        "description_length": "Caption Length",
        "hashtags": "Hashtag Count",
    }
    if clean_name in label_map:
        return label_map[clean_name]
    if clean_name.startswith("content_type_"):
        return "Content Format"
    if clean_name.startswith("posting_hour_category_"):
        return "Posting Time Window"
    if clean_name.startswith("creator_category_"):
        return "Creator Category"
    if clean_name.startswith("account_type_"):
        return "Account Type"
    if clean_name.startswith("day_of_week_"):
        return "Day of Week"
    if clean_name.startswith("description_length_category_"):
        return "Caption Length"
    return clean_name.replace("_", " ").title()


def _describe_factor(clean_name: str, raw: dict, eng: pd.DataFrame) -> str:
    row = eng.iloc[0]
    descriptions = {
        "historical_engagement_score": f"Historical engagement score is {row['historical_engagement_score']:.2f} "
                                        f"(derived from past reach + engagement rate).",
        "historical_engagement_rate": f"Historical engagement rate: {raw.get('historical_engagement_rate')}%.",
        "followers": f"Follower count: {raw.get('followers'):,}.",
        "historical_avg_views": f"Historical average reach: {raw.get('historical_avg_views'):,}.",
        "follower_normalized_performance": f"Follower-normalized historical performance: "
                                            f"{row['follower_normalized_performance']:.3f}.",
        "creator_experience_score": f"Creator experience score: {row['creator_experience_score']:.2f}.",
        "account_age_months": f"Account age (observed): {raw.get('account_age_months')} months.",
        "posting_hour": f"Posting hour: {raw.get('posting_hour')}:00.",
        "has_call_to_action": "Includes a call-to-action." if raw.get("has_call_to_action") else "No call-to-action.",
        "hashtags": f"Hashtag count: {raw.get('hashtags')}.",
        "description_length": f"Caption length: {raw.get('description_length')} characters.",
    }
    if clean_name in descriptions:
        return descriptions[clean_name]
    if clean_name.startswith("content_type_"):
        return f"Content format is {raw.get('content_type')}."
    if clean_name.startswith("creator_category_"):
        return f"Creator category is {raw.get('creator_category')}."
    if clean_name.startswith("account_type_"):
        return f"Account type is {raw.get('account_type')}."
    if clean_name.startswith("posting_hour_category_"):
        return f"Posting time window: {row['posting_hour_category']}."
    return clean_name.replace("_", " ")


def _local_important_factors(bundle, raw_row: dict, engineered_row: pd.DataFrame, top_n: int = 5):
    """
    Approximate local feature contribution using the model's global
    permutation-importance ranking. This is a lightweight, dependency-free
    explanation approach - documented as such rather than passed off as
    true SHAP values.

    NOTE: with this bundle's baseline models, every permutation importance
    is 0.0 (the model's output genuinely does not depend on any input
    feature - see bundle["data_quality"]). In that case this function
    returns an empty list rather than displaying a fabricated ranking of
    factors that have no actual effect on the prediction.
    """
    global_importance = bundle["top_feature_importance"]
    if not global_importance or all(imp <= 1e-9 for _, imp in global_importance):
        return []
    factors = []
    seen_labels = set()
    for feat_name, importance in global_importance:
        if importance <= 1e-9:
            continue
        clean_name = feat_name.replace("num__", "").replace("cat__", "")
        label = _display_label(clean_name)
        if label in seen_labels:
            continue  # multiple one-hot dummy columns (e.g. two content_type_* levels)
            # can map to the same display label with an identical row-specific
            # description - skip repeats rather than show the same factor twice.
        seen_labels.add(label)
        weight = round(float(importance) * 100, 1)
        factors.append({
            "feature": label,
            "importance": weight,
            "description": _describe_factor(clean_name, raw_row, engineered_row),
        })
        if len(factors) >= top_n:
            break
    return factors


def _recommendations(bundle, raw: dict, eng: pd.DataFrame, performance_score: float) -> list:
    data_quality = bundle.get("data_quality", {})
    if not data_quality.get("signal_detected", True):
        # Honest mode: the training data showed no relationship between any
        # feature and any outcome, so per-input recommendations would be
        # fabricated. Say so plainly instead of inventing generic-sounding
        # advice dressed up as model-driven insight.
        return [
            "This model's training data (see README) showed no measurable relationship between "
            "any input and post performance, so we can't responsibly tell you which specific "
            "changes would help - doing so would be a guess dressed up as an insight.",
            "The score and forecasts above are close to the dataset average for every input, by design.",
            "If you're testing this app: try changing followers, hashtags, or posting hour dramatically "
            "and notice the score barely moves - that's the honest behavior of a model with no signal "
            "to learn from, not a hidden feature.",
        ]

    # Grounded in the actual encoded relationships this model was trained on
    # (see ml/src/generate_dataset.py) - not arbitrary advice.
    recs = []
    if raw.get("historical_engagement_rate", 0) < 3:
        recs.append("Historical engagement rate is on the low side - it's one of the strongest "
                     "predictors in this model, so building engagement before scaling up posting "
                     "volume will likely move your score more than any single-post change.")
    hour = raw.get("posting_hour", 12)
    if not (17 <= hour <= 21):
        recs.append("Posting between 6-9 PM shows a measurable lift in this model's training data - "
                     f"you selected {hour}:00.")
    hashtags = raw.get("hashtags", 0)
    if hashtags > 10:
        recs.append(f"You're using {hashtags} hashtags - beyond ~8-10, additional hashtags show "
                     "diminishing or slightly negative returns in this model. Consider trimming.")
    if not raw.get("has_call_to_action"):
        recs.append("Adding a call-to-action (e.g. \"comment below\", \"save this\") is associated "
                     "with higher engagement in this model.")
    desc_len = raw.get("description_length", 0)
    if desc_len < 60 or desc_len > 220:
        recs.append("Caption length outside roughly 90-160 characters tends to underperform the "
                     f"sweet spot in this model - yours is {desc_len} characters.")
    if not recs:
        recs.append("This content profile looks solid across the factors this model weighs most - "
                     "no major red flags identified.")
    return recs[:5]


def predict_one(payload: dict) -> dict:
    bundle = load_bundle()
    preprocessor = bundle["preprocessor"]
    data_quality = bundle.get("data_quality", {})

    raw_df = pd.DataFrame([payload])
    eng_df = add_engineered_features(raw_df)
    X = eng_df[ALL_FEATURES]
    Xt = preprocessor.transform(X)

    # Views (trained on log1p scale)
    log_views_pred = bundle["views_model"].predict(Xt)[0]
    views_pred = float(np.expm1(log_views_pred))
    views_pred = max(views_pred, 0.0)

    # Engagement rate (%)
    engagement_pred = float(bundle["engagement_model"].predict(Xt)[0])
    engagement_pred = float(np.clip(engagement_pred, 0, 100))

    # Category + probability.
    # IMPORTANT: predict_proba() columns follow model.classes_ (alphabetical
    # by default) - NOT the human-readable ["Low","Medium","High"] severity
    # order. Always zip against model.classes_, never a hand-written list.
    category_model = bundle["category_model"]
    category_pred = category_model.predict(Xt)[0]
    proba = category_model.predict_proba(Xt)[0]
    model_classes = list(category_model.classes_)
    proba_map_raw = {cls: float(p) for cls, p in zip(model_classes, proba)}
    labels = bundle["category_labels"]  # ["Low", "Medium", "High"] - display order
    proba_map = {label: round(proba_map_raw.get(label, 0.0), 4) for label in labels}
    confidence = float(max(proba))

    # Composite 0-100 performance score, consistent with how it was derived
    # at training time (percentile blend of views + engagement), approximated
    # here via the classifier's class probabilities weighted toward the
    # predicted class's typical score band (documented approximation).
    band_center = {"Low": 22.0, "Medium": 54.0, "High": 88.0}
    performance_score = sum(proba_map[l] * band_center[l] for l in labels)
    performance_score = round(float(np.clip(performance_score, 0, 100)), 1)

    display_category = (
        "Excellent" if performance_score >= 85 else
        "Good" if performance_score >= 70 else
        "Moderate" if performance_score >= 40 else
        "Low"
    )

    important_factors = _local_important_factors(bundle, payload, eng_df)
    recommendations = _recommendations(bundle, payload, eng_df, performance_score)

    return {
        "performance_score": performance_score,
        "performance_category": display_category,
        "model_category_prediction": str(category_pred),
        "category_probabilities": proba_map,
        "confidence": round(confidence, 4),
        "expected_views": round(views_pred),
        "expected_engagement_rate": round(engagement_pred, 2),
        "important_factors": important_factors,
        "recommendations": recommendations,
        "data_quality_notice": data_quality.get("notice"),
        "signal_detected": data_quality.get("signal_detected", True),
    }


if __name__ == "__main__":
    sample = {
        "content_type": "reel",
        "creator_category": "Technology",
        "account_type": "creator",
        "has_call_to_action": 1,
        "description_length": 120,
        "hashtags": 8,
        "followers": 25000,
        "account_age_months": 6.0,
        "historical_avg_views": 5000,
        "historical_engagement_rate": 4.2,
        "posting_hour": 19,
        "day_of_week": "Saturday",
    }
    import json
    print(json.dumps(predict_one(sample), indent=2))
