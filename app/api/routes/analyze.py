from fastapi import APIRouter, HTTPException, status
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.youtube_service import youtube_service

router = APIRouter(tags=["YouTube"])


@router.post("/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
def analyze_youtube_url(payload: AnalyzeRequest) -> AnalyzeResponse:
    """Extract and normalize song title, artist, and metadata from a YouTube URL."""
    try:
        data = youtube_service.extract_song_info(payload.youtube_url)
        return AnalyzeResponse(**data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while analyzing the YouTube video: {str(e)}",
        )

