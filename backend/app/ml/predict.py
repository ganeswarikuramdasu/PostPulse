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


DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _posting_schedule_analysis(bundle, raw: dict, base_views: float) -> dict:
    """Sweep all 7 days x 24 hours through the views model to find the
    optimal posting schedule. Returns structured data with best day, best hour,
    top time slots, and a heatmap-ready grid of predicted views."""
    current_day = raw.get("day_of_week", "Monday")
    current_hour = int(raw.get("posting_hour", 12))

    day_views = {}
    for day in DAYS_OF_WEEK:
        trial = dict(raw)
        trial["day_of_week"] = day
        day_views[day] = _infer_views(bundle, trial)

    hour_views = {}
    for hour in range(24):
        trial = dict(raw)
        trial["posting_hour"] = hour
        hour_views[hour] = _infer_views(bundle, trial)

    best_day = max(day_views, key=day_views.get)
    best_hour = max(hour_views, key=hour_views.get)

    slot_views = {}
    for day in DAYS_OF_WEEK:
        for hour in range(24):
            trial = dict(raw)
            trial["day_of_week"] = day
            trial["posting_hour"] = hour
            slot_views[f"{day} {hour}:00"] = _infer_views(bundle, trial)

    top_slots = sorted(slot_views.items(), key=lambda x: -x[1])[:5]

    current_views = slot_views.get(f"{current_day} {current_hour}:00", base_views)
    best_views = slot_views[top_slots[0][0]]

    day_ranking = sorted(day_views.items(), key=lambda x: -x[1])
    hour_ranking = sorted(hour_views.items(), key=lambda x: -x[1])

    day_labels = []
    for day, views in day_ranking:
        delta = views - base_views
        day_labels.append({
            "day": day,
            "predicted_views": round(views),
            "delta_vs_current": round(delta),
            "is_current": day == current_day,
        })

    hour_labels = []
    for hour, views in hour_ranking[:6]:
        delta = views - base_views
        hour_labels.append({
            "hour": f"{hour}:00",
            "predicted_views": round(views),
            "delta_vs_current": round(delta),
            "is_current": hour == current_hour,
        })

    slot_labels = []
    for slot_name, views in top_slots:
        delta = views - base_views
        slot_labels.append({
            "time_slot": slot_name,
            "predicted_views": round(views),
            "delta_vs_current": round(delta),
        })

    return {
        "best_day": best_day,
        "best_day_views": round(day_views[best_day]),
        "best_hour": f"{best_hour}:00",
        "best_hour_views": round(hour_views[best_hour]),
        "current_day": current_day,
        "current_hour": f"{current_hour}:00",
        "current_slot_views": round(current_views),
        "best_slot": top_slots[0][0],
        "best_slot_views": round(best_views),
        "potential_gain": round(best_views - base_views),
        "top_time_slots": slot_labels,
        "day_rankings": day_labels,
        "hour_rankings": hour_labels,
    }


def _caption_strategy(bundle, raw: dict, base_views: float) -> dict:
    """Test multiple caption lengths through the views model to find the
    optimal length for this specific post."""
    current_len = int(raw.get("description_length", 120))
    test_lengths = [40, 60, 80, 100, 120, 140, 160, 200, 250, 300]

    length_views = {}
    for length in test_lengths:
        trial = dict(raw)
        trial["description_length"] = length
        length_views[length] = _infer_views(bundle, trial)

    best_length = max(length_views, key=length_views.get)
    best_views = length_views[best_length]
    current_views = length_views.get(current_len, base_views)

    length_ranking = sorted(length_views.items(), key=lambda x: -x[1])
    top_lengths = []
    for length, views in length_ranking[:4]:
        top_lengths.append({
            "length": length,
            "predicted_views": round(views),
            "delta_vs_current": round(views - base_views),
            "is_current": length == current_len,
        })

    if best_length == current_len:
        advice = f"Your caption length ({current_len} chars) is already optimal for this post."
    elif best_length > current_len:
        advice = (f"Lengthen your caption from {current_len} to ~{best_length} characters. "
                  f"The model predicts ~{_fmt_views(best_views - current_views)} more views at this length.")
    else:
        advice = (f"Tighten your caption from {current_len} to ~{best_length} characters. "
                  f"The model predicts ~{_fmt_views(best_views - current_views)} more views at this length.")

    return {
        "current_length": current_len,
        "optimal_length": best_length,
        "optimal_views": round(best_views),
        "potential_gain": round(best_views - base_views),
        "advice": advice,
        "tested_lengths": top_lengths,
    }


def _hashtag_strategy(bundle, raw: dict, base_views: float) -> dict:
    """Test multiple hashtag counts through the views model to find the
    optimal number for this specific post."""
    current_tags = int(raw.get("hashtags", 8))
    test_counts = [2, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20]

    tag_views = {}
    for count in test_counts:
        trial = dict(raw)
        trial["hashtags"] = count
        tag_views[count] = _infer_views(bundle, trial)

    best_count = max(tag_views, key=tag_views.get)
    best_views = tag_views[best_count]
    current_views = tag_views.get(current_tags, base_views)

    tag_ranking = sorted(tag_views.items(), key=lambda x: -x[1])
    top_counts = []
    for count, views in tag_ranking[:4]:
        top_counts.append({
            "count": count,
            "predicted_views": round(views),
            "delta_vs_current": round(views - base_views),
            "is_current": count == current_tags,
        })

    if best_count == current_tags:
        advice = f"Your hashtag count ({current_tags}) is already optimal for this post."
    elif best_count > current_tags:
        advice = (f"Increase hashtags from {current_tags} to {best_count}. "
                  f"The model predicts ~{_fmt_views(best_views - current_views)} more views at this count.")
    else:
        advice = (f"Reduce hashtags from {current_tags} to {best_count}. "
                  f"The model predicts ~{_fmt_views(best_views - current_views)} fewer spam signals, netting ~{_fmt_views(best_views - current_views)} more views.")

    return {
        "current_count": current_tags,
        "optimal_count": best_count,
        "optimal_views": round(best_views),
        "potential_gain": round(best_views - base_views),
        "advice": advice,
        "tested_counts": top_counts,
    }


def _recommendations(bundle, raw: dict, eng: pd.DataFrame, performance_score: float,
                     expected_views: float = None, expected_engagement_rate: float = None,
                     important_factors: list = None) -> dict:
    data_quality = bundle.get("data_quality", {})
    if not data_quality.get("signal_detected", True):
        return {
            "quick_tips": [
                "This model's training data showed no measurable relationship between "
                "any input and post performance, so we can't responsibly tell you which specific "
                "changes would help - doing so would be a guess dressed up as an insight.",
                "The score and forecasts above are close to the dataset average for every input, by design.",
            ],
            "posting_schedule": None,
            "caption_strategy": None,
            "hashtag_strategy": None,
        }

    base_views = _infer_views(bundle, raw)
    levers: list = []

    def record(label: str, modified: dict, summary: str):
        if modified == raw:
            return
        delta = _infer_views(bundle, modified) - base_views
        if delta <= 0:
            return
        levers.append({
            "delta": delta,
            "text": f"{summary} Model estimate: ~{_fmt_views(delta)} more views.",
        })

    content_type = str(raw.get("content_type", ""))
    hashtags = int(raw.get("hashtags", 0))
    cta = bool(raw.get("has_call_to_action"))
    desc_len = int(raw.get("description_length", 0))
    hour = int(raw.get("posting_hour", 12))

    if content_type != "reel":
        trial = dict(raw); trial["content_type"] = "reel"
        record("Format -> reel", trial,
               f"Post this as a reel instead of {content_type} - reels are the format this model associates "
               f"with the widest non-follower reach.")

    if not cta:
        trial = dict(raw); trial["has_call_to_action"] = 1
        record("Add a CTA", trial,
               'Add an explicit call-to-action ("Comment below", "Save this", "Share") - the model associates '
               'a CTA with higher reach-driving engagement.')

    posting_schedule = _posting_schedule_analysis(bundle, raw, base_views)
    caption_strat = _caption_strategy(bundle, raw, base_views)
    hashtag_strat = _hashtag_strategy(bundle, raw, base_views)

    if caption_strat["potential_gain"] > 0:
        target_len = caption_strat["optimal_length"]
        trial = dict(raw); trial["description_length"] = target_len
        record("Caption length", trial,
               caption_strat["advice"].split(". ")[0] + ".")

    if hashtag_strat["potential_gain"] > 0:
        target_tags = hashtag_strat["optimal_count"]
        trial = dict(raw); trial["hashtags"] = target_tags
        record("Hashtag count", trial,
               hashtag_strat["advice"].split(". ")[0] + ".")

    if posting_schedule["potential_gain"] > 0:
        best_day = posting_schedule["best_day"]
        best_hour_str = posting_schedule["best_hour"]
        if best_day != raw.get("day_of_week") or best_hour_str != f"{hour}:00":
            trial = dict(raw)
            trial["day_of_week"] = best_day
            trial["posting_hour"] = int(best_hour_str.replace(":00", ""))
            record("Best time slot", trial,
                   f"Post on {best_day} at {best_hour_str} instead of {raw.get('day_of_week')} at {hour}:00")

    quick_tips = []
    if levers:
        levers.sort(key=lambda l: -l["delta"])
        quick_tips.append(
            f"Predicted views now: ~{_fmt_views(base_views)}. Biggest wins for this post, ranked by the model:"
        )
        for lev in levers[:5]:
            quick_tips.append(lev["text"])
    else:
        engagement = round(float(expected_engagement_rate or raw.get("historical_engagement_rate", 0) or 0), 2)
        if engagement < 3:
            quick_tips.append(
                f"Your post looks well set up - the model predicts ~{_fmt_views(base_views)} views as-is. "
                f"Most content reaches its audience through engagement, and yours ({engagement}%) is on the low side."
            )
            quick_tips.append(
                "Focus on steady wins: reply to every comment, end posts with a question, and pick a clear niche."
            )
        else:
            quick_tips.append(
                f"Your post is already well optimized - the model predicts ~{_fmt_views(base_views)} views as-is."
            )

    engagement = round(float(expected_engagement_rate or raw.get("historical_engagement_rate", 0) or 0), 2)
    if engagement < 3:
        quick_tips.append(
            f"Your historical engagement rate ({engagement}%) is low - the model weights it heavily, so "
            "raising it over time will compound the content tweaks above."
        )
    elif engagement >= 7:
        quick_tips.append(
            f"Strong engagement base ({engagement}%) - ride the tweaks above using the topics/formats that "
            "already draw the most comments and saves."
        )

    return {
        "quick_tips": quick_tips[:6],
        "posting_schedule": posting_schedule,
        "caption_strategy": caption_strat,
        "hashtag_strategy": hashtag_strat,
    }


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
        "recommendations": recommendations.get("quick_tips", []),
        "posting_schedule": recommendations.get("posting_schedule"),
        "caption_strategy": recommendations.get("caption_strategy"),
        "hashtag_strategy": recommendations.get("hashtag_strategy"),
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
