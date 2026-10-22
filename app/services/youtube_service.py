import re
from typing import Any, Dict, Optional, Tuple
import urllib.parse
import httpx


# Comprehensive noise patterns found in music video titles
NOISE_PATTERNS = [
    r"\s*[|/]\s*(?:official\s*(?:music\s*|lyric\s*)?video|music\s*video|lyric\s*video|official\s*audio|official\s*visualizer|visualizer|audio).*$",
    r"\s*[\(\[\{]\s*(?:official\s*(?:music\s*|lyric\s*|visualizer\s*)?video|official\s*audio|official\s*visualizer|visualizer)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:lyrics?|lyric\s*video|audio|audio\s*only|official\s*track|color\s*coded\s*lyrics?)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:slowed\s*(?:\+|\&|and)?\s*reverb|slowed|reverb|speed\s*up|sped\s*up)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:\d+\s*hours?|\d+\s*hour\s*loop|loop|extended|extended\s*mix)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:(?:4k|hd|hq|1080p|720p|60fps|remaster(?:ed)?(?:\s*\d{4})?)\s*)+[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:prod\.\s*by\s*[\w\s]+|produced\s*by\s*[\w\s]+)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:clip\s*officiel|video\s*clip|mv)\s*[\)\]\}]",
    r"\s*[\(\[\{]\s*(?:explicit|clean|radio\s*edit)\s*[\)\]\}]",
]


def extract_video_id(url: str) -> Optional[str]:
    """Robustly extract the 11-character YouTube video ID from any valid YouTube URL format.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - youtube.com/watch?v=VIDEO_ID (without protocol)
    - https://www.youtube.com/watch?feature=share&v=VIDEO_ID (params before v)
    - https://youtu.be/VIDEO_ID?si=...
    - youtu.be/VIDEO_ID (without protocol)
    - https://m.youtube.com/watch?v=VIDEO_ID
    - https://music.youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/live/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    if not url or not isinstance(url, str):
        return None

    cleaned_url = url.strip()

    # If protocol is omitted (e.g. youtube.com/watch?v=...), prepend https://
    if "://" not in cleaned_url:
        cleaned_url = f"https://{cleaned_url}"

    try:
        parsed = urllib.parse.urlparse(cleaned_url)
    except Exception:
        return None

    hostname = (parsed.hostname or "").lower()

    # Short links: youtu.be/<video_id>
    if "youtu.be" in hostname:
        path = parsed.path.strip("/")
        video_id = path.split("/")[0] if path else ""
        if len(video_id) == 11 and re.match(r"^[\w-]{11}$", video_id):
            return video_id

    # Standard youtube domains
    if any(d in hostname for d in ("youtube.com", "m.youtube.com", "music.youtube.com")):
        # Path based: /shorts/<id>, /embed/<id>, /v/<id>, /live/<id>
        path_match = re.match(r"^/(?:shorts|embed|v|live)/([\w-]{11})", parsed.path)
        if path_match:
            return path_match.group(1)

        # Query param based: ?v=<id>
        query_params = urllib.parse.parse_qs(parsed.query)
        if "v" in query_params and query_params["v"]:
            candidate = query_params["v"][0]
            if len(candidate) == 11 and re.match(r"^[\w-]{11}$", candidate):
                return candidate

    return None


def clean_channel_name(channel: str) -> str:
    """Clean channel name by removing standard suffixes (VEVO, Topic, Official)."""
    if not channel:
        return ""
    cleaned = channel.strip()
    cleaned = re.sub(r"(?i)\s*-\s*topic$", "", cleaned)
    cleaned = re.sub(r"(?i)vevo$", "", cleaned)
    cleaned = re.sub(r"(?i)\s+official$", "", cleaned)
    cleaned = re.sub(r"(?i)\s+music$", "", cleaned)
    cleaned = re.sub(r"(?i)\s+records$", "", cleaned)
    return cleaned.strip()


def clean_title_noise(raw_title: str) -> str:
    """Strip boilerplate noise from video titles."""
    if not raw_title:
        return ""

    cleaned = raw_title
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

    # Strip surrounding quotes
    cleaned = cleaned.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()

    # Clean leftover dangling hyphens, colons, or pipes
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"[-–—:|]+$", "", cleaned).strip()
    return cleaned


def normalize_title_and_artist(raw_title: str, channel: str) -> Tuple[str, str]:
    """Parse raw title and channel into structured (song_title, artist)."""
    cleaned_full = clean_title_noise(raw_title)
    cleaned_chan = clean_channel_name(channel)

    # 1. Separator search (' - ', ' – ', ' — ', ' | ', ' : ')
    separator_match = re.search(r"\s+[-–—|:]\s+", cleaned_full)
    if separator_match:
        artist_part = cleaned_full[: separator_match.start()].strip()
        title_part = cleaned_full[separator_match.end() :].strip()

        # Clean any nested noise in both halves
        artist_final = clean_title_noise(artist_part)
        title_final = clean_title_noise(title_part)

        if artist_final and title_final:
            return title_final, artist_final

    # 2. Fallback: title is the cleaned title, artist derived from channel
    return cleaned_full, (cleaned_chan or "Unknown Artist")


def parse_iso_duration(duration_str: str) -> str:
    """Convert ISO 8601 duration (PT3M33S) to MM:SS or HH:MM:SS."""
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

    def __init__(self, timeout_seconds: float = 8.0):
        self.timeout_seconds = timeout_seconds

    def extract_song_info(self, youtube_url: str) -> Dict[str, Any]:
        """Extract song information from YouTube URL using official oEmbed and video page inspection."""
        video_id = extract_video_id(youtube_url)
        if not video_id:
            raise ValueError(f"Invalid YouTube URL: '{youtube_url}'. Please provide a valid YouTube watch, short, or share link.")

        canonical_url = f"https://www.youtube.com/watch?v={video_id}"
        oembed_url = f"https://www.youtube.com/oembed?url={canonical_url}&format=json"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds, headers=headers) as client:
                response = client.get(oembed_url)
                if response.status_code == 404:
                    raise ValueError(f"Video not found or is private/unavailable: '{youtube_url}'")
                response.raise_for_status()
                oembed_data = response.json()

                # Extract duration from page
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
            "artist": artist,
            "channel": channel,
            "duration": duration,
            "thumbnail_url": oembed_data.get("thumbnail_url", f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"),
        }


youtube_service = YouTubeService()
