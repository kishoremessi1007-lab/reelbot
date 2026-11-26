from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from backend.database.db import get_db, row_to_dict, rows_to_list

logger = logging.getLogger(__name__)


class ContinuityEngine:
    """Maintains persistent story memory across episodes and series."""

    def get_continuity(self, series_id: int) -> Dict[str, Any]:
        with get_db() as conn:
            cont = row_to_dict(
                conn.execute("SELECT * FROM story_continuity WHERE series_id = ?", (series_id,)).fetchone()
            )
            bible = row_to_dict(
                conn.execute("SELECT * FROM story_bibles WHERE series_id = ?", (series_id,)).fetchone()
            )
            series = row_to_dict(
                conn.execute("SELECT * FROM series WHERE id = ?", (series_id,)).fetchone()
            )
            episodes = rows_to_list(
                conn.execute(
                    "SELECT episode_number, title, summary, ending_cliffhanger, status FROM episodes WHERE series_id = ? ORDER BY episode_number",
                    (series_id,),
                ).fetchall()
            )
            characters = rows_to_list(
                conn.execute("SELECT id, character_uid, name, role, visual_prompt_token FROM characters WHERE series_id = ?", (series_id,)).fetchall()
            )

        return {
            "series": series or {},
            "bible": bible or {},
            "continuity": cont or {},
            "previous_episodes": episodes,
            "characters": characters,
        }

    def update_after_episode(
        self,
        series_id: int,
        episode_number: int,
        summary: str,
        cliffhanger: str,
        unresolved_mysteries: Optional[List[str]] = None,
    ) -> None:
        with get_db() as conn:
            conn.execute(
                """
                UPDATE story_continuity
                SET current_episode_number = ?,
                    last_episode_summary = ?,
                    last_cliffhanger = ?,
                    unresolved_mysteries_json = COALESCE(?, unresolved_mysteries_json),
                    updated_at = datetime('now')
                WHERE series_id = ?
                """,
                (
                    episode_number,
                    summary,
                    cliffhanger,
                    json.dumps(unresolved_mysteries) if unresolved_mysteries is not None else None,
                    series_id,
                ),
            )
            conn.execute(
                """
                UPDATE series
                SET current_episode = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (episode_number, series_id),
            )

    def record_published_post(self, series_id: int, instagram_media_id: str) -> None:
        if not instagram_media_id:
            return
        with get_db() as conn:
            row = conn.execute(
                "SELECT published_post_ids_json FROM story_continuity WHERE series_id = ?",
                (series_id,),
            ).fetchone()
            if not row:
                return
            try:
                ids = json.loads(row["published_post_ids_json"] or "[]")
            except json.JSONDecodeError:
                ids = []
            if instagram_media_id not in ids:
                ids.append(instagram_media_id)
            conn.execute(
                """
                UPDATE story_continuity
                SET published_post_ids_json = ?, updated_at = datetime('now')
                WHERE series_id = ?
                """,
                (json.dumps(ids), series_id),
            )

    def check_and_complete_series(self, series_id: int) -> bool:
        """Mark series completed if current_episode >= total_episodes."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT current_episode, total_episodes, status FROM series WHERE id = ?",
                (series_id,),
            ).fetchone()
            if not row:
                return False
            if row["current_episode"] >= row["total_episodes"] and row["status"] != "completed":
                conn.execute(
                    """
                    UPDATE series
                    SET status = 'completed', completed_at = datetime('now'), updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (series_id,),
                )
                logger.info("Series #%s marked as COMPLETED (%d/%d episodes).", series_id, row["current_episode"], row["total_episodes"])
                return True
            return row["status"] == "completed"
