from fastapi import APIRouter, Header, HTTPException, status
from app.models.schemas import SpotifySearchRequest, SpotifySearchResponse
from app.services.spotify_service import spotify_service

router = APIRouter(prefix="/spotify", tags=["Spotify Operations"])


@router.post("/search", response_model=SpotifySearchResponse)
def search_spotify_track(payload: SpotifySearchRequest):
    """Search Spotify for matching tracks using parsed song title and artist."""
    try:
        results = spotify_service.search_track(
            title=payload.title,
            artist=payload.artist,
            access_token=payload.access_token,
        )
        return results
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Spotify search error: {str(e)}",
        )


@router.get("/playlists")
def get_user_playlists(authorization: str = Header(..., description="Bearer <Spotify Access Token>")):
    """Retrieve existing playlists for the authenticated user."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'.",
        )
    token = authorization.split(" ")[1]
    try:
        playlists = spotify_service.get_user_playlists(token)
        return {"playlists": playlists}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user playlists: {str(e)}",
        )
