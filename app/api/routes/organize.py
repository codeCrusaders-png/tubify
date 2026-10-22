from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.database import MoodHistory, get_db
from app.models.schemas import AddTrackRequest, AddTrackResponse
from app.services.spotify_service import spotify_service

router = APIRouter(prefix="/organize", tags=["Organize & History"])


@router.post("/add", response_model=AddTrackResponse)
def add_track_to_playlist(
    payload: AddTrackRequest,
    db: Session = Depends(get_db),
):
    """Add a confirmed track to a Spotify playlist with duplicate detection and history logging."""
    access_token = payload.access_token

    # 1. Fetch user profile
    try:
        user_profile = spotify_service.get_current_user_profile(access_token)
        user_id = user_profile["id"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Spotify session or expired token: {str(e)}",
        )

    target_playlist_id = payload.playlist_id
    target_playlist_name = payload.playlist_name
    playlist_url = None

    # 2. Resolve Playlist
    if not target_playlist_id:
        existing = spotify_service.find_playlist(access_token, target_playlist_name)
        if existing:
            target_playlist_id = existing["id"]
            playlist_url = existing.get("spotify_url")
        else:
            if not payload.create_if_missing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Playlist '{target_playlist_name}' does not exist. Please confirm playlist creation.",
                )
            # Create playlist
            new_pl = spotify_service.create_playlist(
                access_token=access_token,
                user_id=user_id,
                playlist_name=target_playlist_name,
            )
            target_playlist_id = new_pl["id"]
            playlist_url = new_pl.get("spotify_url")

    if target_playlist_id and not playlist_url:
        playlist_url = f"https://open.spotify.com/playlist/{target_playlist_id}"

    # 3. Duplicate check & Add track
    try:
        result = spotify_service.add_track(
            access_token=access_token,
            playlist_id=target_playlist_id,
            track_uri=payload.track_uri,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add track to Spotify playlist: {str(e)}",
        )

    # 4. Save decision to mood_history if addition was attempted/successful
    if result["success"]:
        history_entry = MoodHistory(
            song_id=payload.song_id,
            song_title=payload.song_title,
            artist=payload.artist,
            user_mood=payload.user_mood or "",
            ai_mood=payload.ai_mood,
            recommended_playlist=payload.recommended_playlist,
            selected_playlist=target_playlist_name,
        )
        db.add(history_entry)
        db.commit()

    return AddTrackResponse(
        success=result["success"],
        already_exists=result.get("already_exists", False),
        message=result["message"],
        playlist_name=target_playlist_name,
        playlist_id=target_playlist_id,
        playlist_url=playlist_url,
        spotify_track_url=f"https://open.spotify.com/track/{payload.song_id}",
    )


@router.get("/history")
def get_mood_history(db: Session = Depends(get_db)):
    """Fetch user's past music organization decisions."""
    records = db.query(MoodHistory).order_by(MoodHistory.created_at.desc()).limit(50).all()
    return {
        "history": [
            {
                "id": r.id,
                "song_id": r.song_id,
                "song_title": r.song_title,
                "artist": r.artist,
                "user_mood": r.user_mood,
                "ai_mood": r.ai_mood,
                "recommended_playlist": r.recommended_playlist,
                "selected_playlist": r.selected_playlist,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }


@router.delete("/history")
def clear_mood_history(db: Session = Depends(get_db)):
    """Clear past music organization history."""
    db.query(MoodHistory).delete()
    db.commit()
    return {"success": True, "message": "History cleared successfully."}
