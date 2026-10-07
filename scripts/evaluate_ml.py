import json
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report
from app.services.mood_service import TRAINING_DATA, clean_text, MOOD_CATEGORIES, mood_service


def evaluate():
    print("=" * 60)
    print("      TUBIFY NLP MOOD CLASSIFIER EVALUATION REPORT")
    print("=" * 60)

    texts = [clean_text(item[0]) for item in TRAINING_DATA]
    labels = [item[1] for item in TRAINING_DATA]

    # Stratified 5-Fold Cross Validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(mood_service.pipeline, texts, labels, cv=cv, scoring="accuracy")

    print(f"\nTotal Corpus Samples: {len(texts)}")
    print(f"Categories ({len(MOOD_CATEGORIES)}): {', '.join(MOOD_CATEGORIES)}")
    print(f"\nStratified 5-Fold Cross Validation Accuracies:")
    for fold_idx, score in enumerate(scores, 1):
        print(f"  Fold {fold_idx}: {score * 100:.2f}%")

    mean_acc = np.mean(scores)
    std_acc = np.std(scores)
    print(f"\n-> Mean Cross-Validation Accuracy: {mean_acc * 100:.2f}% (+/- {std_acc * 100:.2f}%)")

    # Fit pipeline on full dataset to inspect in-sample report
    mood_service.pipeline.fit(texts, labels)
    preds = mood_service.pipeline.predict(texts)

    labels_in_data = sorted(list(set(labels)))
    report_dict = classification_report(labels, preds, target_names=labels_in_data, output_dict=True)
    report_text = classification_report(labels, preds, target_names=labels_in_data)

    print("\nClassification Report:")
    print(report_text)

    # Export metrics JSON for documentation
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ml_evaluation.json")

    metrics_payload = {
        "total_samples": len(texts),
        "categories": MOOD_CATEGORIES,
        "kfold_mean_accuracy": round(float(mean_acc), 4),
        "kfold_std": round(float(std_acc), 4),
        "classification_report": report_dict,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)

    print(f"Metrics saved to: {out_path}")
    print("=" * 60)


if __name__ == "__main__":
    evaluate()
