from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from backend.config import settings


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

DEFAULT_GENRES: List[Dict[str, Any]] = [
    {"name": "Fantasy", "description": "Magic systems, mythical realms, and epic quests.", "typical_styles": ["Cinematic fantasy illustration", "Premium anime", "Watercolour illustration"]},
    {"name": "Dark fantasy", "description": "Grim worlds, moral ambiguity, and cursed powers.", "typical_styles": ["Dark noir comic", "Cinematic fantasy illustration", "Japanese manga"]},
    {"name": "Romance", "description": "Emotional bonds, yearning, and heartfelt drama.", "typical_styles": ["Webtoon-inspired artwork", "Watercolour illustration", "Premium anime"]},
    {"name": "Horror", "description": "Supernatural dread, survival terror, and eerie atmospheres.", "typical_styles": ["Dark noir comic", "Japanese manga"]},
    {"name": "Psychological horror", "description": "Paranoia, unreliable perception, and creeping dread.", "typical_styles": ["Dark noir comic", "Semi-realistic graphic novel"]},
    {"name": "Mystery", "description": "Hidden truths, clues, and slow-burn revelations.", "typical_styles": ["Dark noir comic", "Western graphic novel", "Semi-realistic graphic novel"]},
    {"name": "Detective", "description": "Investigations, forensic puzzles, and clever deductions.", "typical_styles": ["Dark noir comic", "Western graphic novel"]},
    {"name": "Science fiction", "description": "Space, advanced tech, and speculative futures.", "typical_styles": ["Cyberpunk comic", "Semi-realistic graphic novel", "Western graphic novel"]},
    {"name": "Cyberpunk", "description": "Neon megacities, corporate control, and cybernetic rebels.", "typical_styles": ["Cyberpunk comic", "Premium anime"]},
    {"name": "Action", "description": "High-stakes combat, kinetic choreography, and adrenaline.", "typical_styles": ["Japanese manga", "Premium anime", "Western graphic novel"]},
    {"name": "Adventure", "description": "Exploration, uncharted territories, and discovery.", "typical_styles": ["Premium anime", "Cinematic fantasy illustration", "Cartoon comic"]},
    {"name": "Comedy", "description": "Witty banter, absurd situations, and expressive timing.", "typical_styles": ["Cartoon comic", "Webtoon-inspired artwork"]},
    {"name": "School life", "description": "Campus rivalries, friendships, and coming-of-age.", "typical_styles": ["Webtoon-inspired artwork", "Japanese manga", "Premium anime"]},
    {"name": "Historical fiction", "description": "Period detail, cultural intrigue, and bygone eras.", "typical_styles": ["Watercolour illustration", "Semi-realistic graphic novel"]},
    {"name": "Mythology", "description": "Gods, legends, prophecies, and ancient trials.", "typical_styles": ["Cinematic fantasy illustration", "Watercolour illustration"]},
    {"name": "Supernatural", "description": "Hidden spirits, occult phenomena, and uncanny powers.", "typical_styles": ["Japanese manga", "Premium anime", "Dark noir comic"]},
    {"name": "Crime", "description": "Underworld syndicates, heists, and gritty moral choices.", "typical_styles": ["Dark noir comic", "Western graphic novel"]},
    {"name": "Survival", "description": "Harsh environments, scarce resources, and endurance.", "typical_styles": ["Semi-realistic graphic novel", "Dark noir comic"]},
    {"name": "Post-apocalyptic", "description": "Ruined civilizations, scavengers, and fragile hope.", "typical_styles": ["Semi-realistic graphic novel", "Cyberpunk comic"]},
    {"name": "Drama", "description": "Intense interpersonal conflict and emotional stakes.", "typical_styles": ["Webtoon-inspired artwork", "Semi-realistic graphic novel"]},
    {"name": "Thriller", "description": "Ticking clocks, conspiracies, and relentless tension.", "typical_styles": ["Dark noir comic", "Western graphic novel"]},
    {"name": "Political intrigue", "description": "Faction schemes, diplomacy, and betrayal.", "typical_styles": ["Semi-realistic graphic novel", "Cinematic fantasy illustration"]},
    {"name": "Sports", "description": "Tournament arcs, teamwork, and fierce rivalry.", "typical_styles": ["Japanese manga", "Premium anime"]},
    {"name": "Slice of life", "description": "Quiet everyday moments, warmth, and subtle growth.", "typical_styles": ["Watercolour illustration", "Webtoon-inspired artwork", "Cartoon comic"]},
]

DEFAULT_APP_SETTINGS: Dict[str, Any] = {
    "budget_mode": "zero_cost",
    "content_format": "both",
    "art_style_mode": "mixed",
    "preferred_art_styles": [],
    "genre_mode": "auto_rotate",
    "preferred_genres": [],
    "default_series_length_min": 5,
    "default_series_length_max": 10,
    "default_carousel_slides": 6,
    "image_width": 1080,
    "image_height": 1350,
    "carousel_posts_per_day": 1,
    "individual_posts_per_day": 1,
    "carousel_publish_hour": 10,
    "individual_publish_hour": 18,
    "auto_publish": True,
    "require_story_approval": False,
    "scheduler_paused": False,
    "ollama_model": settings.ollama_model,
    "comfyui_checkpoint": settings.comfyui_checkpoint,
}


def get_db_path() -> Path:
    db_path = Path(settings.sqlite_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_db() as conn:
        conn.executescript(schema_sql)
        for genre in DEFAULT_GENRES:
            conn.execute(
                """
                INSERT OR IGNORE INTO genres (name, description, typical_styles)
                VALUES (?, ?, ?)
                """,
                (genre["name"], genre["description"], json.dumps(genre["typical_styles"])),
            )
        for key, value in DEFAULT_APP_SETTINGS.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO app_settings (key, value)
                VALUES (?, ?)
                """,
                (key, json.dumps(value)),
            )


def get_app_settings() -> Dict[str, Any]:
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    result = dict(DEFAULT_APP_SETTINGS)
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except json.JSONDecodeError:
            result[row["key"]] = row["value"]
    return result


def update_app_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    with get_db() as conn:
        for key, value in updates.items():
            conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, datetime('now'))
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = datetime('now')
                """,
                (key, json.dumps(value)),
            )
    return get_app_settings()


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(r) for r in rows]
