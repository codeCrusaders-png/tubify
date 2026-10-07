from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.schemas import MoodRecommendationRequest, MoodRecommendationResponse
from app.services.recommendation_service import recommendation_service
from app.services.spotify_service import spotify_service

router = APIRouter(tags=["Recommendation"])


@router.post("/recommend", response_model=MoodRecommendationResponse)
def get_playlist_recommendation(
    payload: MoodRecommendationRequest,
    db: Session = Depends(get_db),
):
    """Recommend a target Spotify playlist based on song details, user mood, AI NLP, and personal history."""
    user_playlists = []
    if payload.access_token:
        try:
            user_playlists = spotify_service.get_user_playlists(payload.access_token)
        except Exception:
            # Fallback to general recommendation if token is invalid or expired
            user_playlists = []

    try:
        recommendation = recommendation_service.recommend(
            title=payload.title,
            artist=payload.artist,
            user_mood_input=payload.user_mood,
            user_playlists=user_playlists,
            db=db,
        )
        return recommendation
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate playlist recommendation: {str(e)}",
        )
