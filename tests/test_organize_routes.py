from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import init_db

# Ensure database tables exist for tests
init_db()

client = TestClient(app)


def test_auth_status():
    """Verify auth status endpoint responds with configuration details."""
    response = client.get("/auth/spotify/status")
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "redirect_uri" in data


@patch("app.services.spotify_service.spotify_service.search_track")
def test_spotify_search_route(mock_search):
    """Verify POST /spotify/search route invokes service properly."""
    mock_search.return_value = {
        "matched": True,
        "confidence": 0.95,
        "track": {
            "spotify_track_id": "trk_1",
            "spotify_uri": "spotify:track:trk_1",
            "title": "Song",
            "artist": "Artist",
            "album": "Album",
            "album_art": None,
            "spotify_url": "https://open.spotify.com/track/trk_1",
            "preview_url": None,
            "confidence": 0.95,
        },
        "candidates": [],
    }

    res = client.post("/spotify/search", json={"title": "Song", "artist": "Artist"})
    assert res.status_code == 200
    assert res.json()["matched"] is True


@patch("app.services.recommendation_service.recommendation_service.recommend")
def test_recommend_route(mock_rec):
    """Verify POST /recommend route returns recommendations."""
    mock_rec.return_value = {
        "recommended_playlist": "Late Night",
        "playlist_exists": True,
        "playlist_id": "pl_1",
        "confidence": 0.92,
        "ai_mood": "Late Night",
        "user_mood": "night drive",
        "explanation": "Predicted from your input.",
        "alternatives": [],
    }

    res = client.post(
        "/recommend",
        json={"title": "Song", "artist": "Artist", "user_mood": "night drive"},
    )
    assert res.status_code == 200
    assert res.json()["recommended_playlist"] == "Late Night"


@patch("app.services.spotify_service.spotify_service.get_current_user_profile")
@patch("app.services.spotify_service.spotify_service.add_track")
def test_organize_add_success(mock_add_track, mock_user_profile):
    """Verify POST /organize/add adds track and saves decision to history."""
    mock_user_profile.return_value = {"id": "user_123", "display_name": "Test User"}
    mock_add_track.return_value = {
        "success": True,
        "already_exists": False,
        "message": "Track successfully added to playlist.",
    }

    payload = {
        "track_uri": "spotify:track:123",
        "song_id": "123",
        "song_title": "After Dark",
        "artist": "Mr.Kitty",
        "playlist_name": "Late Night",
        "playlist_id": "pl_ln",
        "create_if_missing": False,
        "user_mood": "dark night drive",
        "ai_mood": "Late Night",
        "recommended_playlist": "Late Night",
        "access_token": "valid_token",
    }

    res = client.post("/organize/add", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["playlist_name"] == "Late Night"

    history_res = client.get("/organize/history")
    assert history_res.status_code == 200
    history = history_res.json()["history"]
    assert any(h["song_id"] == "123" for h in history)
