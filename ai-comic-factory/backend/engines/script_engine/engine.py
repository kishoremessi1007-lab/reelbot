from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from backend.database.db import get_app_settings, get_db, row_to_dict
from backend.engines.continuity_engine.engine import ContinuityEngine
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class ScriptEngine:
    """Generates visual comic episode scripts for both Carousel and Individual Page formats."""

    def __init__(
        self,
        llm: Optional[OllamaClient] = None,
        continuity: Optional[ContinuityEngine] = None,
    ) -> None:
        self.llm = llm or OllamaClient()
        self.continuity = continuity or ContinuityEngine()

    def generate_episode_script(self, series_id: int, episode_number: int) -> Dict[str, Any]:
        app_cfg = get_app_settings()
        slide_count = max(5, min(8, int(app_cfg.get("default_carousel_slides", 6))))

        ctx = self.continuity.get_continuity(series_id)
        series = ctx["series"]
        bible = ctx["bible"]
        cont = ctx["continuity"]
        characters = ctx["characters"]

        with get_db() as conn:
            existing = row_to_dict(
                conn.execute(
                    "SELECT * FROM episodes WHERE series_id = ? AND episode_number = ?",
                    (series_id, episode_number),
                ).fetchone()
            )
            if existing:
                return existing

        try:
            outlines = json.loads(bible.get("episode_outlines_json") or "[]")
        except json.JSONDecodeError:
            outlines = []

        ep_outline = next((o for o in outlines if int(o.get("episode_number", 0)) == episode_number), None)
        if not ep_outline:
            ep_outline = {
                "episode_number": episode_number,
                "title": f"Episode {episode_number}",
                "summary": f"The story of {series['title']} advances to chapter {episode_number}.",
                "cliffhanger": "A new threat steps out of the shadows.",
            }

        prev_summary = cont.get("last_episode_summary") or "Series premiere."
        prev_cliffhanger = cont.get("last_cliffhanger") or "None."
        char_list = "\n".join(
            f"- {c['name']} ({c['role']}): {c['visual_prompt_token']}" for c in characters
        )

        prompt = f"""
Write a visual comic-book script for "{series['title']}" Episode {episode_number} of {series['total_episodes']}.
Episode Title: {ep_outline.get('title')}
Outline Summary: {ep_outline.get('summary')}
Previous Episode Summary: {prev_summary}
Previous Cliffhanger to resolve/continue: {prev_cliffhanger}
Art Style: {series['art_style']}
Characters:
{char_list}

Requirements:
1. Create exactly {slide_count} carousel slides (1080x1350 each).
   - Slide 1: High-impact visual hook.
   - Middle slides: Develop plot naturally with concise comic dialogue (max 15 words per bubble).
   - Slide {slide_count}: Dramatic cliffhanger creating anticipation for the next episode.
2. Create 1 SEPARATE standalone individual comic page (NOT a duplicate of any carousel slide) showing an iconic highlight, character moment, or dramatic reveal from this episode.

Return ONLY valid JSON:
{{
  "episode_title": "{ep_outline.get('title')}",
  "summary": "2-sentence summary of what happens in this episode",
  "emotional_beats": ["curiosity", "tension", "shock"],
  "ending_cliffhanger": "Cliffhanger line",
  "scenes": [
    {{
      "scene_number": 1,
      "location": "Location name",
      "time_of_day": "night",
      "mood": "tense",
      "description": "Scene setting"
    }}
  ],
  "carousel_slides": [
    {{
      "slide_number": 1,
      "scene_number": 1,
      "panel_description": "Visual composition of the panel",
      "character_positions": "Who stands where",
      "character_expressions": "Facial expressions",
      "camera_angle": "low-angle wide shot",
      "background_description": "Background details",
      "characters_present": ["Character Name"],
      "dialogue": [{{"speaker": "Character Name", "text": "Short punchy line."}}],
      "narration": "Optional short caption",
      "sound_effects": ["KRAAK"]
    }}
  ],
  "individual_page": {{
    "panel_description": "Distinct standalone dramatic illustration",
    "character_positions": "Center hero framing",
    "character_expressions": "Determined gaze",
    "camera_angle": "dramatic medium close-up",
    "background_description": "Atmospheric backdrop",
    "characters_present": ["Character Name"],
    "dialogue": [{{"speaker": "Character Name", "text": "Iconic standalone line."}}],
    "narration": "Episode spotlight caption",
    "sound_effects": []
  }}
}}
""".strip()

        data = self.llm.generate_json(
            prompt=prompt,
            system_prompt="You are a professional manga/comic scriptwriter. Keep dialogue short, visual, and punchy. Output valid JSON only.",
        )

        if not data or not isinstance(data.get("carousel_slides"), list) or len(data["carousel_slides"]) < 5:
            data = self._fallback_script(series, ep_outline, characters, slide_count, prev_cliffhanger)

        slides = data["carousel_slides"][:slide_count]
        while len(slides) < slide_count:
            idx = len(slides) + 1
            slides.append(
                {
                    "slide_number": idx,
                    "scene_number": 1,
                    "panel_description": f"Continuation beat {idx} in {ep_outline.get('title')}",
                    "character_positions": "Protagonist in foreground",
                    "character_expressions": "Focused and alert",
                    "camera_angle": "medium shot",
                    "background_description": series.get("world_setting", "Atmospheric city"),
                    "characters_present": [characters[0]["name"]] if characters else [],
                    "dialogue": [{"speaker": characters[0]["name"] if characters else "Narrator", "text": "We have no time left."}],
                    "narration": "",
                    "sound_effects": [],
                }
            )
        for idx, s in enumerate(slides, start=1):
            s["slide_number"] = idx

        indiv = data.get("individual_page") or self._fallback_individual_page(series, ep_outline, characters)

        ep_title = str(data.get("episode_title") or ep_outline.get("title") or f"Episode {episode_number}")
        ep_summary = str(data.get("summary") or ep_outline.get("summary") or "")
        cliffhanger = str(data.get("ending_cliffhanger") or ep_outline.get("cliffhanger") or "To be continued...")
        emotional_beats = data.get("emotional_beats") or ["intrigue", "conflict", "cliffhanger"]

        with get_db() as conn:
            cur = conn.execute(
                """
                INSERT INTO episodes (
                    series_id, episode_number, title, previous_summary, summary,
                    emotional_beats_json, ending_cliffhanger, script_json, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'scripted')
                """,
                (
                    series_id,
                    episode_number,
                    ep_title,
                    prev_summary,
                    ep_summary,
                    json.dumps(emotional_beats),
                    cliffhanger,
                    json.dumps(data),
                ),
            )
            episode_id = cur.lastrowid

            scene_id_map: Dict[int, int] = {}
            for sc in data.get("scenes") or [{"scene_number": 1, "location": "Main Setting", "time_of_day": "night", "mood": "dramatic", "description": ep_summary}]:
                sc_num = int(sc.get("scene_number", 1))
                sc_cur = conn.execute(
                    """
                    INSERT INTO scenes (episode_id, scene_number, location, time_of_day, mood, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        episode_id,
                        sc_num,
                        str(sc.get("location", "City")),
                        str(sc.get("time_of_day", "night")),
                        str(sc.get("mood", "dramatic")),
                        str(sc.get("description", "")),
                    ),
                )
                scene_id_map[sc_num] = sc_cur.lastrowid

            default_scene_id = next(iter(scene_id_map.values()), None)
            for s in slides:
                sc_id = scene_id_map.get(int(s.get("scene_number", 1)), default_scene_id)
                conn.execute(
                    """
                    INSERT INTO comic_panels (
                        episode_id, scene_id, panel_order, format_type, panel_description,
                        character_positions, character_expressions, camera_angle,
                        background_description, dialogue_json, narration,
                        sound_effects_json, characters_present_json
                    )
                    VALUES (?, ?, ?, 'carousel', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        episode_id,
                        sc_id,
                        int(s["slide_number"]),
                        str(s.get("panel_description", "")),
                        str(s.get("character_positions", "")),
                        str(s.get("character_expressions", "")),
                        str(s.get("camera_angle", "medium shot")),
                        str(s.get("background_description", "")),
                        json.dumps(s.get("dialogue", [])),
                        str(s.get("narration") or ""),
                        json.dumps(s.get("sound_effects", [])),
                        json.dumps(s.get("characters_present", [])),
                    ),
                )

            conn.execute(
                """
                INSERT INTO comic_panels (
                    episode_id, scene_id, panel_order, format_type, panel_description,
                    character_positions, character_expressions, camera_angle,
                    background_description, dialogue_json, narration,
                    sound_effects_json, characters_present_json
                )
                VALUES (?, ?, 1, 'individual', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode_id,
                    default_scene_id,
                    str(indiv.get("panel_description", "")),
                    str(indiv.get("character_positions", "")),
                    str(indiv.get("character_expressions", "")),
                    str(indiv.get("camera_angle", "dramatic close-up")),
                    str(indiv.get("background_description", "")),
                    json.dumps(indiv.get("dialogue", [])),
                    str(indiv.get("narration") or ""),
                    json.dumps(indiv.get("sound_effects", [])),
                    json.dumps(indiv.get("characters_present", [])),
                ),
            )

            episode_row = row_to_dict(conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone())

        self.continuity.update_after_episode(
            series_id=series_id,
            episode_number=episode_number,
            summary=ep_summary,
            cliffhanger=cliffhanger,
        )
        logger.info("Generated script for series #%s episode %d (%s)", series_id, episode_number, ep_title)
        return episode_row or {}

    @staticmethod
    def _fallback_individual_page(
        series: Dict[str, Any],
        ep_outline: Dict[str, Any],
        characters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        hero = characters[0]["name"] if characters else "Protagonist"
        return {
            "panel_description": f"Iconic standalone key-art scene from {series['title']}: {hero} standing at the edge of the threshold under dramatic lighting.",
            "character_positions": f"{hero} centered in dynamic three-quarter pose",
            "character_expressions": "Resolute, eyes catching the ambient glow",
            "camera_angle": "dramatic low-angle medium shot",
            "background_description": series.get("world_setting", "Atmospheric skyline"),
            "characters_present": [hero],
            "dialogue": [{"speaker": hero, "text": "Every secret leaves a trace."}],
            "narration": f"SPOTLIGHT: {ep_outline.get('title', 'New Chapter')}",
            "sound_effects": [],
        }

    def _fallback_script(
        self,
        series: Dict[str, Any],
        ep_outline: Dict[str, Any],
        characters: List[Dict[str, Any]],
        slide_count: int,
        prev_cliffhanger: str,
    ) -> Dict[str, Any]:
        hero = characters[0]["name"] if len(characters) > 0 else "Kael"
        rival = characters[1]["name"] if len(characters) > 1 else "Dorian"
        ally = characters[2]["name"] if len(characters) > 2 else "Mina"

        beats = [
            (
                f"Opening hook: {hero} confronts the aftermath of '{prev_cliffhanger}' atop a rain-slicked overlook.",
                "wide establishing shot",
                [{"speaker": hero, "text": "That signal wasn't meant for us to find."}],
                f"{series['title'].upper()} — {ep_outline.get('title', 'Episode')}",
                ["WHOOSH"],
                [hero],
            ),
            (
                f"{ally} examines the recovered clue under warm workshop lamps while sparks drift.",
                "over-the-shoulder close-up",
                [{"speaker": ally, "text": "Look at the cipher—it's counting down."}],
                "",
                [],
                [hero, ally],
            ),
            (
                f"Tension rises as {rival} steps into the corridor, flanked by long shadows.",
                "low-angle medium shot",
                [{"speaker": rival, "text": "Hand over the key before the city forgets you."}],
                "",
                ["CLANG"],
                [rival],
            ),
            (
                f"{hero} and {ally} evade the ambush across narrow neon-lit walkways.",
                "dynamic dutch angle",
                [{"speaker": hero, "text": "Left! Through the archive gate!"}],
                "No turning back now.",
                ["DASH"],
                [hero, ally],
            ),
            (
                f"Inside the sealed chamber, a glowing projection reveals the hidden truth.",
                "dramatic medium shot",
                [{"speaker": ally, "text": "Wait... those aren't ruins. That's a map."}],
                "",
                ["HUMMM"],
                [hero, ally],
            ),
            (
                f"Cliffhanger: {ep_outline.get('cliffhanger', 'A mysterious figure watches from above.')}",
                "extreme close-up",
                [{"speaker": hero, "text": "Who else knew this place existed?"}],
                "TO BE CONTINUED...",
                ["SHING"],
                [hero],
            ),
        ]

        slides: List[Dict[str, Any]] = []
        for idx in range(1, slide_count + 1):
            b = beats[min(idx - 1, len(beats) - 1)]
            slides.append(
                {
                    "slide_number": idx,
                    "scene_number": 1 if idx <= 3 else 2,
                    "panel_description": b[0],
                    "character_positions": "Foreground focal framing",
                    "character_expressions": "Expressive and intense",
                    "camera_angle": b[1],
                    "background_description": series.get("world_setting", "Detailed comic backdrop"),
                    "characters_present": b[5],
                    "dialogue": b[2],
                    "narration": b[3],
                    "sound_effects": b[4],
                }
            )

        return {
            "episode_title": ep_outline.get("title", "Chapter"),
            "summary": ep_outline.get("summary", ""),
            "emotional_beats": ["intrigue", "pursuit", "revelation", "cliffhanger"],
            "ending_cliffhanger": ep_outline.get("cliffhanger", "To be continued..."),
            "scenes": [
                {"scene_number": 1, "location": "Outer Overlook", "time_of_day": "night", "mood": "mysterious", "description": "Rain and neon reflections."},
                {"scene_number": 2, "location": "Sealed Archive", "time_of_day": "night", "mood": "tense", "description": "Ancient glowing chamber."},
            ],
            "carousel_slides": slides,
            "individual_page": self._fallback_individual_page(series, ep_outline, characters),
        }
