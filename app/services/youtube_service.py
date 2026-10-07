import re
from typing import Any, Dict, Optional, Tuple
import httpx


YOUTUBE_URL_REGEX = re.compile(
    r"^(https?://)?(www\.|m\.|music\.)?(youtube\.com/(watch\?v=|embed/|v/|shorts/)|youtu\.be/)([\w-]{11})",
    re.IGNORECASE,
)

NOISE_PATTERNS = [
    r"\s*[\(\[\{]\s*(?:official\s*(?:music\s*|lyric\s*)?video|official\s*audio|official\s*visualizer|visualizer)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:lyrics?|lyric\s*video|audio|audio\s*only)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:slowed\s*(?:\+|\&|and)?\s*reverb|slowed|reverb)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:\d+\s*hours?|\d+\s*hour\s*loop|loop)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:4k(?:\s*remaster(?:ed)?)?|hd|hq|remaster(?:ed)?(?:\s*\d+)?)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:prod\.\s*by\s*[\w\s]+|produced\s*by\s*[\w\s]+)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:clip\s*officiel|video\s*clip)\s*[\)\]\}]",
]


def extract_video_id(url: str) -> Optional[str]:
    """Extract standard 11-character YouTube video ID from various URL formats."""
    if not url:
        return None
    match = YOUTUBE_URL_REGEX.search(url.strip())
    if match:
        return match.group(5)
    return None


def clean_channel_name(channel: str) -> str:
    """Clean channel name by removing common artist channel suffixes like VEVO or - Topic."""
    if not channel:
        return ""
    cleaned = channel.strip()
    cleaned = re.sub(r"(?i)\s*-\s*topic$", "", cleaned)
    cleaned = re.sub(r"(?i)vevo$", "", cleaned)
    cleaned = re.sub(r"(?i)\s+official$", "", cleaned)
    cleaned = re.sub(r"(?i)\s+music$", "", cleaned)
    return cleaned.strip()


def clean_title_noise(raw_title: str) -> str:
    """Remove boilerplate noise (e.g., 'Official Video', 'Lyrics', 'Slowed') from title."""
    cleaned = raw_title
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    cleaned = cleaned.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"[-–—:|]+$", "", cleaned).strip()
    return cleaned


def normalize_title_and_artist(raw_title: str, channel: str) -> Tuple[str, str]:
    """Parse raw YouTube video title into structured (title, artist)."""
    cleaned_full_title = clean_title_noise(raw_title)
    cleaned_channel = clean_channel_name(channel)

    separator_match = re.search(r"\s+[-–—|:]\s+", cleaned_full_title)
    if separator_match:
        parts = cleaned_full_title[: separator_match.start()], cleaned_full_title[separator_match.end() :]
        artist_candidate = parts[0].strip()
        title_candidate = parts[1].strip()

        if artist_candidate and title_candidate:
            return clean_title_noise(title_candidate), clean_title_noise(artist_candidate)

    return cleaned_full_title, cleaned_channel


def parse_iso_duration(duration_str: str) -> str:
    """Convert ISO 8601 duration (PT3M33S) to readable MM:SS."""
    if not duration_str:
        return "Unknown"
    match = re.search(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    return duration_str


class YouTubeService:
    """Service responsible for validating YouTube URLs and extracting metadata."""

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds

    def extract_song_info(self, youtube_url: str) -> Dict[str, Any]:
        """Extract song information from YouTube URL using official oEmbed and video page inspection."""
        video_id = extract_video_id(youtube_url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL: '{youtube_url}'. Please provide a valid YouTube watch or share link.")

        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        oembed_url = f"https://www.youtube.com/oembed?url={canonical_url}&format=json"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds, headers=headers) as client:
                response = client.get(oembed_url)
                if response.status_code == 404:
                    raise ValueError(f"Video not found or is private/unavailable: '{youtube_url}'")
                response.raise_for_status()
                oembed_data = response.json()

                duration = "Unknown"
                try:
                    page_response = client.get(canonical_url)
                    if page_response.status_code == 200:
                        dur_match = re.search(r'itemprop="duration"\s+content="([^"]+)"', page_response.text)
                        if dur_match:
                            duration = parse_iso_duration(dur_match.group(1))
                        else:
                            ms_match = re.search(r'"approxDurationMs":"(\d+)"', page_response.text)
                            if ms_match:
                                total_sec = int(ms_match.group(1)) // 1000
                                duration = f"{total_sec // 60}:{total_sec % 60:02d}"
                except Exception:
                    duration = "Unknown"

        except httpx.HTTPStatusError as e:
            raise ValueError(f"YouTube metadata request failed: {e.response.status_code}")
        except httpx.RequestError as e:
            raise ConnectionError(f"Network error while connecting to YouTube: {str(e)}")

        raw_title = oembed_data.get("title", "")
        channel = oembed_data.get("author_name", "")
        title, artist = normalize_title_and_artist(raw_title, channel)

        return {
            "youtube_url": canonical_url,
            "video_id": video_id,
            "title": title,
            "artist": artist if artist else channel,
            "channel": channel,
            "duration": duration,
            "thumbnail_url": oembed_data.get("thumbnail_url", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"),
        }


youtube_service = YouTubeService()

