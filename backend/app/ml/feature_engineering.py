"""
feature_engineering.py

Derived features, computed identically at train time and inference time.
Importing this module in both ml/src/train.py and backend/app/ml/*
guarantees train/serve consistency (rule #5 in project engineering rules).

SCHEMA VERSION 2 (Instagram Kaggle dataset). Changed from the original
synthetic, multi-platform schema because the real dataset doesn't support
some of those fields and does support some new ones - see
ml/src/load_instagram_dataset.py for the full rationale:
  - REMOVED: platform (single-platform dataset), title_length /
    title_length_category (no title field distinct from caption),
    video_duration (not present for any media type), mentions (not present),
    content_complexity (was defined from video_duration + description_length;
    without video_duration it would just duplicate description_length, so
    it's dropped rather than kept as a redundant signal).
  - ADDED: account_type (brand/creator), has_call_to_action.
  - CHANGED: description_length_category now uses quantile-based bins
    (qcut) instead of fixed absolute-length thresholds, because Instagram
    captions in this dataset cluster tightly (70-166 chars) - the original
    fixed bins tuned for longer-form YouTube descriptions would have put
    almost every row in a single bucket.
"""
import numpy as np
import pandas as pd


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- description length category: quantile-based (adapts to the actual
    # distribution instead of hardcoded absolute thresholds) ---
    try:
        df["description_length_category"] = pd.qcut(
            df["description_length"], q=4, labels=["short", "medium", "long", "very_long"], duplicates="drop"
        ).astype(str)
    except ValueError:
        # fallback for degenerate/tiny inputs (e.g. a single inference row)
        df["description_length_category"] = "medium"

    # --- posting time ---
    df["posting_hour_category"] = pd.cut(
        df["posting_hour"], bins=[-1, 5, 11, 17, 21, 24],
        labels=["late_night", "morning", "afternoon", "evening", "night"]
    ).astype(str)

    df["is_weekend"] = df["day_of_week"].isin(["Saturday", "Sunday"]).astype(int)

    # --- hashtag density (per 100 chars of caption, guards div-by-zero) ---
    df["hashtag_density"] = df["hashtags"] / (df["description_length"].clip(lower=1) / 100)

    # --- historical engagement score: blends historical views + engagement rate ---
    hist_views = df["historical_avg_views"].fillna(0).clip(lower=0)
    df["historical_engagement_score"] = (
        np.log1p(hist_views) * (df["historical_engagement_rate"].fillna(0) / 10)
    )

    # --- creator experience score: account age combined with follower scale ---
    account_age = df["account_age_months"].fillna(df["account_age_months"].median())
    df["creator_experience_score"] = np.log1p(account_age) * np.log1p(df["followers"])

    # --- follower-normalized historical performance (per-follower reach efficiency) ---
    df["follower_normalized_performance"] = df["historical_avg_views"].fillna(0) / df["followers"].clip(lower=1)

    return df


NUMERIC_FEATURES = [
    "description_length", "hashtags", "has_call_to_action", "followers", "account_age_months",
    "historical_avg_views", "historical_engagement_rate", "posting_hour", "is_weekend",
    "hashtag_density", "historical_engagement_score", "creator_experience_score",
    "follower_normalized_performance",
]

CATEGORICAL_FEATURES = [
    "content_type", "creator_category", "account_type", "day_of_week",
    "description_length_category", "posting_hour_category",
]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
