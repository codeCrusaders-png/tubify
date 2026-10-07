from unittest.mock import patch, MagicMock
import pytest
from app.services.youtube_service import (
    extract_video_id,
    clean_channel_name,
    clean_title_noise,
    normalize_title_and_artist,
    YouTubeService,
)


def test_extract_video_id_variants():
    """Verify video ID extraction across various YouTube URL formats."""
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ&feature=share") == "dQw4w9WgXcQ"
    assert extract_video_id("https://music.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://example.com/not-youtube") is None
    assert extract_video_id("invalid-text") is None


def test_clean_channel_name():
    """Verify artist channel cleaning removes noise suffixes."""
    assert clean_channel_name("TheWeekndVEVO") == "TheWeeknd"
    assert clean_channel_name("Coldplay - Topic") == "Coldplay"
    assert clean_channel_name("Queen Official") == "Queen"
    assert clean_channel_name("Dua Lipa") == "Dua Lipa"


def test_clean_title_noise():
    """Verify boilerplate noise patterns are stripped from titles."""
    assert clean_title_noise("Blinding Lights (Official Video)") == "Blinding Lights"
    assert clean_title_noise("After Dark [Lyrics]") == "After Dark"
    assert clean_title_noise("Stay (Slowed + Reverb)") == "Stay"
    assert clean_title_noise("Lofi Hip Hop (1 Hour Loop)") == "Lofi Hip Hop"
    assert clean_title_noise("Never Gonna Give You Up (4K Remaster)") == "Never Gonna Give You Up"
    assert clean_title_noise('"Starboy" (Official Music Video)') == "Starboy"


def test_normalize_title_and_artist_with_separator():
    """Verify splitting artist and title when separator is present."""
    title, artist = normalize_title_and_artist("The Weeknd - Blinding Lights (Official Video)", "The Weeknd")
    assert title == "Blinding Lights"
    assert artist == "The Weeknd"

    title, artist = normalize_title_and_artist("Mr.Kitty – After Dark [Lyrics]", "Mr.Kitty")
    assert title == "After Dark"
    assert artist == "Mr.Kitty"


def test_normalize_title_and_artist_fallback_to_channel():
    """Verify fallback to channel name when title has no artist separator."""
    title, artist = normalize_title_and_artist("Bohemian Rhapsody (Remastered 2011)", "Queen Official")
    assert title == "Bohemian Rhapsody"
    assert artist == "Queen"


def test_youtube_service_invalid_url():
    """Verify service raises ValueError when given an invalid URL."""
    service = YouTubeService()
    with pytest.raises(ValueError, match="Invalid YouTube URL"):
        service.extract_song_info("https://google.com/search?q=song")


@patch("httpx.Client")
def test_youtube_service_extract_song_info_success(mock_client_class):
    """Verify extract_song_info coordinates oEmbed and metadata normalization properly."""
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_oembed_resp = MagicMock()
    mock_oembed_resp.status_code = 200
    mock_oembed_resp.json.return_value = {
        "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
        "author_name": "Rick Astley",
        "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
    }

    mock_page_resp = MagicMock()
    mock_page_resp.status_code = 200
    mock_page_resp.text = '<meta itemprop="duration" content="PT3M33S">'

    mock_client.get.side_effect = [mock_oembed_resp, mock_page_resp]

    service = YouTubeService()
    result = service.extract_song_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert result["video_id"] == "dQw4w9WgXcQ"
    assert result["title"] == "Never Gonna Give You Up"
    assert result["artist"] == "Rick Astley"
    assert result["channel"] == "Rick Astley"
    assert result["duration"] == "3:33"
    assert "thumbnail_url" in result

