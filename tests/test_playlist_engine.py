from unittest.mock import patch, MagicMock
from app.services.spotify_service import SpotifyService


@patch.object(SpotifyService, "get_user_playlists")
def test_find_playlist(mock_get_playlists):
    """Verify finding existing playlist by name (case-insensitive)."""
    mock_get_playlists.return_value = [
        {"id": "pl_1", "name": "Late Night", "total_tracks": 10},
        {"id": "pl_2", "name": "Workout Hype", "total_tracks": 25},
    ]

    service = SpotifyService()
    found = service.find_playlist("token", "late night")
    assert found is not None
    assert found["id"] == "pl_1"

    not_found = service.find_playlist("token", "Non Existent")
    assert not_found is None


@patch.object(SpotifyService, "track_exists")
@patch("httpx.Client")
def test_add_track_prevents_duplicate(mock_client, mock_track_exists):
    """Verify add_track does not add song if already present in playlist."""
    mock_track_exists.return_value = True

    service = SpotifyService()
    res = service.add_track("token", "pl_1", "spotify:track:123")

    assert res["success"] is False
    assert res["already_exists"] is True
    assert "already in this playlist" in res["message"]


@patch.object(SpotifyService, "track_exists")
@patch("httpx.Client")
def test_add_track_success(mock_client_class, mock_track_exists):
    """Verify add_track adds song when not duplicated."""
    mock_track_exists.return_value = False

    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_client.post.return_value = mock_resp

    service = SpotifyService()
    res = service.add_track("token", "pl_1", "spotify:track:123")

    assert res["success"] is True
    assert res["already_exists"] is False
