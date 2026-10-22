from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base, MoodHistory
from app.services.recommendation_service import RecommendationService


def create_in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_recommendation_with_existing_playlist():
    """Verify recommendation maps to existing user playlist when available."""
    rec_service = RecommendationService()
    user_playlists = [
        {"id": "pl_ln", "name": "Late Night Vibes"},
        {"id": "pl_ch", "name": "Chill Beats"},
    ]

    res = rec_service.recommend(
        title="After Dark",
        artist="Mr.Kitty",
        user_mood_input="dark night drive",
        user_playlists=user_playlists,
    )

    assert res["ai_mood"] == "Late Night"
    assert res["recommended_playlist"] == "Late Night Vibes"
    assert res["playlist_exists"] is True
    assert res["playlist_id"] == "pl_ln"
    assert res["confidence"] >= 0.25
    assert len(res["alternatives"]) > 0


def test_recommendation_requires_creation_when_playlist_missing():
    """Verify recommendation indicates playlist_exists=False if user has no such playlist."""
    rec_service = RecommendationService()
    user_playlists = [
        {"id": "pl_random", "name": "Pop Hits 2024"},
    ]

    res = rec_service.recommend(
        title="Weightless",
        artist="Marconi Union",
        user_mood_input="Chill",
        user_playlists=user_playlists,
    )

    assert res["recommended_playlist"] == "Chill"
    assert res["playlist_exists"] is False
    assert res["playlist_id"] == None


def test_recommendation_personalization_boost():
    """Verify historical choices adjust future recommendations."""
    db = create_in_memory_db()
    for _ in range(3):
        db.add(
            MoodHistory(
                song_id="s1",
                song_title="Song",
                artist="Artist",
                user_mood="night drive",
                ai_mood="Late Night",
                recommended_playlist="Late Night",
                selected_playlist="Midnight Cruise",
            )
        )
    db.commit()

    rec_service = RecommendationService()
    user_playlists = [{"id": "pl_mc", "name": "Midnight Cruise"}]

    res = rec_service.recommend(
        title="Resonance",
        artist="HOME",
        user_mood_input="night drive",
        user_playlists=user_playlists,
        db=db,
    )

    assert res["recommended_playlist"] == "Midnight Cruise"
    assert "past taste" in res["explanation"]


def test_recommendation_artist_affinity():
    """Verify artist affinity guides playlist recommendation when mood query is omitted."""
    db = create_in_memory_db()
    for _ in range(2):
        db.add(
            MoodHistory(
                song_id="s_m1",
                song_title="After Dark",
                artist="Mr.Kitty",
                user_mood="",
                ai_mood="Late Night",
                recommended_playlist="Late Night",
                selected_playlist="Dark Synthwave",
            )
        )
    db.commit()

    rec_service = RecommendationService()
    user_playlists = [{"id": "pl_ds", "name": "Dark Synthwave"}]

    res = rec_service.recommend(
        title="Glow",
        artist="Mr.Kitty",
        user_mood_input="",
        user_playlists=user_playlists,
        db=db,
    )

    assert res["recommended_playlist"] == "Dark Synthwave"
    assert "previously organized Mr.Kitty" in res["explanation"]
    assert res["playlist_exists"] is True
