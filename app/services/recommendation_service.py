from collections import Counter
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.database import MoodHistory
from app.services.mood_service import mood_service
from app.services.spotify_service import string_similarity


class RecommendationService:
    """Combines NLP mood detection, user natural language input, and historical user taste

    to recommend existing or new Spotify playlists.
    """

    def recommend(
        self,
        title: str,
        artist: str,
        user_mood_input: Optional[str],
        user_playlists: List[Dict[str, Any]],
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Generate playlist recommendation and alternatives."""
        raw_input = (user_mood_input or "").strip()
        fallback_context = f"{title} {artist}"

        # 1. NLP Mood Prediction
        nlp_result = mood_service.predict_mood(raw_input, fallback_context=fallback_context)
        detected_ai_mood = nlp_result["mood"]
        ai_confidence = nlp_result["confidence"]

        # 2. Historical Taste Personalization
        historical_playlist_boost: Optional[str] = None
        historical_weight = 0.0

        if db and raw_input:
            history_records = db.query(MoodHistory).all()
            matching_playlists = []
            for record in history_records:
                if record.user_mood:
                    sim = string_similarity(record.user_mood, raw_input)
                    if sim >= 0.70:
                        matching_playlists.append(record.selected_playlist)

            if matching_playlists:
                # Find most frequent playlist chosen for this mood type
                counts = Counter(matching_playlists)
                most_common_playlist, count = counts.most_common(1)[0]
                historical_playlist_boost = most_common_playlist
                historical_weight = min(0.35, count * 0.1)

        # 3. Determine Candidate Playlists
        candidate_primary = historical_playlist_boost if historical_playlist_boost else detected_ai_mood

        # 4. Map candidate against existing user playlists
        playlist_map = {p["name"].strip().lower(): p for p in user_playlists}

        def find_best_existing(target_name: str) -> Optional[Dict[str, Any]]:
            # Exact match
            target_lower = target_name.strip().lower()
            if target_lower in playlist_map:
                return playlist_map[target_lower]
            # Substring or high similarity match (e.g. "Late Night" matches "Late Night Drives")
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

        # Final calculated confidence
        final_confidence = min(0.98, round(ai_confidence + historical_weight, 2))

        # 5. Build Alternatives
        alternatives = []
        scores = nlp_result.get("all_scores", {})
        sorted_moods = sorted(scores.items(), key=lambda x: x[1], reverse=True)

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

        explanation = f"Detected mood '{detected_ai_mood}' with {int(ai_confidence * 100)}% confidence."
        if historical_playlist_boost:
            explanation += f" Adjusted for your past taste matching '{historical_playlist_boost}'."

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
