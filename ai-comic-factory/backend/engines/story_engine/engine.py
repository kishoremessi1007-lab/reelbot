from __future__ import annotations

import hashlib
import json
import logging
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.database.db import get_app_settings, get_db, row_to_dict, rows_to_list
from backend.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

ART_STYLES: List[str] = [
    "Premium anime",
    "Japanese manga",
    "Western graphic novel",
    "Dark noir comic",
    "Watercolour illustration",
    "Cartoon comic",
    "Cinematic fantasy illustration",
    "Cyberpunk comic",
    "Semi-realistic graphic novel",
    "Webtoon-inspired artwork",
]

STYLE_PALETTES: Dict[str, Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]] = {
    "Premium anime": ((20, 28, 54), (242, 108, 128), (245, 247, 255)),
    "Japanese manga": ((24, 24, 28), (210, 210, 215), (250, 250, 250)),
    "Western graphic novel": ((32, 24, 38), (229, 145, 42), (248, 242, 230)),
    "Dark noir comic": ((12, 13, 18), (185, 40, 52), (232, 232, 236)),
    "Watercolour illustration": ((46, 62, 78), (214, 152, 124), (252, 248, 240)),
    "Cartoon comic": ((38, 72, 145), (255, 205, 45), (255, 252, 244)),
    "Cinematic fantasy illustration": ((24, 34, 48), (218, 168, 78), (246, 242, 232)),
    "Cyberpunk comic": ((14, 12, 34), (0, 232, 210), (240, 248, 255)),
    "Semi-realistic graphic novel": ((28, 30, 36), (188, 122, 86), (244, 240, 235)),
    "Webtoon-inspired artwork": ((32, 42, 68), (118, 184, 255), (250, 252, 255)),
}


class StoryEngine:
    """Autonomous original story, genre rotation, and series bible engine."""

    def __init__(self, llm: Optional[OllamaClient] = None) -> None:
        self.llm = llm or OllamaClient()

    def select_genre_and_style(self) -> Tuple[str, Optional[str], str]:
        """Select an unused/least-recent genre (or combo) and matching art style."""
        app_cfg = get_app_settings()
        with get_db() as conn:
            all_genres = rows_to_list(
                conn.execute("SELECT name, typical_styles FROM genres WHERE enabled = 1").fetchall()
            )
            recent_history = rows_to_list(
                conn.execute(
                    "SELECT primary_genre, secondary_genre, art_style FROM genre_history ORDER BY id DESC LIMIT 12"
                ).fetchall()
            )

        preferred_genres = [g for g in app_cfg.get("preferred_genres", []) if g]
        candidate_genres = [g for g in all_genres if not preferred_genres or g["name"] in preferred_genres]
        if not candidate_genres:
            candidate_genres = all_genres

        used_primary = {r["primary_genre"] for r in recent_history[:6]}
        unused = [g for g in candidate_genres if g["name"] not in used_primary]
        pool = unused if unused else candidate_genres

        chosen = random.choice(pool)
        primary_genre = chosen["name"]

        # Occasionally combine with a second distinct genre (~35% chance)
        secondary_genre: Optional[str] = None
        if len(candidate_genres) > 1 and random.random() < 0.35:
            other_pool = [g["name"] for g in candidate_genres if g["name"] != primary_genre]
            if other_pool:
                secondary_genre = random.choice(other_pool)

        # Select art style matched to genre, avoiding repeating the very last style
        preferred_styles = [s for s in app_cfg.get("preferred_art_styles", []) if s in ART_STYLES]
        last_style = recent_history[0]["art_style"] if recent_history else None
        try:
            typical_styles = json.loads(chosen.get("typical_styles") or "[]")
        except json.JSONDecodeError:
            typical_styles = []

        style_pool = preferred_styles or [s for s in typical_styles if s in ART_STYLES] or ART_STYLES
        filtered_styles = [s for s in style_pool if s != last_style] or style_pool
        art_style = random.choice(filtered_styles)

        return primary_genre, secondary_genre, art_style

    def generate_new_series(
        self,
        forced_genre: Optional[str] = None,
        forced_style: Optional[str] = None,
        episode_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Invent a completely original series, create its bible, and initialize continuity."""
        app_cfg = get_app_settings()
        primary_genre, secondary_genre, art_style = self.select_genre_and_style()
        if forced_genre:
            primary_genre = forced_genre
        if forced_style and forced_style in ART_STYLES:
            art_style = forced_style

        min_ep = int(app_cfg.get("default_series_length_min", 5))
        max_ep = int(app_cfg.get("default_series_length_max", 10))
        total_episodes = episode_count or random.randint(min(min_ep, max_ep), max(min_ep, max_ep))

        with get_db() as conn:
            existing_rows = rows_to_list(conn.execute("SELECT title, concept FROM series ORDER BY id DESC LIMIT 20").fetchall())

        existing_summary = "; ".join(f"{r['title']}: {r['concept'][:80]}" for r in existing_rows) or "None"
        genre_label = f"{primary_genre} + {secondary_genre}" if secondary_genre else primary_genre

        prompt = f"""
Create a completely original comic series bible in JSON.
Genre: {genre_label}
Art Style: {art_style}
Episode Count: {total_episodes}
Previously generated series to AVOID repeating or resembling: {existing_summary}

Rules:
- Never copy existing anime, manga, movies, books, or comics.
- Invent fresh, memorable original characters, world rules, and central conflict.
- Divide the story into exactly {total_episodes} connected episodes with a clear beginning, middle, and ending.

Return ONLY valid JSON with this exact schema:
{{
  "title": "Series Title",
  "concept": "2-sentence high-concept pitch",
  "world_setting": "Detailed description of the world, era, and rules",
  "central_conflict": "The core conflict driving the series",
  "logline": "One-sentence hook",
  "beginning_arc": "Episodes 1-2 summary",
  "middle_arc": "Mid-series escalation summary",
  "ending_arc": "Climax and resolution summary",
  "world_rules": "Key rules/magic/tech constraints of this universe",
  "themes": "Core themes explored",
  "unresolved_mysteries": ["Mystery 1", "Mystery 2", "Mystery 3"],
  "episode_outlines": [
    {{
      "episode_number": 1,
      "title": "Episode Title",
      "summary": "What happens in this episode",
      "cliffhanger": "Ending hook leading to next episode"
    }}
  ]
}}
""".strip()

        data = self.llm.generate_json(
            prompt=prompt,
            system_prompt="You are an acclaimed original comic-book writer and worldbuilder. Always output valid JSON.",
        )

        if not data or not isinstance(data.get("episode_outlines"), list) or len(data["episode_outlines"]) < 1:
            data = self._fallback_series_bible(primary_genre, secondary_genre, art_style, total_episodes, existing_rows)

        # Normalize episode outlines to exact total_episodes
        outlines = data.get("episode_outlines", [])
        while len(outlines) < total_episodes:
            idx = len(outlines) + 1
            outlines.append(
                {
                    "episode_number": idx,
                    "title": f"Chapter {idx}: Turning Tide",
                    "summary": f"The stakes escalate in {data['title']} as hidden motives surface.",
                    "cliffhanger": "A sudden revelation changes who can be trusted.",
                }
            )
        outlines = outlines[:total_episodes]
        for idx, ep in enumerate(outlines, start=1):
            ep["episode_number"] = idx

        title = str(data.get("title") or f"Echoes of {primary_genre}").strip()
        slug = self._unique_slug(title)
        seed = int(hashlib.sha256(f"{slug}-{random.randint(1, 999999)}".encode()).hexdigest()[:8], 16) % 2_000_000_000

        with get_db() as conn:
            cur = conn.execute(
                """
                INSERT INTO series (
                    title, slug, primary_genre, secondary_genre, art_style,
                    concept, world_setting, central_conflict, total_episodes,
                    current_episode, status, seed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'active', ?)
                """,
                (
                    title,
                    slug,
                    primary_genre,
                    secondary_genre,
                    art_style,
                    data.get("concept", ""),
                    data.get("world_setting", ""),
                    data.get("central_conflict", ""),
                    total_episodes,
                    seed,
                ),
            )
            series_id = cur.lastrowid

            conn.execute(
                """
                INSERT INTO story_bibles (
                    series_id, logline, beginning_arc, middle_arc, ending_arc,
                    world_rules, themes, episode_outlines_json, unresolved_mysteries_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    series_id,
                    data.get("logline", data.get("concept", "")),
                    data.get("beginning_arc", ""),
                    data.get("middle_arc", ""),
                    data.get("ending_arc", ""),
                    data.get("world_rules", ""),
                    data.get("themes", ""),
                    json.dumps(outlines),
                    json.dumps(data.get("unresolved_mysteries", [])),
                ),
            )

            conn.execute(
                """
                INSERT INTO genre_history (series_id, primary_genre, secondary_genre, art_style)
                VALUES (?, ?, ?, ?)
                """,
                (series_id, primary_genre, secondary_genre, art_style),
            )

            conn.execute(
                """
                INSERT INTO story_continuity (
                    series_id, current_episode_number, last_episode_summary,
                    last_cliffhanger, unresolved_mysteries_json, character_states_json,
                    future_plot_hooks_json, published_post_ids_json
                )
                VALUES (?, 0, '', '', ?, '{}', ?, '[]')
                """,
                (
                    series_id,
                    json.dumps(data.get("unresolved_mysteries", [])),
                    json.dumps([ep.get("cliffhanger", "") for ep in outlines]),
                ),
            )

            series_row = row_to_dict(conn.execute("SELECT * FROM series WHERE id = ?", (series_id,)).fetchone())

        logger.info("Created new series #%s '%s' (%s | %s)", series_id, title, genre_label, art_style)
        return series_row or {}

    @staticmethod
    def _unique_slug(title: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "comic-series"
        with get_db() as conn:
            existing = conn.execute("SELECT COUNT(*) as cnt FROM series WHERE slug LIKE ?", (f"{base}%",)).fetchone()
            count = existing["cnt"] if existing else 0
        return base if count == 0 else f"{base}-{count + 1}"

    @staticmethod
    def _fallback_series_bible(
        primary_genre: str,
        secondary_genre: Optional[str],
        art_style: str,
        total_episodes: int,
        existing_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Deterministic original fallback when Ollama is offline."""
        nouns = ["Clockwork", "Glass", "Astral", "Velvet", "Obsidian", "Lantern", "Silver", "Cipher", "Crimson", "Sunken"]
        subjects = ["Archivist", "Meridian", "Tide", "Cartographer", "Signal", "Bell", "Covenant", "Harbor", "Echo", "Spire"]
        used_titles = {r["title"] for r in existing_rows}

        title = f"The {random.choice(nouns)} {random.choice(subjects)}"
        while title in used_titles:
            title = f"The {random.choice(nouns)} {random.choice(subjects)} {random.randint(2, 99)}"

        genre_desc = f"{primary_genre} and {secondary_genre}" if secondary_genre else primary_genre
        outlines = []
        for ep in range(1, total_episodes + 1):
            if ep == 1:
                summary = f"An ordinary courier uncovers a forbidden artifact that triggers the central {genre_desc.lower()} crisis."
                cliffhanger = "The artifact activates on its own, projecting a map to a place that should not exist."
            elif ep == total_episodes:
                summary = "All factions converge at the final threshold where the true cost of the mystery is revealed and resolved."
                cliffhanger = "Peace returns, though a distant beacon flickers once in the night."
            else:
                summary = f"Episode {ep} deepens the alliance and exposes a betrayal within the inner circle."
                cliffhanger = "A key ally vanishes, leaving behind a single coded warning."
            outlines.append(
                {
                    "episode_number": ep,
                    "title": f"Part {ep}: {'The Spark' if ep == 1 else 'Final Reckoning' if ep == total_episodes else f'Fracture {ep}'}",
                    "summary": summary,
                    "cliffhanger": cliffhanger,
                }
            )

        return {
            "title": title,
            "concept": f"In a {genre_desc.lower()} world rendered in {art_style}, a reluctant investigator races to stop an ancient mechanism from rewriting memory.",
            "world_setting": f"A vertical city built atop layered ruins where {primary_genre.lower()} forces shape daily survival.",
            "central_conflict": "Stopping a secretive syndicate from erasing the city's collective history.",
            "logline": f"When memories become currency, one outsider holds the key to {title}.",
            "beginning_arc": "Discovery of the anomaly and formation of an uneasy partnership.",
            "middle_arc": "Escalating pursuits, uncovered betrayals, and shifting loyalties.",
            "ending_arc": "Confrontation at the core spire and restoration of the truth.",
            "world_rules": "Every use of the forbidden relic leaves a visible luminous mark on the user.",
            "themes": "Memory, trust, and the courage to question consensus.",
            "unresolved_mysteries": [
                "Who originally forged the Meridian Key?",
                "Why did the Seventh District disappear ten years ago?",
                "What does the syndicate's leader truly remember?",
            ],
            "episode_outlines": outlines,
        }
