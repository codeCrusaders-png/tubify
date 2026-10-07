import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from app.services.mood_service import mood_service, TRAINING_DATA, clean_text, MOOD_CATEGORIES


def test_classifier_cross_validation_benchmark():
    """Verify ML pipeline attains high cross-validation performance (>85%)."""
    texts = [clean_text(item[0]) for item in TRAINING_DATA]
    labels = [item[1] for item in TRAINING_DATA]

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(mood_service.pipeline, texts, labels, cv=cv, scoring="accuracy")

    mean_acc = np.mean(scores)
    assert mean_acc >= 0.85, f"Expected cross-validation accuracy >= 85%, got {mean_acc * 100:.2f}%"


def test_classifier_covers_all_categories():
    """Verify pipeline includes and predicts across all 7 target classes."""
    assert set(mood_service.categories) == set(MOOD_CATEGORIES)
    for cat in MOOD_CATEGORIES:
        res = mood_service.predict_mood(cat)
        assert res["mood"] == cat
        assert res["confidence"] == 1.0
