import re
from typing import Dict, Any, List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


MOOD_CATEGORIES = [
    "Chill",
    "Late Night",
    "Sad",
    "Romantic",
    "Workout",
    "Focus",
    "Driving",
]

TRAINING_DATA: List[Tuple[str, str]] = [
    # Chill
    ("peaceful relaxing calm mellow ambient lofi beats", "Chill"),
    ("lazy sunday afternoon sitting on porch", "Chill"),
    ("rainy evening reading book warm tea cozy", "Chill"),
    ("acoustic guitar soft gentle morning coffee", "Chill"),
    ("unwinding after a long stressful day", "Chill"),
    ("breezy tranquil serene ocean waves floating", "Chill"),
    ("lofi hip hop to relax sleep to", "Chill"),
    ("smooth slow quiet mellow atmosphere", "Chill"),
    ("something peaceful for rainy evening", "Chill"),
    ("soothing calming slow tempo", "Chill"),

    # Late Night
    ("dark night drive midnight cruising empty highway", "Late Night"),
    ("2am thoughts insomnia late night vibes", "Late Night"),
    ("neon lights city skyline after hours", "Late Night"),
    ("synthwave retrowave dark electro night music", "Late Night"),
    ("after dark nocturnal moody mysterious atmosphere", "Late Night"),
    ("alone in my room at midnight looking at stars", "Late Night"),
    ("midnight ride through empty city streets", "Late Night"),
    ("dark moody atmospheric synth late evening", "Late Night"),
    ("deep nocturnal bass synthwave cruising", "Late Night"),
    ("dark night drive", "Late Night"),

    # Sad
    ("heartbreak crying broken heart tears sorrow", "Sad"),
    ("melancholy depressing grieving feeling lonely", "Sad"),
    ("sad emotional acoustic ballad crying alone", "Sad"),
    ("missing you wishing you were here grief", "Sad"),
    ("gloomy rainy day lost someone i loved", "Sad"),
    ("painful memories heartbreak hurt inside", "Sad"),
    ("dark depressing lonely broken soul", "Sad"),
    ("feeling helpless devastated weep mournful", "Sad"),

    # Romantic
    ("love song date night romantic dinner candles", "Romantic"),
    ("falling in love crush sweetheart romance", "Romantic"),
    ("slow dance holding hands kissing affection", "Romantic"),
    ("sensual intimate tender passion lovers", "Romantic"),
    ("candlelight anniversary wedding slow romance", "Romantic"),
    ("sweet melody love ballad for my partner", "Romantic"),
    ("butterflies in stomach romantic serenade", "Romantic"),

    # Workout
    ("gym motivation heavy bass high energy pump up", "Workout"),
    ("cardio running fast tempo aggressive electronic", "Workout"),
    ("lifting heavy weights fitness workout beast mode", "Workout"),
    ("intense training boxing crossfit explosive energy", "Workout"),
    ("running uphill adrenaline rush high bpm", "Workout"),
    ("powerlifting hard techno aggressive phonk", "Workout"),
    ("push past limits workout hype track", "Workout"),

    # Focus
    ("study coding concentration deep work programming", "Focus"),
    ("reading background instrumental no lyrics", "Focus"),
    ("productivity flow state ambient focus binaural", "Focus"),
    ("working on projects writing essay study session", "Focus"),
    ("deep concentration intellectual math science study", "Focus"),
    ("subtle instrumental beats for work and study", "Focus"),
    ("minimalist ambient noise focus and learn", "Focus"),

    # Driving
    ("road trip driving cruising with windows down", "Driving"),
    ("car stereo highway cruising fast lane sunny drive", "Driving"),
    ("weekend drive with friends roadtrip playlist", "Driving"),
    ("scenic mountain road speed cruising music", "Driving"),
    ("open road driving fast sports car radio", "Driving"),
    ("summer road trip windows rolled down breeze", "Driving"),
    ("car vibes driving into the sunset highway", "Driving"),
]


def clean_text(text: str) -> str:
    """Normalize text: lowercasing, removing special characters and extra whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class MoodClassifierService:
    """Classifies user natural language input and song context into predefined mood categories."""

    def __init__(self):
        self.categories = MOOD_CATEGORIES
        self.pipeline: Pipeline = Pipeline(
            [
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), stop_words="english")),
                ("clf", LogisticRegression(C=5.0, max_iter=300, random_state=42)),
            ]
        )
        self._train()

    def _train(self) -> None:
        """Train classifier with initial training dataset."""
        texts = [clean_text(item[0]) for item in TRAINING_DATA]
        labels = [item[1] for item in TRAINING_DATA]
        self.pipeline.fit(texts, labels)

    def predict_mood(self, user_text: str, fallback_context: str = "") -> Dict[str, Any]:
        """Predict mood category and confidence from natural language user input."""
        raw = (user_text or "").strip()

        # Check exact or case-insensitive category match
        for cat in self.categories:
            if raw.lower() == cat.lower():
                return {
                    "mood": cat,
                    "confidence": 1.0,
                    "all_scores": {c: (1.0 if c == cat else 0.0) for c in self.categories},
                }

        cleaned = clean_text(raw)
        if not cleaned:
            cleaned = clean_text(fallback_context)

        if not cleaned:
            return {
                "mood": "Chill",
                "confidence": 0.50,
                "all_scores": {c: round(1.0 / len(self.categories), 2) for c in self.categories},
            }

        probabilities = self.pipeline.predict_proba([cleaned])[0]
        classes = self.pipeline.classes_

        scores = {cls_name: round(float(prob), 4) for cls_name, prob in zip(classes, probabilities)}
        best_mood = max(scores, key=scores.get)
        confidence = round(scores[best_mood], 2)

        return {
            "mood": best_mood,
            "confidence": confidence,
            "all_scores": scores,
        }


mood_service = MoodClassifierService()
