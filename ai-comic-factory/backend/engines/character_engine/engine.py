from __future__ import annotations

import json
import logging
import random
import uuid
from typing import Any, Dict, List, Optional

from backend.database.db import get_db, row_to_dict, rows_to_list
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class CharacterEngine:
    """Manages original character creation, visual tokens, and reference sheets."""

    def __init__(self, llm: Optional[OllamaClient] = None) -> None:
        self.llm = llm or OllamaClient()

    def generate_characters_for_series(self, series: Dict[str, Any], count: int = 3) -> List[Dict[str, Any]]:
        """Create protagonist, antagonist, and supporting cast for a series."""
        series_id = series["id"]
        with get_db() as conn:
            existing = rows_to_list(conn.execute("SELECT * FROM characters WHERE series_id = ?", (series_id,)).fetchall())
            if existing:
                return existing

        prompt = f"""
Create {count} completely original characters for the comic series "{series['title']}".
Genre: {series['primary_genre']} {f"+ {series['secondary_genre']}" if series.get('secondary_genre') else ""}
Art Style: {series['art_style']}
Concept: {series['concept']}
World: {series['world_setting']}
Central Conflict: {series['central_conflict']}

Include at least 1 protagonist, 1 antagonist, and 1 supporting character.
Make their visual appearance vivid, specific, and consistent (hairstyle, hair color, eye color, clothing, accessories, proportions).

Return ONLY valid JSON:
{{
  "characters": [
    {{
      "name": "Full Name",
      "role": "protagonist|antagonist|supporting",
      "age": "22",
      "gender": "Female/Male/Non-binary",
      "personality": "Personality traits",
      "physical_appearance": "Face, build, distinguishing marks",
      "hairstyle": "Exact hairstyle",
      "hair_color": "Exact hair color",
      "eye_color": "Exact eye color",
      "clothing": "Signature outfit that stays consistent",
      "accessories": "Signature accessories",
      "height_proportions": "Height and build",
      "background": "Backstory",
      "goals": "Primary motivation",
      "weaknesses": "Flaws and vulnerabilities",
      "abilities": "Skills or powers",
      "relationships": {{"Other Character": "Relationship dynamic"}},
      "character_development": "How they change across the series"
    }}
  ]
}}
""".strip()

        data = self.llm.generate_json(
            prompt=prompt,
            system_prompt="You are a character designer for serialized comics. Output valid JSON only.",
        )

        chars_raw = data.get("characters", []) if data else []
        if not chars_raw:
            chars_raw = self._fallback_characters(series)

        saved: List[Dict[str, Any]] = []
        with get_db() as conn:
            for idx, c in enumerate(chars_raw[:count]):
                role = str(c.get("role", "supporting")).lower()
                if role not in ("protagonist", "antagonist", "supporting"):
                    role = "protagonist" if idx == 0 else "antagonist" if idx == 1 else "supporting"

                char_uid = f"CHR-{series_id}-{uuid.uuid4().hex[:8].upper()}"
                seed = (series.get("seed", 42) + (idx + 1) * 137) % 2_000_000_000
                visual_token = (
                    f"{c.get('name', 'Hero')}, {c.get('age', '20s')} {c.get('gender', '')}, "
                    f"{c.get('hair_color', 'dark')} {c.get('hairstyle', 'short hair')}, "
                    f"{c.get('eye_color', 'amber')} eyes, wearing {c.get('clothing', 'signature coat')}, "
                    f"{c.get('accessories', '')}, {c.get('physical_appearance', '')}"
                ).strip(", ")

                cur = conn.execute(
                    """
                    INSERT INTO characters (
                        character_uid, series_id, name, role, age, gender, personality,
                        physical_appearance, hairstyle, hair_color, eye_color, clothing,
                        accessories, height_proportions, background, goals, weaknesses,
                        abilities, relationships_json, character_development,
                        visual_prompt_token, seed
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        char_uid,
                        series_id,
                        c.get("name", f"Character {idx+1}"),
                        role,
                        str(c.get("age", "24")),
                        str(c.get("gender", "Unknown")),
                        str(c.get("personality", "")),
                        str(c.get("physical_appearance", "")),
                        str(c.get("hairstyle", "")),
                        str(c.get("hair_color", "")),
                        str(c.get("eye_color", "")),
                        str(c.get("clothing", "")),
                        str(c.get("accessories", "")),
                        str(c.get("height_proportions", "")),
                        str(c.get("background", "")),
                        str(c.get("goals", "")),
                        str(c.get("weaknesses", "")),
                        str(c.get("abilities", "")),
                        json.dumps(c.get("relationships", {})),
                        str(c.get("character_development", "")),
                        visual_token,
                        seed,
                    ),
                )
                row = row_to_dict(conn.execute("SELECT * FROM characters WHERE id = ?", (cur.lastrowid,)).fetchone())
                if row:
                    saved.append(row)

        logger.info("Created %d characters for series #%s", len(saved), series_id)
        return saved

    @staticmethod
    def get_series_characters(series_id: int) -> List[Dict[str, Any]]:
        with get_db() as conn:
            return rows_to_list(conn.execute("SELECT * FROM characters WHERE series_id = ? ORDER BY id", (series_id,)).fetchall())

    @staticmethod
    def _fallback_characters(series: Dict[str, Any]) -> List[Dict[str, Any]]:
        first_names = ["Kael", "Sora", "Mina", "Dorian", "Vesper", "Ren", "Nadia", "Corvus"]
        last_names = ["Vane", "Kuroda", "Solis", "Mercer", "Harrow", "Takanashi", "bell", "Kestrel"]
        random.shuffle(first_names)
        random.shuffle(last_names)
        return [
            {
                "name": f"{first_names[0]} {last_names[0]}",
                "role": "protagonist",
                "age": "21",
                "gender": "Female",
                "personality": "Resourceful, observant, fiercely protective of forgotten people.",
                "physical_appearance": "Sharp jawline, faint scar across left eyebrow, athletic posture.",
                "hairstyle": "Layered shoulder-length bob with side-swept bangs",
                "hair_color": "Cobalt blue",
                "eye_color": "Amber gold",
                "clothing": "Tailored charcoal trench coat over a cream high-collar tunic and utility belt",
                "accessories": "Brass pocket chronometer and fingerless leather gloves",
                "height_proportions": "168 cm, lean agile build",
                "background": f"Raised in the lower tiers of {series['title']}'s world as a courier.",
                "goals": "Uncover the truth behind the vanished district and protect her mentor's legacy.",
                "weaknesses": "Overextends herself to save others; distrusts authority.",
                "abilities": "Photographic spatial memory and rooftop parkour.",
                "relationships": {f"{first_names[1]} {last_names[1]}": "Sworn rival"},
                "character_development": "Learns to rely on allies instead of carrying every burden alone.",
            },
            {
                "name": f"{first_names[1]} {last_names[1]}",
                "role": "antagonist",
                "age": "34",
                "gender": "Male",
                "personality": "Calculating, articulate, convinced that erasing painful history brings peace.",
                "physical_appearance": "Tall, composed, silver-rimmed monocle over right eye.",
                "hairstyle": "Slicked-back undercut",
                "hair_color": "Silver-white",
                "eye_color": "Ice grey",
                "clothing": "Crimson-lined obsidian high-collar cape over formal waistcoat",
                "accessories": "Obsidian signet ring and carved cane",
                "height_proportions": "186 cm, commanding slender frame",
                "background": "Former chief archivist who witnessed a catastrophe no one else remembers.",
                "goals": "Seal the central relic permanently, regardless of who gets erased.",
                "weaknesses": "Underestimates emotional bonds and refuses to admit past mistakes.",
                "abilities": "Master strategist with access to forbidden cipher tech.",
                "relationships": {f"{first_names[0]} {last_names[0]}": "Sees her as a dangerous anomaly"},
                "character_development": "Gradually realizes his cure is worse than the memory he fears.",
            },
            {
                "name": f"{first_names[2]} {last_names[2]}",
                "role": "supporting",
                "age": "26",
                "gender": "Non-binary",
                "personality": "Dry humor, loyal mechanic, calm under pressure.",
                "physical_appearance": "Warm bronze skin, smudge of ink near cheek, expressive eyes.",
                "hairstyle": "Curly undercut tied in a short topknot",
                "hair_color": "Chestnut brown",
                "eye_color": "Emerald green",
                "clothing": "Olive canvas work vest over rolled-sleeve indigo shirt",
                "accessories": "Brass goggles resting on forehead and tool satchel",
                "height_proportions": "174 cm, sturdy build",
                "background": "Independent tinkerer who repairs outlawed relics.",
                "goals": "Keep their workshop independent and decode the Meridian Key.",
                "weaknesses": "Stubbornly refuses to abandon broken machines or friends.",
                "abilities": "Reverse-engineers ancient mechanisms in minutes.",
                "relationships": {f"{first_names[0]} {last_names[0]}": "Trusted partner and confidant"},
                "character_development": "Steps from behind the workbench into the front lines.",
            },
        ]
