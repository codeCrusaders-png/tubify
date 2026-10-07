from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@patch("app.services.youtube_service.youtube_service.extract_song_info")
def test_analyze_endpoint_success(mock_extract):
    """Test POST /analyze endpoint with valid input and successful extraction."""
    mock_extract.return_value = {
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "artist": "Rick Astley",
        "channel": "Rick Astley",
        "duration": "3:33",
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    }

    response = client.post("/analyze", json={"youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Never Gonna Give You Up"
    assert data["artist"] == "Rick Astley"
    assert data["duration"] == "3:33"
    assert data["video_id"] == "dQw4w9WgXcQ"


def test_analyze_endpoint_invalid_url():
    """Test POST /analyze endpoint returns HTTP 400 for bad URL."""
    response = client.post("/analyze", json={"youtube_url": "https://invalid-site.com/video"})
    assert response.status_code == 400
    assert "Invalid YouTube URL" in response.json()["detail"]

