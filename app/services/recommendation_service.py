from collections import Counter
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.database import MoodHistory
from app.services.mood_service import mood_service
from app.services.spotify_service import string_similarity


class RecommendationService:
    """Multi-Factor Hybrid Recommender combining:

    1. NLP Semantic Mood Affinity
    2. Historical Taste Personalization (Query Similarity & Frequency)
    3. Artist & Track Affinity
    4. Spotify Library Alignment
    """

    def recommend(
        self,
        title: str,
        artist: str,
        user_mood_input: Optional[str],
        user_playlists: List[Dict[str, Any]],
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Generate high-precision playlist recommendation with explainability."""
        raw_input = (user_mood_input or "").strip()
        fallback_context = f"{title} {artist}"

        # 1. NLP Mood Prediction
        nlp_result = mood_service.predict_mood(raw_input, fallback_context=fallback_context)
        detected_ai_mood = nlp_result["mood"]
        base_confidence = nlp_result["confidence"]
        all_mood_scores = nlp_result.get("all_scores", {})

        # 2. Historical Preferences & Artist Affinity Analysis
        historical_playlist_boost: Optional[str] = None
        historical_weight = 0.0
        artist_playlist_boost: Optional[str] = None
        explanation_factors = [f"NLP detected '{detected_ai_mood}' mood ({int(base_confidence * 100)}% match)"]

        if db:
            history_records = db.query(MoodHistory).all()
            now = datetime.now(timezone.utc)

            mood_matches = []
            artist_matches = []

            for record in history_records:
                # Recency weight (half-life of 30 days) with robust timezone handling
                created_dt = record.created_at
                if created_dt:
                    if created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=timezone.utc)
                    rec_age_days = max(0.0, (now - created_dt).total_seconds() / 86400)
                else:
                    rec_age_days = 0.0
                decay = math.exp(-0.02 * min(rec_age_days, 180))

                # Mood similarity
                if raw_input and record.user_mood:
                    sim = string_similarity(record.user_mood, raw_input)
                    if sim >= 0.65:
                        mood_matches.append((record.selected_playlist, sim * decay))

                # Artist matching
                if artist and record.artist and string_similarity(artist, record.artist) >= 0.80:
                    artist_matches.append((record.selected_playlist, decay))

            # Process mood match scores
            if mood_matches:
                score_by_pl: Dict[str, float] = {}
                for pl, score in mood_matches:
                    score_by_pl[pl] = score_by_pl.get(pl, 0.0) + score
                best_hist_pl = max(score_by_pl, key=score_by_pl.get)
                historical_playlist_boost = best_hist_pl
                historical_weight = min(0.30, round(score_by_pl[best_hist_pl] * 0.1, 2))
                explanation_factors.append(f"matched past taste for similar mood phrases -> '{best_hist_pl}'")

            # Process artist affinity
            if artist_matches:
                artist_counts = Counter([pl for pl, _ in artist_matches])
                fav_pl, count = artist_counts.most_common(1)[0]
                artist_playlist_boost = fav_pl
                explanation_factors.append(f"you previously organized {artist} into '{fav_pl}' ({count}x)")

        # 3. Determine Candidate Primary Playlist
        # Priority:
        # - Strong mood query history takes precedence if specific and confident
        # - Artist affinity takes precedence when user didn't enter a contrary mood
        # - Otherwise historical mood choice or detected NLP mood
        if historical_playlist_boost and historical_weight >= 0.20 and not (artist_playlist_boost and artist_playlist_boost == historical_playlist_boost):
            candidate_primary = historical_playlist_boost
        elif artist_playlist_boost:
            candidate_primary = artist_playlist_boost
        elif historical_playlist_boost:
            candidate_primary = historical_playlist_boost
        else:
            candidate_primary = detected_ai_mood

        # 4. Map candidate against existing user playlists
        playlist_map = {p["name"].strip().lower(): p for p in user_playlists}

        def find_best_existing(target_name: str) -> Optional[Dict[str, Any]]:
            target_lower = target_name.strip().lower()
            if target_lower in playlist_map:
                return playlist_map[target_lower]
            for name_lower, p_data in playlist_map.items():
                if target_lower in name_lower or name_lower in target_lower:
                    return p_data
                if string_similarity(target_lower, name_lower) >= 0.75:
                    return p_data
            return None

        primary_existing = find_best_existing(candidate_primary)
        primary_playlist_name = primary_existing["name"] if primary_existing else candidate_primary
        primary_exists = primary_existing is not None
        primary_playlist_id = primary_existing["id"] if primary_existing else None

        # Calculate final calibrated confidence
        final_confidence = min(0.98, max(0.40, round(base_confidence + historical_weight, 2)))

        # 5. Build Alternatives
        alternatives = []
        sorted_moods = sorted(all_mood_scores.items(), key=lambda x: x[1], reverse=True)

        for mood_name, score in sorted_moods:
            if mood_name == detected_ai_mood:
                continue
            alt_existing = find_best_existing(mood_name)
            alternatives.append(
                {
                    "playlist": alt_existing["name"] if alt_existing else mood_name,
                    "playlist_exists": alt_existing is not None,
                    "playlist_id": alt_existing["id"] if alt_existing else None,
                    "confidence": round(score, 2),
                }
            )
            if len(alternatives) >= 2:
                break

        explanation = "; ".join(explanation_factors) + "."

        return {
            "recommended_playlist": primary_playlist_name,
            "playlist_exists": primary_exists,
            "playlist_id": primary_playlist_id,
            "confidence": final_confidence,
            "ai_mood": detected_ai_mood,
            "user_mood": raw_input if raw_input else "Auto (AI Decision)",
            "explanation": explanation,
            "alternatives": alternatives,
        }


recommendation_service = RecommendationService()
