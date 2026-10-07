import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import health, analyze, auth, spotify, recommend, organize
from app.core.config import settings
from app.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and tables
    init_db()
    yield


def create_application() -> FastAPI:
    """Application factory for the YouTube to Spotify Music Organizer."""
    application = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Extract song details from YouTube, match on Spotify, and organize playlists based on user mood.",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Configure CORS for local development & frontend interaction
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API Routers
    application.include_router(health.router)
    application.include_router(analyze.router)
    application.include_router(auth.router)
    application.include_router(spotify.router)
    application.include_router(recommend.router)
    application.include_router(organize.router)

    # Mount static frontend directory
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
    if os.path.exists(static_dir):
        application.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return application


app = create_application()
