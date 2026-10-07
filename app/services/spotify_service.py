import base64
from difflib import SequenceMatcher
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import httpx
from app.core.config import settings


SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

SPOTIFY_SCOPES = [
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-read-private",
]


def string_similarity(a: str, b: str) -> float:
    """Calculate ratio of similarity between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, (a or "").lower().strip(), (b or "").lower().strip()).ratio()


class SpotifyService:
    """Abstraction for Spotify Web API and OAuth 2.0 interactions."""

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self._client_credentials_token: Optional[str] = None
        self._client_token_expiry: float = 0.0

    # -------------------------------------------------------------
    # Authentication & OAuth Flow
    # -------------------------------------------------------------

    def get_authorization_url(self, state: str = "state") -> str:
        """Generate Spotify OAuth 2.0 authorization URL."""
        if not settings.SPOTIFY_CLIENT_ID:
            raise ValueError("SPOTIFY_CLIENT_ID is not configured in .env")

        params = {
            "client_id": settings.SPOTIFY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
            "scope": " ".join(SPOTIFY_SCOPES),
            "state": state,
            "show_dialog": "true",
        }
        return f"{SPOTIFY_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
            raise ValueError("Spotify credentials (CLIENT_ID / CLIENT_SECRET) are missing.")

        auth_header = base64.b64encode(
            f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
            if response.status_code != 200:
                raise ValueError(f"Spotify token exchange failed: {response.text}")
            return response.json()

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token using refresh_token."""
        auth_header = base64.b64encode(
            f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
            if response.status_code != 200:
                raise ValueError(f"Failed to refresh Spotify token: {response.text}")
            return response.json()

    def get_client_credentials_token(self) -> str:
        """Obtain Client Credentials access token for public search when user token is absent."""
        if self._client_credentials_token and time.time() < self._client_token_expiry - 60:
            return self._client_credentials_token

        if not settings.SPOTIFY_CLIENT_ID or not settings.SPOTIFY_CLIENT_SECRET:
            raise ValueError("Spotify credentials (CLIENT_ID / CLIENT_SECRET) are missing.")

        auth_header = base64.b64encode(
            f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"grant_type": "client_credentials"}

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch client credentials token: {response.text}")
            data = response.json()
            self._client_credentials_token = data["access_token"]
            self._client_token_expiry = time.time() + data.get("expires_in", 3600)
            return self._client_credentials_token

    # -------------------------------------------------------------
    # Search & Track Matching (Phase 4)
    # -------------------------------------------------------------

    def search_track(
        self,
        title: str,
        artist: str,
        access_token: Optional[str] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """Search Spotify for matching tracks using title and artist.

        Calculates confidence score and provides candidate alternatives.
        """
        token = access_token or self.get_client_credentials_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Clean query terms
        clean_title = title.strip()
        clean_artist = artist.strip()

        # Step 1: Field-specific search
        query = f"track:{clean_title} artist:{clean_artist}"
        tracks = self._execute_search(query, headers, limit)

        # Step 2: Fallback to loose general search if zero results
        if not tracks:
            fallback_query = f"{clean_artist} {clean_title}"
            tracks = self._execute_search(fallback_query, headers, limit)

        if not tracks:
            return {
                "matched": False,
                "confidence": 0.0,
                "track": None,
                "candidates": [],
            }

        candidates = []
        for t in tracks:
            item_artists = [a["name"] for a in t.get("artists", [])]
            primary_artist = item_artists[0] if item_artists else "Unknown"
            track_title = t.get("name", "")

            # Confidence is harmonic mean/combination of artist match & title match
            title_sim = string_similarity(clean_title, track_title)
            artist_sim = max([string_similarity(clean_artist, a) for a in item_artists]) if item_artists else 0.0
            combined_confidence = round((title_sim * 0.6) + (artist_sim * 0.4), 2)

            album_data = t.get("album", {})
            album_images = album_data.get("images", [])
            album_art = album_images[0]["url"] if album_images else None

            candidate = {
                "spotify_track_id": t["id"],
                "spotify_uri": t["uri"],
                "title": track_title,
                "artist": ", ".join(item_artists),
                "album": album_data.get("name", ""),
                "album_art": album_art,
                "spotify_url": t.get("external_urls", {}).get("spotify", ""),
                "preview_url": t.get("preview_url"),
                "confidence": combined_confidence,
            }
            candidates.append(candidate)

        # Sort candidates descending by confidence
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        best_match = candidates[0]

        return {
            "matched": True,
            "confidence": best_match["confidence"],
            "track": best_match,
            "candidates": candidates,
        }

    def _execute_search(self, query: str, headers: Dict[str, str], limit: int) -> List[Dict[str, Any]]:
        url = f"{SPOTIFY_API_BASE}/search"
        params = {"q": query, "type": "track", "limit": limit}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                return resp.json().get("tracks", {}).get("items", [])
            return []

    # -------------------------------------------------------------
    # Playlist Management (Phase 5)
    # -------------------------------------------------------------

    def get_current_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetch current logged-in user profile."""
        headers = {"Authorization": f"Bearer {access_token}"}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.get(f"{SPOTIFY_API_BASE}/me", headers=headers)
            if resp.status_code != 200:
                raise ValueError(f"Failed to fetch Spotify user profile: {resp.text}")
            return resp.json()

    def get_user_playlists(self, access_token: str) -> List[Dict[str, Any]]:
        """Retrieve user's existing Spotify playlists."""
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{SPOTIFY_API_BASE}/me/playlists"
        params = {"limit": 50}

        playlists = []
        with httpx.Client(timeout=self.timeout_seconds) as client:
            while url:
                resp = client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    break
                data = resp.json()
                for item in data.get("items", []):
                    if item:
                        playlists.append(
                            {
                                "id": item["id"],
                                "name": item["name"],
                                "total_tracks": item.get("tracks", {}).get("total", 0),
                                "spotify_url": item.get("external_urls", {}).get("spotify", ""),
                            }
                        )
                url = data.get("next")
                params = None  # Next URL already includes pagination query parameters
        return playlists

    def find_playlist(self, access_token: str, playlist_name: str) -> Optional[Dict[str, Any]]:
        """Find a playlist by exact or case-insensitive name match."""
        playlists = self.get_user_playlists(access_token)
        clean_target = playlist_name.strip().lower()
        for p in playlists:
            if p["name"].strip().lower() == clean_target:
                return p
        return None

    def create_playlist(
        self,
        access_token: str,
        user_id: str,
        playlist_name: str,
        description: str = "Created via YouTube to Spotify Personal Music Organizer",
        public: bool = False,
    ) -> Dict[str, Any]:
        """Create a new playlist for the user."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        url = f"{SPOTIFY_API_BASE}/users/{user_id}/playlists"
        payload = {
            "name": playlist_name,
            "description": description,
            "public": public,
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                raise ValueError(f"Failed to create playlist '{playlist_name}': {resp.text}")
            data = resp.json()
            return {
                "id": data["id"],
                "name": data["name"],
                "total_tracks": 0,
                "spotify_url": data.get("external_urls", {}).get("spotify", ""),
            }

    def track_exists(self, access_token: str, playlist_id: str, track_uri: str) -> bool:
        """Check if a track already exists inside the playlist to prevent duplicates."""
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks"
        params = {"fields": "items(track(uri)),next", "limit": 100}

        with httpx.Client(timeout=self.timeout_seconds) as client:
            while url:
                resp = client.get(url, headers=headers, params=params)
                if resp.status_code != 200:
                    return False
                data = resp.json()
                for item in data.get("items", []):
                    track = item.get("track")
                    if track and track.get("uri") == track_uri:
                        return True
                url = data.get("next")
                params = None
        return False

    def add_track(self, access_token: str, playlist_id: str, track_uri: str) -> Dict[str, Any]:
        """Add track to a playlist after duplicate check."""
        if self.track_exists(access_token, playlist_id, track_uri):
            return {
                "success": False,
                "already_exists": True,
                "message": "Track is already in this playlist.",
            }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks"
        payload = {"uris": [track_uri]}

        with httpx.Client(timeout=self.timeout_seconds) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                raise ValueError(f"Failed to add track to playlist: {resp.text}")
            return {
                "success": True,
                "already_exists": False,
                "message": "Track successfully added to playlist.",
            }


spotify_service = SpotifyService()
