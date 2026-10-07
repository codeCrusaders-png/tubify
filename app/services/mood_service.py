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

# Comprehensive natural language corpus across 7 core musical vibes
TRAINING_DATA: List[Tuple[str, str]] = [
    # ☕ Chill
    ("peaceful relaxing calm mellow ambient lofi beats", "Chill"),
    ("lazy sunday afternoon sitting on porch drinking iced tea", "Chill"),
    ("rainy afternoon reading a book with warm coffee cozy", "Chill"),
    ("acoustic guitar soft gentle morning sunlight", "Chill"),
    ("unwinding after a long stressful day at work relaxing", "Chill"),
    ("breezy tranquil serene ocean waves floating slow", "Chill"),
    ("lofi hip hop to relax and fall asleep to peaceful", "Chill"),
    ("smooth slow quiet mellow atmosphere unwinding", "Chill"),
    ("something peaceful for a cozy rainy evening", "Chill"),
    ("soothing calming slow tempo acoustic indie chill", "Chill"),
    ("warm bath candle cozy blankets fireplace relaxing vibe", "Chill"),
    ("soft piano background music tranquil quiet calm", "Chill"),
    ("dreamy cloud floating daydreaming soft synths chill", "Chill"),
    ("coffee shop background murmur acoustic vibes mellow", "Chill"),
    ("chill vibes only low tempo relaxing rhythm", "Chill"),

    # 🌙 Late Night
    ("dark night drive midnight cruising empty highway neon", "Late Night"),
    ("2am thoughts insomnia late night moody vibes alone", "Late Night"),
    ("neon lights city skyline after hours synthesizer", "Late Night"),
    ("synthwave retrowave dark electro night music headlights", "Late Night"),
    ("after dark nocturnal moody mysterious atmosphere dark", "Late Night"),
    ("alone in my bedroom at midnight staring at the ceiling", "Late Night"),
    ("midnight ride through empty rainy city streets alone", "Late Night"),
    ("dark moody atmospheric synth bass late evening", "Late Night"),
    ("deep nocturnal bass synthwave cruising night time", "Late Night"),
    ("dark night drive through empty downtown streets", "Late Night"),
    ("driving alone under streetlights past midnight", "Late Night"),
    ("midnight insomnia 3am quiet city dark electro", "Late Night"),
    ("nocturnal urban city night vibes brooding", "Late Night"),
    ("shadowy neon aesthetic late night drive synth", "Late Night"),
    ("late night cruising dark thoughts retro electro", "Late Night"),

    # 🌧️ Sad
    ("heartbreak crying broken heart tears sorrow pain", "Sad"),
    ("melancholy depressing grieving feeling completely lonely", "Sad"),
    ("sad emotional acoustic ballad crying alone in the dark", "Sad"),
    ("missing you wishing you were still here grief emptiness", "Sad"),
    ("gloomy rainy day lost someone i loved deeply hurtful", "Sad"),
    ("painful memories heartbreak hurts so much inside ache", "Sad"),
    ("dark depressing lonely broken soul hopeless weeping", "Sad"),
    ("feeling helpless devastated mournful sorrow tearful", "Sad"),
    ("songs to cry to after a bad breakup heartbreak", "Sad"),
    ("melancholic slow guitar sad vocals aching loneliness", "Sad"),
    ("nobody loves me feeling down gloomy depressing thoughts", "Sad"),
    ("regret missing an ex tears weeping sadness", "Sad"),
    ("heavy heart grieving loss emotional crying ballad", "Sad"),
    ("sorrowful hopeless melancholy weeping in bed", "Sad"),
    ("depressed sad lonely empty cold rainy day", "Sad"),

    # 🕯️ Romantic
    ("love song date night romantic dinner candles sweet", "Romantic"),
    ("falling in love crush sweetheart romance devotion", "Romantic"),
    ("slow dance holding hands kissing tender affection", "Romantic"),
    ("sensual intimate tender passion lovers romantic evening", "Romantic"),
    ("candlelight anniversary wedding slow romance gentle", "Romantic"),
    ("sweet melody love ballad for my partner forever love", "Romantic"),
    ("butterflies in stomach romantic serenade acoustic love", "Romantic"),
    ("holding you close slow dancing in the living room", "Romantic"),
    ("falling deeply in love forever you and me romantic", "Romantic"),
    ("intimacy passionate love warmth tender caress lovers", "Romantic"),
    ("sunset walk on the beach holding hands romantic", "Romantic"),
    ("love of my life sweet cute romantic affection", "Romantic"),
    ("soulmate tender kiss slow romance melody", "Romantic"),
    ("honeymoon candlelight dinner sweet passionate", "Romantic"),

    # ⚡ Workout
    ("gym motivation heavy bass high energy pump up beast mode", "Workout"),
    ("cardio running fast tempo aggressive electronic phonk", "Workout"),
    ("lifting heavy weights fitness workout intense power", "Workout"),
    ("intense training boxing crossfit explosive energy bpm", "Workout"),
    ("running sprint uphill adrenaline rush high tempo hype", "Workout"),
    ("powerlifting hard techno aggressive hardstyle bass drop", "Workout"),
    ("push past limits workout hype track adrenaline gym", "Workout"),
    ("pre workout energy pump up the bass aggressive hype", "Workout"),
    ("heavy deadlifts squats bench press workout motivation", "Workout"),
    ("fast paced running treadmill sprint workout music", "Workout"),
    ("aggressive rap heavy electronic gym hype pump", "Workout"),
    ("explosive workout training session high bpm boost", "Workout"),
    ("fitness workout motivation sweat grind beast", "Workout"),

    # 📚 Focus
    ("study coding concentration deep work programming flow", "Focus"),
    ("reading background instrumental no lyrics uninterrupted", "Focus"),
    ("productivity flow state ambient focus binaural beats", "Focus"),
    ("working on projects writing essay study session quiet", "Focus"),
    ("deep concentration intellectual math science study grind", "Focus"),
    ("subtle instrumental beats for work and study session", "Focus"),
    ("minimalist ambient noise focus and learn deep attention", "Focus"),
    ("studying for finals exam prep focus concentration", "Focus"),
    ("software engineering coding deep focus uninterrupted", "Focus"),
    ("lofi study beats no vocals instrumental focus mode", "Focus"),
    ("brain power concentration reading productivity zone", "Focus"),
    ("ambient synth for deep analytical work and focus", "Focus"),
    ("laser focus distraction free studying work session", "Focus"),

    # 🚗 Driving
    ("road trip driving cruising with windows rolled down breeze", "Driving"),
    ("car stereo highway cruising fast lane sunny road drive", "Driving"),
    ("weekend drive with friends roadtrip playlist sunshine", "Driving"),
    ("scenic mountain road speed cruising music car radio", "Driving"),
    ("open road driving fast sports car radio sunglasses", "Driving"),
    ("summer road trip windows rolled down coastal highway", "Driving"),
    ("car vibes driving into the sunset highway cruise", "Driving"),
    ("singing along in the car road trip with friends", "Driving"),
    ("long highway drive gas station sunset convertible car", "Driving"),
    ("coastal road trip driving sunny afternoon breeze", "Driving"),
    ("driving fast on the interstate car bass sound system", "Driving"),
    ("winding country roads weekend road trip driving", "Driving"),
    ("car ride sunny afternoon good vibes cruising", "Driving"),
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
                ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")),
                ("clf", LogisticRegression(C=5.0, max_iter=300, random_state=42)),
            ]
        )
        self._train()

    def _train(self) -> None:
        """Train classifier with training dataset."""
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
