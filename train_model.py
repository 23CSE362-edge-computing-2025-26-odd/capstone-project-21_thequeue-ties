# train_model.py
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    average_precision_score,
    precision_recall_curve,
    confusion_matrix,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
import joblib

# ----------------------------
# Config (edit as needed)
# ----------------------------
RANDOM_SEED = 42
TEST_SIZE = 0.25
RECALL_TARGET = 0.80      # optional: try to meet this recall (class 1)
MIN_PRECISION = 0.20      # only accept thresholds meeting this precision
USE_RECALL_TARGET = True  # if False, we use "best F1" threshold
MODEL_PATH = "failure_rf.pkl"
META_PATH = "model_meta.json"

# ----------------------------
# Load data
# ----------------------------
df = pd.read_csv("training_data.csv")

num_cols = [
    "temperature_c","vibration_rms_mm_s",
    "temp_threshold","vib_threshold",
    "dt_seconds","d_temp","d_vibration",
    "pct_of_temp_thresh","pct_of_vib_thresh",
    "temp_avg_win","temp_std_win","vib_avg_win","vib_std_win"
]
cat_cols = ["class_name"]
target = "failure_flag"

X = df[num_cols + cat_cols]
y = df[target].astype(int)

# ----------------------------
# Split
# ----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_SEED
)

# ----------------------------
# Preprocess + Model
# ----------------------------
num_pipe = Pipeline([
    ("impute", SimpleImputer(strategy="median")),
])

cat_pipe = Pipeline([
    ("impute", SimpleImputer(strategy="most_frequent")),
    ("oh", OneHotEncoder(handle_unknown="ignore"))
])

pre = ColumnTransformer([
    ("num", num_pipe, num_cols),
    ("cat", cat_pipe, cat_cols),
])

clf = RandomForestClassifier(
    n_estimators=400,
    max_depth=None,
    class_weight="balanced",   # handle imbalance
    random_state=RANDOM_SEED,
    n_jobs=-1
)

pipe = Pipeline([
    ("pre", pre),
    ("clf", clf)
])

# ----------------------------
# Train
# ----------------------------
pipe.fit(X_train, y_train)

# ----------------------------
# Evaluate (probabilities)
# ----------------------------
y_prob = pipe.predict_proba(X_test)[:, 1]

roc_auc = roc_auc_score(y_test, y_prob)
pr_auc = average_precision_score(y_test, y_prob)
prec, rec, thr = precision_recall_curve(y_test, y_prob)
f1 = (2 * prec * rec) / (prec + rec + 1e-12)

# Best-F1 threshold
best_f1_idx = int(np.argmax(f1))
best_f1_thr = float(thr[best_f1_idx]) if best_f1_idx < len(thr) else 0.5

# Optional: target recall with minimum precision
target_thr = None
if USE_RECALL_TARGET:
    for p, r, t in zip(prec, rec, np.r_[thr, 1.0]):
        if r >= RECALL_TARGET and p >= MIN_PRECISION:
            target_thr = float(t)
            break

chosen_thr = float(target_thr if target_thr is not None else best_f1_thr)

# Final discrete predictions at chosen threshold
y_pred = (y_prob >= chosen_thr).astype(int)

# Reports
cm = confusion_matrix(y_test, y_pred)
report = classification_report(y_test, y_pred, digits=3)

print("\n=== PERFORMANCE (Prob-based) ===")
print(f"ROC-AUC: {roc_auc:.3f}")
print(f"PR-AUC:  {pr_auc:.3f}")
print("\n=== THRESHOLDS ===")
print(f"Best-F1 threshold: {best_f1_thr:.3f} (F1={f1[best_f1_idx]:.3f})")
if target_thr is not None:
    print(f"Recall-target threshold: {target_thr:.3f} (target recall={RECALL_TARGET}, min precision={MIN_PRECISION})")
print(f"Chosen threshold for classification: {chosen_thr:.3f}")

print("\n=== CLASSIFICATION @ Chosen Threshold ===")
print(report)
print("Confusion matrix [tn fp; fn tp]:")
print(cm)

# ----------------------------
# Save model + meta (threshold)
# ----------------------------
joblib.dump(pipe, MODEL_PATH)
with open(META_PATH, "w") as f:
    json.dump({
        "model_path": MODEL_PATH,
        "chosen_threshold": chosen_thr,
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "best_f1_threshold": best_f1_thr,
        "used_recall_target": USE_RECALL_TARGET,
        "recall_target": RECALL_TARGET,
        "min_precision": MIN_PRECISION
    }, f, indent=2)

print(f"\nSaved model → {MODEL_PATH}")
print(f"Saved metadata (incl. threshold) → {META_PATH}")
