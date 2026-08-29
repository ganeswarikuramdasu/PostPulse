"""
eda.py - Exploratory Data Analysis for the Content Performance dataset.

Run: python ml/src/eda.py
Outputs: PNG charts + eda_summary.txt in ml/reports/
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")

df = pd.read_csv("ml/data/content_performance_raw.csv")
report = []

report.append(f"Shape: {df.shape}")
report.append(f"\nMissing values:\n{df.isnull().sum()[df.isnull().sum() > 0]}")
report.append(f"\nDuplicate rows: {df.duplicated().sum()}")
report.append(f"\nTarget describe (expected_views):\n{df['expected_views'].describe()}")
report.append(f"\nTarget describe (expected_engagement_rate):\n{df['expected_engagement_rate'].describe()}")
report.append(f"\nPerformance category counts:\n{df['performance_category'].value_counts()}")

# outlier check via IQR on expected_views
q1, q3 = df["expected_views"].quantile([0.25, 0.75])
iqr = q3 - q1
outliers = df[(df["expected_views"] < q1 - 1.5 * iqr) | (df["expected_views"] > q3 + 1.5 * iqr)]
report.append(f"\nOutliers in expected_views (IQR method): {len(outliers)} ({len(outliers)/len(df):.1%})")

with open("ml/reports/eda_summary.txt", "w") as f:
    f.write("\n".join(str(r) for r in report))

# 1. Target distributions
fig, axes = plt.subplots(1, 3, figsize=(16, 4))
sns.histplot(df["expected_views"].clip(upper=df["expected_views"].quantile(0.99)), bins=50, ax=axes[0], color="#5B8DEF")
axes[0].set_title("Expected Views (clipped @ p99)")
sns.histplot(df["expected_engagement_rate"], bins=50, ax=axes[1], color="#6FCF97")
axes[1].set_title("Expected Engagement Rate (%)")
sns.histplot(df["performance_score"], bins=30, ax=axes[2], color="#F2994A")
axes[2].set_title("Performance Score")
plt.tight_layout()
plt.savefig("ml/reports/target_distributions.png", dpi=110)
plt.close()

# 2. Category counts
plt.figure(figsize=(5, 4))
sns.countplot(data=df, x="performance_category", order=["Low", "Medium", "High"], palette=["#EB5757", "#F2994A", "#27AE60"])
plt.title("Performance Category Distribution")
plt.tight_layout()
plt.savefig("ml/reports/category_counts.png", dpi=110)
plt.close()

# 3. Account type-wise average performance (this dataset is Instagram-only,
# so there's no cross-platform comparison anymore - see README)
plt.figure(figsize=(8, 4.5))
acct_perf = df.groupby("account_type")["performance_score"].mean().sort_values(ascending=False)
sns.barplot(x=acct_perf.values, y=acct_perf.index, palette="viridis")
plt.title("Average Performance Score by Account Type")
plt.xlabel("Avg Performance Score")
plt.tight_layout()
plt.savefig("ml/reports/platform_performance.png", dpi=110)
plt.close()

# 4. Posting hour vs performance
plt.figure(figsize=(9, 4.5))
hour_perf = df.groupby("posting_hour")["performance_score"].mean()
sns.lineplot(x=hour_perf.index, y=hour_perf.values, marker="o", color="#9B51E0")
plt.title("Average Performance Score by Posting Hour")
plt.xlabel("Hour of Day (24h)")
plt.ylabel("Avg Performance Score")
plt.tight_layout()
plt.savefig("ml/reports/posting_hour_performance.png", dpi=110)
plt.close()

# 5. Content type vs performance
plt.figure(figsize=(8, 4.5))
ct_perf = df.groupby("content_type")["performance_score"].mean().sort_values(ascending=False)
sns.barplot(x=ct_perf.values, y=ct_perf.index, palette="mako")
plt.title("Average Performance Score by Content Type")
plt.tight_layout()
plt.savefig("ml/reports/content_type_performance.png", dpi=110)
plt.close()

# 6. Correlation heatmap (numeric features + targets)
numeric_cols = df.select_dtypes(include="number").columns
plt.figure(figsize=(10, 8))
corr = df[numeric_cols].corr()
sns.heatmap(corr, cmap="coolwarm", center=0, annot=False)
plt.title("Correlation Heatmap (numeric features)")
plt.tight_layout()
plt.savefig("ml/reports/correlation_heatmap.png", dpi=110)
plt.close()

print("EDA complete. See ml/reports/")
