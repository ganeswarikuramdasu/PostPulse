"""
load_instagram_dataset.py

Adapts the Kaggle "Instagram Analytics" dataset (uploaded by the user as
Instagram_Analytics.csv) into the schema ml/src/train.py expects.

This REPLACES the synthetic dataset as the training source. Key differences
from the original synthetic generator, and why:

1. LEAKAGE: `traffic_source` describes where a post's reach came from
   (Home Feed, Hashtags, Explore, ...) - that is decided by Instagram's
   ranking/discovery algorithm AFTER publishing, not by the creator before
   publishing. It is excluded as a feature even though it's in the raw file.
   `likes`, `comments`, `shares`, `saves`, `reach`, `impressions`,
   `engagement_rate`, `followers_gained`, `performance_bucket_label` are all
   post-publication OUTCOMES (or derived from outcomes) and are only ever
   used to build TARGETS, never as input features.

2. NOT AVAILABLE in this dataset (dropped from the schema entirely, rather
   than faked): platform (Instagram-only - no cross-platform column), a
   title field distinct from the caption, video duration, @mentions count,
   and true account-creation date.

3. NEWLY AVAILABLE (added to the schema): `account_type` (brand/creator),
   `has_call_to_action`.

4. HISTORICAL FEATURES ARE REAL, NOT SYNTHETIC: this dataset has 20 accounts
   with ~1,500 posts each spread across a year, so `historical_avg_views`
   and `historical_engagement_rate` are computed as an EXPANDING (prior-only)
   average per account, sorted by post datetime - i.e. "this account's
   average performance up to (not including) this post". A post's own
   outcome never leaks into its own historical features. The first post for
   each account has no history (NaN), which the existing median-imputation
   step in preprocessing.py handles the same way it would for a brand-new
   creator in production.

5. ACCOUNT AGE: this dataset has no real account-creation date, only a
   window of observed posts (2024-11-19 to 2025-11-19). `account_age_months`
   is therefore an approximation: months since THIS account's first post
   *in the observed data*, not true account age. This is a documented
   limitation, not a hidden one - see README.

Run: python ml/src/load_instagram_dataset.py
Output: ml/data/content_performance_raw.csv (same filename train.py reads,
so no other pipeline code needs to change paths)
"""
import numpy as np
import pandas as pd
from pathlib import Path

RAW_PATH = str(Path(__file__).resolve().parents[1] / "data" / "Instagram_Analytics.csv")
OUT_PATH = "ml/data/content_performance_raw.csv"


def load_and_adapt() -> pd.DataFrame:
    df = pd.read_csv(RAW_PATH)
    df["post_datetime"] = pd.to_datetime(df["post_datetime"])
    df = df.sort_values(["account_id", "post_datetime"]).reset_index(drop=True)

    # --- leakage-safe historical features: expanding mean of PRIOR posts only ---
    # .shift(1) excludes the current row's own outcome from its own history.
    grp = df.groupby("account_id")
    df["historical_avg_views"] = grp["reach"].transform(lambda s: s.shift(1).expanding().mean())
    df["historical_engagement_rate"] = grp["engagement_rate"].transform(
        lambda s: s.shift(1).expanding().mean()
    ) * 100  # convert fraction -> percentage, consistent with the rest of the project

    # --- account age proxy: months since this account's first post IN THE DATA ---
    first_post = grp["post_datetime"].transform("min")
    df["account_age_months"] = ((df["post_datetime"] - first_post).dt.days / 30.44).round(1)

    # --- rename raw columns to the schema used throughout the project ---
    df = df.rename(columns={
        "media_type": "content_type",
        "content_category": "creator_category",
        "follower_count": "followers",
        "post_hour": "posting_hour",
        "caption_length": "description_length",
        "hashtags_count": "hashtags",
    })

    # --- targets ---
    df["expected_views"] = df["reach"].astype(int)
    df["expected_engagement_rate"] = (df["engagement_rate"] * 100).round(2)

    # Performance score / category derived the SAME WAY as the original
    # synthetic pipeline (percentile blend of views + engagement), for
    # consistency with the rest of the documented scoring system - see
    # README "Performance Score". The dataset's own `performance_bucket_label`
    # is kept as a reference/sanity column but is NOT used as the training
    # target, since we don't know its exact derivation and want one
    # consistent, documented scoring definition across the whole project.
    views_rank = df["expected_views"].rank(pct=True)
    eng_rank = df["expected_engagement_rate"].rank(pct=True)
    composite = 0.55 * views_rank + 0.45 * eng_rank
    df["performance_score"] = (composite * 100).round(1)
    df["performance_category"] = pd.cut(
        df["performance_score"], bins=[-0.1, 39, 69, 100], labels=["Low", "Medium", "High"]
    ).astype(str)
    df["kaggle_performance_bucket_label"] = df["performance_bucket_label"]  # kept for reference only

    keep_cols = [
        "content_type", "creator_category", "account_type", "has_call_to_action",
        "description_length", "hashtags", "followers", "account_age_months",
        "historical_avg_views", "historical_engagement_rate", "posting_hour", "day_of_week",
        "expected_views", "expected_engagement_rate", "performance_score", "performance_category",
        "kaggle_performance_bucket_label",
    ]
    out = df[keep_cols].copy()
    return out


if __name__ == "__main__":
    out = load_and_adapt()
    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out)} rows to {OUT_PATH}")
    print(f"Rows with no prior history (first post per account, NaN historicals): "
          f"{out['historical_avg_views'].isna().sum()}")
    print(out.head())
