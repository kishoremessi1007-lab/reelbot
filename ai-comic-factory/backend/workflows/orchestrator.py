from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from backend.database.db import get_db, row_to_dict, rows_to_list
from backend.engines.art_engine.engine import ArtEngine
from backend.engines.character_engine.engine import CharacterEngine
from backend.engines.composition_engine.engine import CompositionEngine, QualityController
from backend.engines.continuity_engine.engine import ContinuityEngine
from backend.engines.publishing_engine.engine import PublishingEngine
from backend.engines.script_engine.engine import ScriptEngine
from backend.engines.story_engine.engine import StoryEngine

logger = logging.getLogger(__name__)


class ComicFactoryOrchestrator:
    """Coordinates Workflows A (New Series), B (Episode Production), C (Publishing), D (Continuation), E (Recovery)."""

    def __init__(self) -> None:
        self.story = StoryEngine()
        self.characters = CharacterEngine()
        self.continuity = ContinuityEngine()
        self.script = ScriptEngine(continuity=self.continuity)
        self.art = ArtEngine()
        self.composer = CompositionEngine()
        self.qc = QualityController()
        self.publisher = PublishingEngine(continuity=self.continuity)

    def _start_run(self, workflow_name: str, trigger_source: str, series_id: Optional[int] = None, episode_id: Optional[int] = None) -> int:
        with get_db() as conn:
            cur = conn.execute(
                """
                INSERT INTO automation_runs (workflow_name, trigger_source, status, series_id, episode_id)
                VALUES (?, ?, 'running', ?, ?)
                """,
                (workflow_name, trigger_source, series_id, episode_id),
            )
            return int(cur.lastrowid)

    def _finish_run(self, run_id: int, status: str, details: Dict[str, Any], error: Optional[str] = None) -> None:
        with get_db() as conn:
            conn.execute(
                """
                UPDATE automation_runs
                SET status = ?, details_json = ?, error_message = ?, finished_at = datetime('now')
                WHERE id = ?
                """,
                (status, json.dumps(details), error, run_id),
            )

    def run_new_series_workflow(
        self,
        trigger_source: str = "manual",
        forced_genre: Optional[str] = None,
        forced_style: Optional[str] = None,
        episode_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Workflow A: Select genre/style -> create series bible -> generate characters -> generate character reference sheets."""
        run_id = self._start_run("workflow_a_new_series", trigger_source)
        try:
            series = self.story.generate_new_series(
                forced_genre=forced_genre,
                forced_style=forced_style,
                episode_count=episode_count,
            )
            chars = self.characters.generate_characters_for_series(series)
            refs = self.art.generate_character_references(series, chars)
            result = {
                "series": series,
                "characters_count": len(chars),
                "references_count": len(refs),
            }
            self._finish_run(run_id, "completed", {"series_id": series["id"], "title": series["title"]})
            return result
        except Exception as exc:
            logger.exception("Workflow A failed")
            self._finish_run(run_id, "failed", {}, str(exc))
            raise

    def run_episode_production_workflow(
        self,
        series_id: Optional[int] = None,
        trigger_source: str = "manual",
        queue_for_publishing: bool = True,
    ) -> Dict[str, Any]:
        """Workflow B + C: Produce next episode for active series, run QC, and prepare publishing queue."""
        with get_db() as conn:
            if series_id is not None:
                series = row_to_dict(conn.execute("SELECT * FROM series WHERE id = ?", (series_id,)).fetchone())
            else:
                series = row_to_dict(
                    conn.execute("SELECT * FROM series WHERE status = 'active' ORDER BY id DESC LIMIT 1").fetchone()
                )

        if not series:
            created = self.run_new_series_workflow(trigger_source=trigger_source)
            series = created["series"]

        if series["current_episode"] >= series["total_episodes"]:
            self.continuity.check_and_complete_series(series["id"])
            created = self.run_new_series_workflow(trigger_source=trigger_source)
            series = created["series"]

        next_ep_num = int(series["current_episode"]) + 1
        run_id = self._start_run("workflow_b_episode_production", trigger_source, series_id=series["id"])

        try:
            episode = self.script.generate_episode_script(series["id"], next_ep_num)
            self.art.generate_episode_artwork(series, episode)
            composed = self.composer.compose_episode(series, episode)
            qc_passed, qc_report = self.qc.validate_episode(episode["id"])

            queued = None
            if qc_passed and queue_for_publishing:
                queued = self.publisher.prepare_episode_posts(series, episode)

            completed_series = self.continuity.check_and_complete_series(series["id"])
            result = {
                "series_id": series["id"],
                "episode_id": episode["id"],
                "episode_number": next_ep_num,
                "qc_passed": qc_passed,
                "qc_report": qc_report,
                "carousel_slides": len(composed["carousel_images"]),
                "individual_page": composed["individual_image"] is not None,
                "queued": queued,
                "series_completed": completed_series,
            }
            self._finish_run(run_id, "completed" if qc_passed else "failed", result, None if qc_passed else json.dumps(qc_report))
            return result
        except Exception as exc:
            logger.exception("Workflow B failed")
            self._finish_run(run_id, "failed", {"series_id": series["id"], "episode_number": next_ep_num}, str(exc))
            raise

    def run_due_publishing_workflow(self, trigger_source: str = "scheduler") -> Dict[str, Any]:
        """Workflow C: Publish due items in publishing_queue."""
        run_id = self._start_run("workflow_c_publishing", trigger_source)
        published: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        try:
            with get_db() as conn:
                due_items = rows_to_list(
                    conn.execute(
                        """
                        SELECT * FROM publishing_queue
                        WHERE status = 'pending' AND scheduled_for <= datetime('now')
                        ORDER BY scheduled_for ASC
                        """
                    ).fetchall()
                )

            for item in due_items:
                res = self.publisher.publish_queue_item(item["id"])
                if res.get("status") in ("published", "already_published"):
                    published.append({"queue_id": item["id"], **res})
                else:
                    failed.append({"queue_id": item["id"], **res})

            summary = {"checked": len(due_items), "published": published, "failed": failed}
            self._finish_run(run_id, "completed", summary)
            return summary
        except Exception as exc:
            self._finish_run(run_id, "failed", {}, str(exc))
            raise

    def run_continuation_workflow(self, trigger_source: str = "scheduler") -> Dict[str, Any]:
        """Workflow D: Check active series, complete if done, rotate to new series, produce next episode."""
        with get_db() as conn:
            active = row_to_dict(
                conn.execute("SELECT * FROM series WHERE status = 'active' ORDER BY id DESC LIMIT 1").fetchone()
            )
        if active and active["current_episode"] >= active["total_episodes"]:
            self.continuity.check_and_complete_series(active["id"])
            active = None

        if not active:
            self.run_new_series_workflow(trigger_source=trigger_source)

        return self.run_episode_production_workflow(trigger_source=trigger_source)
