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

IMPORTANT: the bundled models were trained on the synthetic signal-bearing
dataset (see ml/src/generate_dataset.py) and surface bundle["data_quality"]
(signal_detected) in every response so the app stays honest about how much
signal the underlying data actually contains. When a meaningful signal exists,
this module generates rich, input-specific recommendations for growing views;
if no signal is detected, the "important factors" and recommendations sections
are adjusted accordingly rather than inventing false confidence.

This module has no FastAPI/Pydantic dependency so it can be unit tested or
reused from a notebook/CLI directly.
"""
from pathlib import Path
import os
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
    # Deployment-friendly bundle resolution. The module lives in one of two
    # repo locations: ml/src/ (canonical training tree) or backend/app/ml/
    # (self-contained copy shipped with the API). From either one, walk up to
    # the repo root and look in the standard bundle locations. Candidates:
    #   1. MODEL_BUNDLE_PATH env var (explicit override)
    #   2. <repo>/backend/models/... (shipped with the API)
    #   3. <repo>/ml/models/...      (local training output)
    here = Path(__file__).resolve().parent
    repo_candidates = []
    if here.name == "src" and here.parent.name == "ml":
        repo_root = here.parent.parent          # ml/src -> repo root
    elif here.name == "ml" and here.parent.name == "app":
        repo_root = here.parent.parent.parent   # backend/app/ml -> repo root
    else:
        repo_root = here.parent.parent          # fallback
    repo_candidates = [
        repo_root / "backend" / "models" / "content_performance_bundle.joblib",
        repo_root / "ml" / "models" / "content_performance_bundle.joblib",
    ]
    candidates = [
        Path(os.getenv("MODEL_BUNDLE_PATH", "")).expanduser() if os.getenv("MODEL_BUNDLE_PATH") else None,
    ] + repo_candidates
    for c in candidates:
        if c is not None and c.exists():
            return c
    raise FileNotFoundError(
        "content_performance_bundle.joblib not found. Set MODEL_BUNDLE_PATH or run "
        "`python ml/src/train.py` first."
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


def _infer_views(bundle, payload: dict) -> float:
    """Run the views model on a payload dict and return the predicted views.

    Extracted so the what-if suggestion engine can re-run the model on small
    single-variable mutations of the user's input and report the real predicted
    change in views - i.e. truly model-driven suggestions rather than hand-
    written rules.
    """
    preprocessor = bundle["preprocessor"]
    eng = add_engineered_features(pd.DataFrame([payload]))
    Xt = preprocessor.transform(eng[ALL_FEATURES])
    log_views = bundle["views_model"].predict(Xt)[0]
    return max(float(np.expm1(log_views)), 0.0)


def _fmt_views(n: float) -> str:
    """Compact thousands formatting for suggestion deltas, e.g. 12453 -> '12.5k'."""
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return f"{int(round(n))}"


def _recommendations(bundle, raw: dict, eng: pd.DataFrame, performance_score: float,
                     expected_views: float = None, expected_engagement_rate: float = None,
                     important_factors: list = None) -> list:
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

    # ------------------------------------------------------------------
    # MODEL-DRIVEN what-if recommendations.
    # Each lever re-runs the *views model* on a single-variable mutation of
    # the user's input, so every suggestion is backed by the model's own
    # predicted change in views, sorted by real impact. No hand-written
    # "best practice" that the model doesn't actually reward is reported.
    # ------------------------------------------------------------------
    base_views = _infer_views(bundle, raw)
    levers: list = []

    def record(label: str, modified: dict, summary: str):
        if modified == raw:
            return
        delta = _infer_views(bundle, modified) - base_views
        if delta <= 0:
            return  # only surface changes the model says actually help
        levers.append({
            "delta": delta,
            "text": f"{summary} Model estimate: ~{_fmt_views(delta)} more views.",
        })

    content_type = str(raw.get("content_type", ""))
    hashtags = int(raw.get("hashtags", 0))
    cta = bool(raw.get("has_call_to_action"))
    desc_len = int(raw.get("description_length", 0))
    hour = int(raw.get("posting_hour", 12))

    # 1. Content format: reel is the discovery-optimised baseline for this model.
    if content_type != "reel":
        trial = dict(raw); trial["content_type"] = "reel"
        record("Format -> reel", trial,
               f"Post this as a reel instead of {content_type} - reels are the format this model associates "
               f"with the widest non-follower reach.")

    # 2. Hashtag count: nudge toward the model's sweet spot (~8).
    target_hashtags = 8 if hashtags < 8 else (6 if hashtags > 10 else hashtags)
    if target_hashtags != hashtags:
        trial = dict(raw); trial["hashtags"] = target_hashtags
        record("Hashtags", trial,
               f"{'Raise' if target_hashtags > hashtags else 'Trim'} hashtags from {hashtags} to {target_hashtags} "
               f"- this model links that range to better discoverability.")

    # 3. Call-to-action.
    if not cta:
        trial = dict(raw); trial["has_call_to_action"] = 1
        record("Add a CTA", trial,
               'Add an explicit call-to-action ("Comment below", "Save this", "Share") - the model associates '
               'a CTA with higher reach-driving engagement.')

    # 4. Caption length: nudge toward ~140 chars.
    target_len = desc_len
    if desc_len > 0 and desc_len < 90:
        target_len = 140
    elif desc_len > 200:
        target_len = 140
    if target_len != desc_len:
        trial = dict(raw); trial["description_length"] = target_len
        record("Caption length", trial,
               f"{'Lengthen' if target_len > desc_len else 'Tighten'} the caption from {desc_len} to ~{target_len} "
               f"characters - the length this model favors for holding attention.")

    # 5. Posting hour: toward the model's active evening window.
    if not (18 <= hour <= 21):
        target_hour = 19
        if target_hour != hour:
            trial = dict(raw); trial["posting_hour"] = target_hour
            record("Posting time", trial,
                   f"Post at {target_hour}:00 instead of {hour}:00 - this model's data shows the evening window "
                   f"drives more initial reach.")

    if not levers:
        # Nothing the user can tweak moved predicted views up - say so honestly
        # rather than inventing numbered advice the model doesn't back.
        engagement = round(float(expected_engagement_rate or raw.get("historical_engagement_rate", 0) or 0), 2)
        if engagement < 3:
            return [
                f"Your post looks well set up - the model predicts about {_fmt_views(base_views)} views with it "
                f"as-is, and none of the usual tweaks (format, caption, hashtags, posting time) would raise that "
                "prediction. Most content reaches its audience through one thing: a healthy engagement rate.",
                f"Right now that rate ({engagement}%) is on the low side, and it's the single biggest factor the "
                "model weighs. Focus on small, steady wins over time - a clear niche, replying to every comment, "
                "and ending posts with a question - because every bit of engagement predicts more reach.",
            ]
        return [
            f"Your post is already well set up - the model predicts about {_fmt_views(base_views)} views with it "
            "as-is, and changing the format, caption, hashtags, or posting time wouldn't improve that prediction.",
            "There's no single edit left to squeeze out more views here. If you want to push higher, focus on "
            "growing your audience's engagement (regular replies and questions in posts) - it's what the model "
            "weighs most heavily.",
        ]

    levers.sort(key=lambda l: -l["delta"])

    recs = [f"Predicted views now: ~{_fmt_views(base_views)}. Biggest wins for this post, ranked by the model:"]
    for lev in levers[:5]:
        recs.append(lev["text"])

    # Add one concise context note grounded in the engagement score if it's a
    # real weak spot, since no content tweak can instantly fix historical data.
    engagement = round(float(expected_engagement_rate or raw.get("historical_engagement_rate", 0) or 0), 2)
    if engagement < 3:
        recs.append(f"Your historical engagement rate ({engagement}%) is low - the model weights it heavily, so "
                    "raising it over time (reply to every comment, end posts with a question) will compound the "
                    "content tweaks above.")
    elif engagement >= 7:
        recs.append(f"Strong engagement base ({engagement}%) - ride the tweaks above using the topics/formats that "
                    "already draw the most comments and saves.")

    return recs[:6]


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
    recommendations = _recommendations(
        bundle, payload, eng_df, performance_score,
        expected_views=views_pred, expected_engagement_rate=engagement_pred,
        important_factors=important_factors,
    )

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
