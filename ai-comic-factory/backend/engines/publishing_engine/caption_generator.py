from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from backend.services.ollama_client import OllamaClient

GENRE_HASHTAG_POOLS: Dict[str, List[str]] = {
    "Fantasy": ["#FantasyComics", "#MagicWorld", "#EpicFantasy", "#Worldbuilding"],
    "Dark fantasy": ["#DarkFantasy", "#Grimdark", "#CursedRealm", "#DarkArt"],
    "Romance": ["#RomanceComic", "#WebtoonRomance", "#LoveStory", "#Heartfelt"],
    "Horror": ["#HorrorComics", "#CreepyStories", "#DarkTales", "#ThrillerArt"],
    "Psychological horror": ["#PsychologicalHorror", "#MindBending", "#Eerie", "#Suspense"],
    "Mystery": ["#MysteryComic", "#Whodunit", "#HiddenTruth", "#PlotTwist"],
    "Detective": ["#DetectiveComic", "#NoirMystery", "#CrimeSolver", "#Clues"],
    "Science fiction": ["#SciFiComics", "#FutureWorld", "#SpeculativeFiction", "#SciFiArt"],
    "Cyberpunk": ["#CyberpunkArt", "#NeonNoir", "#CyberpunkComic", "#Dystopian"],
    "Action": ["#ActionComics", "#AnimeAction", "#FightScene", "#DynamicArt"],
    "Adventure": ["#AdventureComic", "#EpicJourney", "#Quest", "#Exploration"],
    "Comedy": ["#ComedyComic", "#FunnyComics", "#ComicStrip", "#Humor"],
    "School life": ["#SchoolLifeManga", "#SliceOfLife", "#CampusStory", "#Webtoon"],
    "Historical fiction": ["#HistoricalComic", "#PeriodDrama", "#HistoryArt", "#Storytelling"],
    "Mythology": ["#MythologyArt", "#Legends", "#GodsAndMortals", "#Mythic"],
    "Supernatural": ["#SupernaturalComic", "#Occult", "#Paranormal", "#SpiritWorld"],
    "Crime": ["#CrimeComic", "#Underworld", "#HeistStory", "#Noir"],
    "Survival": ["#SurvivalStory", "#HighStakes", "#Endurance", "#Thriller"],
    "Post-apocalyptic": ["#PostApocalyptic", "#Wasteland", "#Survivors", "#Ruins"],
    "Drama": ["#DramaComic", "#EmotionalStory", "#CharacterDriven", "#Webcomic"],
    "Thriller": ["#ThrillerComic", "#Suspense", "#EdgeOfYourSeat", "#Cliffhanger"],
    "Political intrigue": ["#PoliticalIntrigue", "#Conspiracy", "#PowerPlay", "#Drama"],
    "Sports": ["#SportsManga", "#Rivalry", "#TeamSpirit", "#TournamentArc"],
    "Slice of life": ["#SliceOfLife", "#CozyComics", "#EverydayMagic", "#IndieComics"],
}

BASE_HASHTAGS = [
    "#OriginalComics",
    "#IndieComic",
    "#AIComicStudio",
    "#DigitalComics",
    "#VisualStorytelling",
    "#ComicSeries",
    "#WebcomicSeries",
    "#InstaComics",
]


class CaptionGenerator:
    """Generates genre-matched Instagram captions, hooks, comment questions, and non-repeating hashtags."""

    def __init__(self, llm: Optional[OllamaClient] = None) -> None:
        self.llm = llm or OllamaClient()

    def generate(
        self,
        series: Dict[str, Any],
        episode: Dict[str, Any],
        post_format: str,
    ) -> Tuple[str, str]:
        """Return (full_caption, hashtags_string)."""
        ep_num = episode["episode_number"]
        total_eps = series["total_episodes"]
        genre = series["primary_genre"]

        genre_tags = list(GENRE_HASHTAG_POOLS.get(genre, ["#ComicArt", "#Storytelling"]))
        random.shuffle(genre_tags)
        base_sample = random.sample(BASE_HASHTAGS, k=4)
        hashtags = " ".join(dict.fromkeys(genre_tags[:3] + base_sample))

        is_final = ep_num >= total_eps
        teaser = (
            "Series Finale! A brand new original series begins tomorrow."
            if is_final
            else f"Episode {ep_num + 1:02d} coming soon."
        )

        prompt = f"""
Write an engaging Instagram caption for a comic post.
Series Title: {series['title']}
Genre: {genre}
Episode: {ep_num:02d} - {episode['title']}
Summary: {episode['summary']}
Cliffhanger: {episode['ending_cliffhanger']}
Format: {"Multi-slide comic episode (Carousel)" if post_format == "carousel" else "Standalone spotlight comic page"}
Teaser: {teaser}

Return ONLY valid JSON:
{{
  "hook": "1-2 punchy opening lines",
  "body": "1-2 engaging sentences without spoilers",
  "question": "1 engaging question for the comments"
}}
""".strip()

        data = self.llm.generate_json(prompt=prompt, system_prompt="You are an Instagram comic growth strategist. Output JSON only.")
        if not data:
            hook = f"{episode['ending_cliffhanger']}" if post_format == "carousel" else f"Inside the world of {series['title']}."
            body = episode["summary"]
            question = f"What do you think happens next in {series['title']}?"
        else:
            hook = str(data.get("hook") or f"New chapter of {series['title']} is here.")
            body = str(data.get("body") or episode["summary"])
            question = str(data.get("question") or "What would you do in this situation?")

        caption = (
            f"{hook}\n\n"
            f"{body}\n\n"
            f"{series['title'].upper()}\n"
            f"Episode {ep_num:02d}: {episode['title']}\n\n"
            f"{question}\n\n"
            f"{teaser}\n\n"
            f"{hashtags}"
        )
        return caption, hashtags
