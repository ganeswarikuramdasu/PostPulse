"""
generate_dataset.py

Produces a dataset matching the CURRENT feature schema (ml/src/feature_engineering.py,
v2 - content_type/creator_category/account_type/has_call_to_action, no platform/
title_length/video_duration/mentions) with REAL, documented relationships between
inputs and outcomes - unlike the real Kaggle dataset this project also supports
(ml/src/load_instagram_dataset.py), which was validated and found to have no
learnable signal (see README "Key Finding").

This is the DEFAULT training data source for PostPulse because the product needs
to actually predict something. It is honestly synthetic - documented as such,
not passed off as real user data - built the same way this project's earlier
synthetic generator was: a deterministic generative model encoding widely-known,
publicly-documented social-media patterns, with injected noise so it isn't
trivially perfect either.

Run: python ml/src/generate_dataset.py
Output: ml/data/content_performance_raw.csv
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
N = 15000

CONTENT_TYPES = ["reel", "image", "carousel"]
CREATOR_CATEGORIES = ["Technology", "Fitness", "Beauty", "Music", "Photography",
                       "Food", "Lifestyle", "Travel", "Fashion", "Comedy"]
ACCOUNT_TYPES = ["brand", "creator"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

CONTENT_TYPE_MULT = {"reel": 1.35, "image": 0.85, "carousel": 1.05}
CATEGORY_MULT = {
    "Technology": 0.95, "Fitness": 1.05, "Beauty": 1.15, "Music": 1.10,
    "Photography": 1.0, "Food": 1.20, "Lifestyle": 1.0, "Travel": 1.08,
    "Fashion": 1.12, "Comedy": 1.25,
}


def generate() -> pd.DataFrame:
    n = N
    content_type = RNG.choice(CONTENT_TYPES, n)
    creator_category = RNG.choice(CREATOR_CATEGORIES, n)
    account_type = RNG.choice(ACCOUNT_TYPES, n, p=[0.4, 0.6])
    has_call_to_action = RNG.binomial(1, 0.45, n)
    day_of_week = RNG.choice(DAYS, n)

    description_length = np.clip(RNG.normal(120, 45, n), 10, 400).round().astype(int)
    hashtags = np.clip(RNG.poisson(6, n), 0, 30)

    # followers on a log scale - most accounts are small, a few are huge
    followers = np.clip(RNG.lognormal(mean=8.8, sigma=1.6, size=n), 200, 5_000_000).round().astype(int)
    account_age_months = np.clip(RNG.normal(14, 9, n), 0, 96).round(1)

    # latent "creator skill" factor - unobserved content quality that drives
    # both historical performance AND (partially) future performance, same as
    # a real creator's skill would carry over post to post
    creator_skill = RNG.normal(0, 1, n)

    historical_avg_views = np.clip(
        followers * RNG.uniform(0.03, 0.30, n) * np.exp(0.4 * creator_skill), 30, None
    ).round().astype(int)
    historical_engagement_rate = np.clip(
        RNG.normal(3.8, 1.8, n) + 0.9 * creator_skill, 0.1, 20
    ).round(2)

    posting_hour = RNG.integers(0, 24, n)

    df = pd.DataFrame({
        "content_type": content_type,
        "creator_category": creator_category,
        "account_type": account_type,
        "has_call_to_action": has_call_to_action,
        "description_length": description_length,
        "hashtags": hashtags,
        "followers": followers,
        "account_age_months": account_age_months,
        "historical_avg_views": historical_avg_views,
        "historical_engagement_rate": historical_engagement_rate,
        "posting_hour": posting_hour,
        "day_of_week": day_of_week,
        "_creator_skill": creator_skill,
    })
    return df


def build_targets(df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)

    content_mult = df["content_type"].map(CONTENT_TYPE_MULT).to_numpy()
    category_mult = df["creator_category"].map(CATEGORY_MULT).to_numpy()
    account_mult = np.where(df["account_type"].to_numpy() == "creator", 1.08, 1.0)
    cta_mult = np.where(df["has_call_to_action"].to_numpy() == 1, 1.06, 1.0)

    # posting hour: evening (18-21) bump, late-night dip
    hour = df["posting_hour"].to_numpy()
    hour_effect = (
        1.0
        + 0.25 * np.exp(-((hour - 19) ** 2) / (2 * 3.0 ** 2))
        - 0.12 * ((hour >= 1) & (hour <= 5))
    )

    weekend = df["day_of_week"].isin(["Saturday", "Sunday"]).to_numpy()
    day_effect = np.where(weekend, 1.06, 1.0)

    # caption length: sweet spot ~90-160 chars (real Instagram norms), penalize extremes
    desc_len = df["description_length"].to_numpy()
    desc_effect = 1.0 + 0.12 * np.exp(-((desc_len - 125) ** 2) / (2 * 45.0 ** 2))

    # hashtags: mild positive up to ~8, then diminishing/negative (spammy)
    hashtags = df["hashtags"].to_numpy()
    hashtag_effect = 1.0 + 0.018 * np.minimum(hashtags, 8) - 0.012 * np.maximum(hashtags - 8, 0)

    skill = df["_creator_skill"].to_numpy()
    follower_term = np.log1p(df["followers"].to_numpy()) / np.log1p(5_000_000)
    hist_views_term = np.log1p(df["historical_avg_views"].to_numpy()) / np.log1p(df["historical_avg_views"].max())
    hist_engagement_term = df["historical_engagement_rate"].to_numpy() / 20.0
    experience_term = np.log1p(df["account_age_months"].to_numpy()) / np.log1p(96)

    reach_signal = (
        0.38 * follower_term + 0.36 * hist_views_term + 0.14 * hist_engagement_term
        + 0.07 * experience_term + 0.10 * np.tanh(skill)
    )

    noise_views = RNG.normal(0, 0.30, len(df))
    base_views = df["historical_avg_views"].to_numpy() * 0.5 + df["followers"].to_numpy() * 0.025 + 250
    expected_views = base_views * content_mult * category_mult * account_mult * cta_mult \
        * hour_effect * day_effect * desc_effect * hashtag_effect * (1 + reach_signal) * np.exp(noise_views)
    expected_views = np.clip(expected_views, 10, None).round().astype(int)

    noise_eng = RNG.normal(0, 0.85, n)
    expected_engagement = (
        0.55 * df["historical_engagement_rate"].to_numpy()
        + 1.0 * np.tanh(skill) + 1.6
        + 0.5 * (hour_effect - 1) * 10
        + 0.4 * (cta_mult - 1) * 10
        - 0.06 * np.maximum(hashtags - 10, 0)
        + noise_eng
    )
    expected_engagement = np.clip(expected_engagement, 0.1, 30).round(2)

    views_rank = pd.Series(expected_views).rank(pct=True).to_numpy()
    eng_rank = pd.Series(expected_engagement).rank(pct=True).to_numpy()
    composite = 0.55 * views_rank + 0.45 * eng_rank
    performance_score = np.clip(composite * 100, 0, 100).round(1)

    category = pd.cut(
        performance_score, bins=[-0.1, 39, 69, 100], labels=["Low", "Medium", "High"]
    ).astype(str)

    df = df.drop(columns=["_creator_skill"])
    df["expected_views"] = expected_views
    df["expected_engagement_rate"] = expected_engagement
    df["performance_score"] = performance_score
    df["performance_category"] = category
    return df


def add_missingness_and_dupes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    idx = RNG.choice(df.index, size=int(len(df) * 0.01), replace=False)
    df.loc[idx, "account_age_months"] = np.nan
    dupes = df.sample(n=30, random_state=1)
    df = pd.concat([df, dupes], ignore_index=True)
    return df


if __name__ == "__main__":
    df = generate()
    df = build_targets(df)
    df = add_missingness_and_dupes(df)
    df = df.sample(frac=1, random_state=7).reset_index(drop=True)
    out_path = "ml/data/content_performance_raw.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    print(df.head())
