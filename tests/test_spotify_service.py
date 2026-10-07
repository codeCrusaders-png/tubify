from unittest.mock import patch
from app.services.spotify_service import SpotifyService, string_similarity


def test_string_similarity():
    """Verify string similarity ratio metric."""
    assert string_similarity("Blinding Lights", "Blinding Lights") == 1.0
    assert string_similarity("Blinding Lights", "Blinding Lights (Remix)") > 0.70
    assert string_similarity("Queen", "The Weeknd") <= 0.40


@patch.object(SpotifyService, "_execute_search")
def test_search_track_success(mock_search):
    """Verify track search matches candidates and computes confidence scores."""
    mock_search.return_value = [
        {
            "id": "track_123",
            "uri": "spotify:track:track_123",
            "name": "After Dark",
            "artists": [{"name": "Mr.Kitty"}],
            "album": {
                "name": "Time",
                "images": [{"url": "https://image.url/cover.jpg"}],
            },
            "external_urls": {"spotify": "https://open.spotify.com/track/track_123"},
            "preview_url": None,
        },
        {
            "id": "track_456",
            "uri": "spotify:track:track_456",
            "name": "After Dark (Acoustic)",
            "artists": [{"name": "Mr.Kitty"}],
            "album": {
                "name": "Time Acoustic",
                "images": [],
            },
            "external_urls": {"spotify": "https://open.spotify.com/track/track_456"},
            "preview_url": None,
        },
    ]

    service = SpotifyService()
    result = service.search_track(title="After Dark", artist="Mr.Kitty", access_token="fake_token")

    assert result["matched"] is True
    assert result["track"]["spotify_track_id"] == "track_123"
    assert result["track"]["title"] == "After Dark"
    assert result["track"]["artist"] == "Mr.Kitty"
    assert result["confidence"] >= 0.90
    assert len(result["candidates"]) == 2


@patch.object(SpotifyService, "_execute_search")
def test_search_track_not_found(mock_search):
    """Verify search returns matched False when no tracks are found."""
    mock_search.return_value = []
    service = SpotifyService()
    result = service.search_track(title="NonExistentSong12345", artist="Nobody", access_token="fake_token")

    assert result["matched"] is False
    assert result["confidence"] == 0.0
    assert result["track"] is None
