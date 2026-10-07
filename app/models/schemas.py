from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class AnalyzeRequest(BaseModel):
    youtube_url: str = Field(..., description="Full YouTube URL to analyze (watch, share, or embed link)")


class AnalyzeResponse(BaseModel):
    youtube_url: str
    video_id: str
    title: str
    artist: str
    channel: str
    duration: str
    thumbnail_url: Optional[str] = None


class SpotifyTrackCandidate(BaseModel):
    spotify_track_id: str
    spotify_uri: str
    title: str
    artist: str
    album: str
    album_art: Optional[str] = None
    spotify_url: str
    preview_url: Optional[str] = None
    confidence: float


class SpotifySearchRequest(BaseModel):
    title: str
    artist: str
    access_token: Optional[str] = None


class SpotifySearchResponse(BaseModel):
    matched: bool
    confidence: float
    track: Optional[SpotifyTrackCandidate] = None
    candidates: List[SpotifyTrackCandidate] = []


class AlternativePlaylist(BaseModel):
    playlist: str
    playlist_exists: bool
    playlist_id: Optional[str] = None
    confidence: float


class MoodRecommendationRequest(BaseModel):
    title: str
    artist: str
    user_mood: Optional[str] = None
    access_token: Optional[str] = None


class MoodRecommendationResponse(BaseModel):
    recommended_playlist: str
    playlist_exists: bool
    playlist_id: Optional[str] = None
    confidence: float
    ai_mood: str
    user_mood: str
    explanation: str
    alternatives: List[AlternativePlaylist] = []


class AddTrackRequest(BaseModel):
    track_uri: str
    song_id: str
    song_title: str
    artist: str
    playlist_name: str
    playlist_id: Optional[str] = None
    create_if_missing: bool = False
    user_mood: Optional[str] = None
    ai_mood: str
    recommended_playlist: str
    access_token: str


class AddTrackResponse(BaseModel):
    success: bool
    already_exists: bool
    message: str
    playlist_name: str
    playlist_id: str
    playlist_url: Optional[str] = None
    spotify_track_url: Optional[str] = None
