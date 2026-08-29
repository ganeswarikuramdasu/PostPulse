"""
train.py - Full training pipeline for the Content Performance Predictor.

Targets:
  1. expected_views          (regression, trained on log1p scale - heavy-tailed target)
  2. expected_engagement_rate (regression)
  3. performance_category     (classification: Low / Medium / High)

Run: python ml/src/train.py
Outputs:
  - ml/reports/model_comparison_*.csv   (comparison tables, real metrics)
  - ml/models/*.joblib                  (final serialized bundle)
  - backend/models/*.joblib             (copy consumed by the API)
"""
import time
import json
import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LinearRegression, Ridge, Lasso, LogisticRegression
from sklearn.ensemble import (
    RandomForestRegressor, GradientBoostingRegressor, HistGradientBoostingRegressor,
    RandomForestClassifier, GradientBoostingClassifier,
)
from sklearn.tree import DecisionTreeClassifier
from sklearn.dummy import DummyRegressor, DummyClassifier
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix,
)

from feature_engineering import add_engineered_features, ALL_FEATURES
from preprocessing import build_preprocessor

RANDOM_STATE = 42

print("Loading data...")
df = pd.read_csv("ml/data/content_performance_raw.csv")
df = df.drop_duplicates().reset_index(drop=True)
df = add_engineered_features(df)

X = df[ALL_FEATURES]
y_views = df["expected_views"]
y_engagement = df["expected_engagement_rate"]
y_category = df["performance_category"]

# 60/20/20 train/val/test split (stratified on category so all three targets share splits)
X_train, X_temp, yv_train, yv_temp, ye_train, ye_temp, yc_train, yc_temp = train_test_split(
    X, y_views, y_engagement, y_category, test_size=0.4, random_state=RANDOM_STATE, stratify=y_category
)
X_val, X_test, yv_val, yv_test, ye_val, ye_test, yc_val, yc_test = train_test_split(
    X_temp, yv_temp, ye_temp, yc_temp, test_size=0.5, random_state=RANDOM_STATE, stratify=yc_temp
)

print(f"Train: {len(X_train)}  Val: {len(X_val)}  Test: {len(X_test)}")

# Fit ONE preprocessor on training data; reuse (transform-only) everywhere else.
preprocessor = build_preprocessor()
Xt_train = preprocessor.fit_transform(X_train)
Xt_val = preprocessor.transform(X_val)
Xt_test = preprocessor.transform(X_test)

# combine train+val for the final refit of the chosen model (test set stays untouched until final eval)
Xt_trainval = preprocessor.transform(pd.concat([X_train, X_val]))

results = {"views": [], "engagement": [], "category": []}


def eval_regression(name, model, Xt_tr, y_tr, Xt_v, y_v, log_target=False):
    t0 = time.time()
    model.fit(Xt_tr, np.log1p(y_tr) if log_target else y_tr)
    train_time = time.time() - t0
    pred = model.predict(Xt_v)
    if log_target:
        pred = np.expm1(pred)
    mae = mean_absolute_error(y_v, pred)
    rmse = mean_squared_error(y_v, pred) ** 0.5
    r2 = r2_score(y_v, pred)
    return {"model": name, "MAE": mae, "RMSE": rmse, "R2": r2, "train_time_s": train_time}, model


# ---------------------------------------------------------------------------
# 1. EXPECTED VIEWS (regression, log1p target due to heavy right tail)
# ---------------------------------------------------------------------------
print("\n=== Training: expected_views ===")
views_candidates = {
    "Baseline (mean)": DummyRegressor(strategy="mean"),
    "Linear Regression": LinearRegression(),
    "Ridge": Ridge(alpha=1.0, random_state=RANDOM_STATE),
    "Lasso": Lasso(alpha=0.01, random_state=RANDOM_STATE),
    "Random Forest": RandomForestRegressor(n_estimators=200, max_depth=14, random_state=RANDOM_STATE, n_jobs=-1),
    "Gradient Boosting": GradientBoostingRegressor(random_state=RANDOM_STATE),
    "HistGradientBoosting": HistGradientBoostingRegressor(random_state=RANDOM_STATE),
}
views_fitted = {}
for name, model in views_candidates.items():
    row, fitted = eval_regression(name, model, Xt_train, yv_train, Xt_val, yv_val, log_target=True)
    results["views"].append(row)
    views_fitted[name] = fitted
    print(f"  {name:22s} MAE={row['MAE']:.1f}  RMSE={row['RMSE']:.1f}  R2={row['R2']:.3f}")

# light hyperparameter tuning on the best-looking candidate (HistGBR / RF)
print("  Tuning HistGradientBoosting...")
param_grid = {"max_depth": [None, 8, 14], "learning_rate": [0.05, 0.1], "max_iter": [150, 250]}
gscv = GridSearchCV(HistGradientBoostingRegressor(random_state=RANDOM_STATE), param_grid, cv=3,
                     scoring="neg_mean_absolute_error", n_jobs=-1)
gscv.fit(Xt_train, np.log1p(yv_train))
best_params_views = gscv.best_params_
pred = np.expm1(gscv.predict(Xt_val))
tuned_row = {
    "model": "HistGradientBoosting (tuned)",
    "MAE": mean_absolute_error(yv_val, pred),
    "RMSE": mean_squared_error(yv_val, pred) ** 0.5,
    "R2": r2_score(yv_val, pred),
    "train_time_s": None,
}
results["views"].append(tuned_row)
print(f"  Tuned params: {best_params_views}")
print(f"  {tuned_row['model']:28s} MAE={tuned_row['MAE']:.1f}  RMSE={tuned_row['RMSE']:.1f}  R2={tuned_row['R2']:.3f}")

views_comparison = pd.DataFrame(results["views"]).sort_values("MAE")
views_comparison.to_csv("ml/reports/model_comparison_views.csv", index=False)
# Linear/Ridge/Lasso are excluded from selection on principle, not just by losing on MAE:
# with a log1p target and one-hot encoded categoricals, unconstrained linear models can
# extrapolate to astronomical predictions (expm1 of a large linear output) on validation
# rows that sit outside the training distribution. Tree ensembles don't extrapolate this
# way (their output is bounded by leaf values seen in training), so this is a genuine
# argument for tree-based models on this problem, not just a metric that happened to win.
UNSTABLE_LINEAR_MODELS = {"Linear Regression", "Ridge", "Lasso"}
sane_views = views_comparison[~views_comparison["model"].isin(UNSTABLE_LINEAR_MODELS)]
best_views_model_name = sane_views.iloc[0]["model"]
baseline_views_mae = views_comparison[views_comparison["model"] == "Baseline (mean)"]["MAE"].iloc[0]
best_views_mae = sane_views.iloc[0]["MAE"]
if best_views_model_name != "Baseline (mean)" and best_views_mae > baseline_views_mae * 0.99:
    # "Winning" by less than 1% over the trivial baseline is noise, not signal -
    # don't ship a falsely-complex model when the mean predictor is just as good.
    print(f"  NOTE: {best_views_model_name} beat baseline MAE by <1% on validation "
          f"({best_views_mae:.1f} vs {baseline_views_mae:.1f}) - treating as no real signal, using baseline.")
    best_views_model_name = "Baseline (mean)"
print(f"  -> Best for views: {best_views_model_name} (Linear/Ridge/Lasso excluded - see comments)")

# refit the ACTUAL best-performing candidate (by validation MAE) on train+val, then
# evaluate once on the held-out test set.
VIEWS_MODEL_FACTORY = {
    "Baseline (mean)": lambda: DummyRegressor(strategy="mean"),
    "Random Forest": lambda: RandomForestRegressor(n_estimators=200, max_depth=14, random_state=RANDOM_STATE, n_jobs=-1),
    "Gradient Boosting": lambda: GradientBoostingRegressor(random_state=RANDOM_STATE),
    "HistGradientBoosting": lambda: HistGradientBoostingRegressor(random_state=RANDOM_STATE),
    "HistGradientBoosting (tuned)": lambda: HistGradientBoostingRegressor(random_state=RANDOM_STATE, **best_params_views),
}
if best_views_model_name == "Baseline (mean)":
    print("  WARNING: no model beat the baseline mean predictor for views either - see note above.")
final_views_model = VIEWS_MODEL_FACTORY[best_views_model_name]()
final_views_model.fit(Xt_trainval, np.log1p(pd.concat([yv_train, yv_val])))
pred_test = np.expm1(final_views_model.predict(Xt_test))
views_test_metrics = {
    "MAE": float(mean_absolute_error(yv_test, pred_test)),
    "RMSE": float(mean_squared_error(yv_test, pred_test) ** 0.5),
    "R2": float(r2_score(yv_test, pred_test)),
}
print(f"  Held-out TEST metrics (views): {views_test_metrics}")

# ---------------------------------------------------------------------------
# 2. EXPECTED ENGAGEMENT RATE (regression)
# ---------------------------------------------------------------------------
print("\n=== Training: expected_engagement_rate ===")
engagement_candidates = {
    "Baseline (mean)": DummyRegressor(strategy="mean"),
    "Linear Regression": LinearRegression(),
    "Ridge": Ridge(alpha=1.0, random_state=RANDOM_STATE),
    "Random Forest": RandomForestRegressor(n_estimators=200, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1),
    "Gradient Boosting": GradientBoostingRegressor(random_state=RANDOM_STATE),
    "HistGradientBoosting": HistGradientBoostingRegressor(random_state=RANDOM_STATE),
}
for name, model in engagement_candidates.items():
    row, fitted = eval_regression(name, model, Xt_train, ye_train, Xt_val, ye_val, log_target=False)
    results["engagement"].append(row)
    print(f"  {name:22s} MAE={row['MAE']:.2f}  RMSE={row['RMSE']:.2f}  R2={row['R2']:.3f}")

engagement_comparison = pd.DataFrame(results["engagement"]).sort_values("MAE")
engagement_comparison.to_csv("ml/reports/model_comparison_engagement.csv", index=False)
best_engagement_name = engagement_comparison.iloc[0]["model"]
print(f"  -> Best for engagement: {best_engagement_name}")

ENGAGEMENT_MODEL_FACTORY = {
    "Baseline (mean)": lambda: DummyRegressor(strategy="mean"),
    "Linear Regression": lambda: LinearRegression(),
    "Ridge": lambda: Ridge(alpha=1.0, random_state=RANDOM_STATE),
    "Random Forest": lambda: RandomForestRegressor(n_estimators=200, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1),
    "Gradient Boosting": lambda: GradientBoostingRegressor(random_state=RANDOM_STATE),
    "HistGradientBoosting": lambda: HistGradientBoostingRegressor(random_state=RANDOM_STATE),
}
if best_engagement_name == "Baseline (mean)":
    print("  WARNING: no model beat the baseline mean predictor - see ml/reports/ for full comparison. "
          "This means the features have ~no measurable linear/nonlinear relationship with this target "
          "in this dataset. Proceeding with the baseline as the 'final model' so the pipeline still "
          "produces an honest, working artifact rather than a misleadingly complex one.")
final_engagement_model = ENGAGEMENT_MODEL_FACTORY[best_engagement_name]()
final_engagement_model.fit(Xt_trainval, pd.concat([ye_train, ye_val]))
pred_test = final_engagement_model.predict(Xt_test)
engagement_test_metrics = {
    "MAE": float(mean_absolute_error(ye_test, pred_test)),
    "RMSE": float(mean_squared_error(ye_test, pred_test) ** 0.5),
    "R2": float(r2_score(ye_test, pred_test)),
}
print(f"  Held-out TEST metrics (engagement): {engagement_test_metrics}")

# ---------------------------------------------------------------------------
# 3. PERFORMANCE CATEGORY (classification)
# ---------------------------------------------------------------------------
print("\n=== Training: performance_category ===")
class_candidates = {
    "Baseline (prior)": DummyClassifier(strategy="prior"),
    "Logistic Regression": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
    "Decision Tree": DecisionTreeClassifier(max_depth=8, random_state=RANDOM_STATE),
    "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1),
    "Gradient Boosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
}
labels_order = ["Low", "Medium", "High"]
labels_sorted = sorted(labels_order)  # roc_auc_score requires `labels` given in sorted order
for name, model in class_candidates.items():
    t0 = time.time()
    model.fit(Xt_train, yc_train)
    train_time = time.time() - t0
    pred = model.predict(Xt_val)
    proba = model.predict_proba(Xt_val) if hasattr(model, "predict_proba") else None
    row = {
        "model": name,
        "Accuracy": accuracy_score(yc_val, pred),
        "Precision_macro": precision_score(yc_val, pred, average="macro", zero_division=0),
        "Recall_macro": recall_score(yc_val, pred, average="macro", zero_division=0),
        "F1_macro": f1_score(yc_val, pred, average="macro", zero_division=0),
        "ROC_AUC_ovr": roc_auc_score(yc_val, proba, multi_class="ovr", labels=labels_sorted) if proba is not None else None,
        "train_time_s": train_time,
    }
    results["category"].append(row)
    print(f"  {name:26s} Acc={row['Accuracy']:.3f}  F1={row['F1_macro']:.3f}  AUC={row['ROC_AUC_ovr']}")

category_comparison = pd.DataFrame(results["category"]).sort_values("F1_macro", ascending=False)
category_comparison.to_csv("ml/reports/model_comparison_category.csv", index=False)
sane_category = category_comparison[category_comparison["model"] != "Baseline (prior)"]
best_category_name = sane_category.iloc[0]["model"]
baseline_category_auc = category_comparison[category_comparison["model"] == "Baseline (prior)"]["ROC_AUC_ovr"].iloc[0]
best_category_auc = sane_category.iloc[0]["ROC_AUC_ovr"]
if best_category_auc is not None and best_category_auc < 0.6:
    # ROC-AUC below ~0.6 is not meaningfully better than random guessing (0.5) -
    # don't ship a model dressed up as "best" when it isn't actually predictive.
    print(f"  NOTE: best category model ROC-AUC ({best_category_auc:.3f}) is close to random (0.5) - "
          f"treating as no real signal, using baseline (most frequent class).")
    best_category_name = "Baseline (prior)"
print(f"  -> Best for category: {best_category_name}")

CATEGORY_MODEL_FACTORY = {
    "Baseline (prior)": lambda: DummyClassifier(strategy="prior"),
    "Logistic Regression": lambda: LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
    "Decision Tree": lambda: DecisionTreeClassifier(max_depth=8, random_state=RANDOM_STATE),
    "Random Forest": lambda: RandomForestClassifier(n_estimators=300, max_depth=12, random_state=RANDOM_STATE, n_jobs=-1),
    "Gradient Boosting": lambda: GradientBoostingClassifier(random_state=RANDOM_STATE),
}
final_category_model = CATEGORY_MODEL_FACTORY[best_category_name]()
final_category_model.fit(Xt_trainval, pd.concat([yc_train, yc_val]))
pred_test = final_category_model.predict(Xt_test)
proba_test = final_category_model.predict_proba(Xt_test)
cm = confusion_matrix(yc_test, pred_test, labels=labels_order)
category_test_metrics = {
    "Accuracy": float(accuracy_score(yc_test, pred_test)),
    "Precision_macro": float(precision_score(yc_test, pred_test, average="macro", zero_division=0)),
    "Recall_macro": float(recall_score(yc_test, pred_test, average="macro", zero_division=0)),
    "F1_macro": float(f1_score(yc_test, pred_test, average="macro", zero_division=0)),
    "ROC_AUC_ovr": float(roc_auc_score(yc_test, proba_test, multi_class="ovr", labels=labels_sorted)),
    "confusion_matrix": cm.tolist(),
    "labels_order": labels_order,
}
print(f"  Held-out TEST metrics (category): {category_test_metrics}")

# ---------------------------------------------------------------------------
# Feature importance - permutation importance on the held-out test set.
# Chosen over .feature_importances_ because it works identically regardless
# of which model type wins (tree ensemble OR logistic regression), and
# because it reflects impact on genuinely unseen data rather than
# training-time impurity reduction (which can overstate high-cardinality
# features). Used for the /model-info endpoint and per-prediction
# "important factors" explanation.
# ---------------------------------------------------------------------------
from sklearn.inspection import permutation_importance

print("\nComputing permutation importance for the final category model...")
perm = permutation_importance(
    final_category_model, Xt_test, yc_test, n_repeats=8, random_state=RANDOM_STATE, n_jobs=-1
)
feature_names = preprocessor.get_feature_names_out().tolist()
feat_importance = sorted(zip(feature_names, perm.importances_mean), key=lambda x: -x[1])[:15]

# ---------------------------------------------------------------------------
# Data quality check: does ANY feature actually correlate with the targets?
# Saved into the bundle so the API/frontend can surface an honest
# signal-quality notice rather than silently presenting baseline
# predictions as if they were learned ones.
# ---------------------------------------------------------------------------
numeric_check_cols = [c for c in df.select_dtypes(include="number").columns
                       if c not in ("expected_views", "expected_engagement_rate", "performance_score")]
views_corrs = df[numeric_check_cols].corrwith(df["expected_views"]).abs()
engagement_corrs = df[numeric_check_cols].corrwith(df["expected_engagement_rate"]).abs()
max_abs_corr = float(max(views_corrs.max(), engagement_corrs.max()))

views_beat_baseline = views_test_metrics["R2"] > 0.02
engagement_beat_baseline = engagement_test_metrics["R2"] > 0.02
category_best_row = category_comparison[category_comparison["model"] != "Baseline (prior)"] \
    .sort_values("F1_macro", ascending=False).iloc[0]
category_auc = float(category_test_metrics["ROC_AUC_ovr"])

data_quality = {
    "max_abs_feature_target_correlation": round(max_abs_corr, 4),
    "views_model_beats_baseline": bool(views_beat_baseline),
    "engagement_model_beats_baseline": bool(engagement_beat_baseline),
    "category_roc_auc": round(category_auc, 4),
    "signal_detected": bool(views_beat_baseline or engagement_beat_baseline or category_auc > 0.6),
}
data_quality["notice"] = (
    "No measurable relationship was found between any input feature and any prediction target "
    f"in this dataset (max |correlation| = {max_abs_corr:.3f} across all numeric features vs. both "
    f"regression targets; classifier ROC-AUC = {category_auc:.3f}, i.e. indistinguishable from random "
    "guessing). This was verified directly via correlation analysis and a baseline-vs-model comparison "
    "before finalizing this bundle - it is a property of the dataset, not a bug in the pipeline. "
    "Predictions from this model sit close to the population average regardless of input and should "
    "not be treated as reliable. See the README 'Dataset' and 'Limitations' sections."
) if not data_quality["signal_detected"] else None
print(f"\nData quality check: max |correlation| between any feature and any target = {max_abs_corr:.4f}")
print(f"Signal detected: {data_quality['signal_detected']}")

# ---------------------------------------------------------------------------
# Save everything
# ---------------------------------------------------------------------------
bundle = {
    "preprocessor": preprocessor,
    "views_model": final_views_model,
    "views_target_transform": "log1p",
    "engagement_model": final_engagement_model,
    "category_model": final_category_model,
    "category_labels": labels_order,
    "feature_columns": ALL_FEATURES,
    "top_feature_importance": feat_importance,
    "test_metrics": {
        "views": views_test_metrics,
        "engagement": engagement_test_metrics,
        "category": category_test_metrics,
    },
    "best_model_names": {
        "views": best_views_model_name,
        "engagement": best_engagement_name,
        "category": best_category_name,
    },
    "hyperparameters": {
        "views": best_params_views,
    },
    "data_quality": data_quality,
    "random_state": RANDOM_STATE,
}

import os
os.makedirs("ml/models", exist_ok=True)
os.makedirs("backend/models", exist_ok=True)
joblib.dump(bundle, "ml/models/content_performance_bundle.joblib")
joblib.dump(bundle, "backend/models/content_performance_bundle.joblib")

with open("ml/reports/test_metrics.json", "w") as f:
    json.dump(bundle["test_metrics"], f, indent=2)

with open("ml/reports/feature_importance.json", "w") as f:
    json.dump([{"feature": f_, "importance": float(i_)} for f_, i_ in feat_importance], f, indent=2)

with open("ml/reports/data_quality.json", "w") as f:
    json.dump(data_quality, f, indent=2)

print("\nSaved model bundle to ml/models/ and backend/models/")
print("Saved comparison tables + metrics to ml/reports/")
