from app.services.mood_service import mood_service, clean_text


def test_clean_text():
    """Verify text normalization removes punctuation and extra whitespace."""
    raw = "  Dark! Night Drive... (through empty streets)?? "
    assert clean_text(raw) == "dark night drive through empty streets"


def test_predict_mood_direct_category():
    """Verify direct category string match yields 1.0 confidence."""
    res = mood_service.predict_mood("Chill")
    assert res["mood"] == "Chill"
    assert res["confidence"] == 1.0


def test_predict_mood_natural_language_queries():
    """Verify natural language mood phrases map to appropriate categories."""
    night_res = mood_service.predict_mood("dark night drive")
    assert night_res["mood"] == "Late Night"
    assert night_res["confidence"] >= 0.25

    chill_res = mood_service.predict_mood("something peaceful for rainy evening")
    assert chill_res["mood"] == "Chill"
    assert chill_res["confidence"] >= 0.25

    gym_res = mood_service.predict_mood("heavy weights cardio energy workout")
    assert gym_res["mood"] == "Workout"
    assert gym_res["confidence"] >= 0.25

    study_res = mood_service.predict_mood("coding concentration deep work")
    assert study_res["mood"] == "Focus"
    assert study_res["confidence"] >= 0.25


def test_predict_mood_empty_fallback():
    """Verify empty input falls back gracefully."""
    res = mood_service.predict_mood("", fallback_context="Mr.Kitty After Dark")
    assert "mood" in res
    assert res["confidence"] > 0.0
