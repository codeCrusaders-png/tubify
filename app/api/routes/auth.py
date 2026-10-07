from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from app.core.config import settings
from app.services.spotify_service import spotify_service

router = APIRouter(prefix="/auth/spotify", tags=["Spotify Auth"])


@router.get("/status")
def get_auth_status():
    """Check if Spotify credentials are configured in .env."""
    is_configured = bool(settings.SPOTIFY_CLIENT_ID and settings.SPOTIFY_CLIENT_SECRET)
    return {
        "configured": is_configured,
        "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        "client_id_set": bool(settings.SPOTIFY_CLIENT_ID),
    }


@router.get("/login")
def login_with_spotify(redirect_to_auth: bool = Query(True)):
    """Generate Spotify OAuth URL. Redirects user or returns URL."""
    try:
        url = spotify_service.get_authorization_url()
        if redirect_to_auth:
            return RedirectResponse(url)
        return {"auth_url": url}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/callback")
def spotify_callback(code: Optional[str] = None, error: Optional[str] = None):
    """Handle OAuth callback from Spotify and exchange authorization code for tokens."""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Spotify authentication error: {error}",
        )
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authorization code missing from Spotify callback.",
        )

    try:
        token_data = spotify_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
        return RedirectResponse(
            f"/?access_token={access_token}&refresh_token={refresh_token}&expires_in={expires_in}#auth_success"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to exchange token with Spotify: {str(e)}",
        )


@router.post("/refresh")
def refresh_token(refresh_token: str = Query(...)):
    """Refresh an expired Spotify access token."""
    try:
        data = spotify_service.refresh_access_token(refresh_token)
        return data
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
