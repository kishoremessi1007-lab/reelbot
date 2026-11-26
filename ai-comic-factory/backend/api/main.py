from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.config import settings
from backend.database.db import get_app_settings, get_db, init_db, row_to_dict, rows_to_list, update_app_settings
from backend.engines.publishing_engine.engine import PublishingEngine
from backend.engines.story_engine.engine import ART_STYLES
from backend.scheduler.manager import scheduler_manager
from backend.services.comfyui_client import ComfyUIClient
from backend.services.ollama_client import OllamaClient
from backend.workflows.orchestrator import ComicFactoryOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.generated_dir.mkdir(parents=True, exist_ok=True)
    scheduler_manager.start()
    yield
    scheduler_manager.shutdown()


app = FastAPI(
    title="AI Comic Factory API",
    description="Zero-cost autonomous AI comic production & Instagram publishing studio.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings.generated_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(settings.generated_dir)), name="media")

orchestrator = ComicFactoryOrchestrator()


class NewSeriesRequest(BaseModel):
    forced_genre: Optional[str] = None
    forced_style: Optional[str] = None
    episode_count: Optional[int] = None


class ProduceEpisodeRequest(BaseModel):
    series_id: Optional[int] = None
    queue_for_publishing: bool = True


class SettingsUpdateRequest(BaseModel):
    updates: Dict[str, Any]


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    ollama = OllamaClient()
    comfy = ComfyUIClient()
    pub = PublishingEngine()
    return {
        "status": "ok",
        "database": "sqlite_connected",
        "ollama": {"online": ollama.is_available(), "model": ollama.model, "models": ollama.list_models()},
        "comfyui": {"online": comfy.is_available(), "fallback_enabled": settings.comfyui_enable_fallback_renderer},
        "instagram": pub.check_token_health(),
        "scheduler": {
            "running": scheduler_manager.is_running(),
            "paused": bool(get_app_settings().get("scheduler_paused", False)),
        },
    }


@app.get("/api/dashboard/overview")
def dashboard_overview() -> Dict[str, Any]:
    with get_db() as conn:
        total_series = conn.execute("SELECT COUNT(*) AS c FROM series").fetchone()["c"]
        active_series = conn.execute("SELECT COUNT(*) AS c FROM series WHERE status = 'active'").fetchone()["c"]
        completed_series = conn.execute("SELECT COUNT(*) AS c FROM series WHERE status = 'completed'").fetchone()["c"]
        total_episodes = conn.execute("SELECT COUNT(*) AS c FROM episodes").fetchone()["c"]
        total_pages = conn.execute(
            "SELECT COUNT(*) AS c FROM generated_images WHERE image_role IN ('carousel_slide', 'individual_page')"
        ).fetchone()["c"]
        published_carousels = conn.execute(
            "SELECT COUNT(*) AS c FROM carousel_posts WHERE status = 'published'"
        ).fetchone()["c"]
        published_individuals = conn.execute(
            "SELECT COUNT(*) AS c FROM individual_posts WHERE status = 'published'"
        ).fetchone()["c"]
        failed_generations = conn.execute(
            "SELECT COUNT(*) AS c FROM episodes WHERE status IN ('qc_failed', 'failed')"
        ).fetchone()["c"]
        scheduled_posts = conn.execute(
            "SELECT COUNT(*) AS c FROM publishing_queue WHERE status = 'pending'"
        ).fetchone()["c"]
        failed_posts = conn.execute(
            "SELECT COUNT(*) AS c FROM publishing_queue WHERE status = 'failed'"
        ).fetchone()["c"]
        recent_runs = rows_to_list(
            conn.execute("SELECT * FROM automation_runs ORDER BY id DESC LIMIT 10").fetchall()
        )

    return {
        "total_series": total_series,
        "active_series": active_series,
        "completed_series": completed_series,
        "total_episodes": total_episodes,
        "total_generated_pages": total_pages,
        "published_carousel_posts": published_carousels,
        "published_individual_posts": published_individuals,
        "failed_generations": failed_generations,
        "scheduled_posts": scheduled_posts,
        "failed_posts": failed_posts,
        "scheduler_paused": bool(get_app_settings().get("scheduler_paused", False)),
        "recent_runs": recent_runs,
    }


@app.get("/api/series")
def list_series() -> List[Dict[str, Any]]:
    with get_db() as conn:
        return rows_to_list(conn.execute("SELECT * FROM series ORDER BY id DESC").fetchall())


@app.get("/api/series/{series_id}")
def get_series_detail(series_id: int) -> Dict[str, Any]:
    with get_db() as conn:
        series = row_to_dict(conn.execute("SELECT * FROM series WHERE id = ?", (series_id,)).fetchone())
        if not series:
            raise HTTPException(status_code=404, detail="Series not found")
        bible = row_to_dict(conn.execute("SELECT * FROM story_bibles WHERE series_id = ?", (series_id,)).fetchone())
        characters = rows_to_list(conn.execute("SELECT * FROM characters WHERE series_id = ? ORDER BY id", (series_id,)).fetchall())
        char_refs = rows_to_list(conn.execute("SELECT * FROM character_references WHERE series_id = ?", (series_id,)).fetchall())
        episodes = rows_to_list(conn.execute("SELECT * FROM episodes WHERE series_id = ? ORDER BY episode_number", (series_id,)).fetchall())
        continuity = row_to_dict(conn.execute("SELECT * FROM story_continuity WHERE series_id = ?", (series_id,)).fetchone())

    return {
        "series": series,
        "bible": bible,
        "characters": characters,
        "character_references": char_refs,
        "episodes": episodes,
        "continuity": continuity,
    }


@app.post("/api/series/generate")
def generate_new_series(req: NewSeriesRequest) -> Dict[str, Any]:
    return orchestrator.run_new_series_workflow(
        trigger_source="api",
        forced_genre=req.forced_genre,
        forced_style=req.forced_style,
        episode_count=req.episode_count,
    )


@app.post("/api/episodes/produce")
def produce_episode(req: ProduceEpisodeRequest) -> Dict[str, Any]:
    return orchestrator.run_episode_production_workflow(
        series_id=req.series_id,
        trigger_source="api",
        queue_for_publishing=req.queue_for_publishing,
    )


@app.get("/api/episodes/{episode_id}/script")
def get_episode_script(episode_id: int) -> Dict[str, Any]:
    with get_db() as conn:
        ep = row_to_dict(conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone())
        if not ep:
            raise HTTPException(status_code=404, detail="Episode not found")
        panels = rows_to_list(
            conn.execute("SELECT * FROM comic_panels WHERE episode_id = ? ORDER BY format_type, panel_order", (episode_id,)).fetchall()
        )
        images = rows_to_list(
            conn.execute("SELECT * FROM generated_images WHERE episode_id = ? ORDER BY image_role, slide_number", (episode_id,)).fetchall()
        )
    return {"episode": ep, "panels": panels, "images": images}


@app.get("/api/gallery")
def get_gallery(
    series_id: Optional[int] = Query(default=None),
    genre: Optional[str] = Query(default=None),
    image_role: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    query = """
        SELECT gi.*, s.title AS series_title, s.primary_genre, s.art_style, e.episode_number, e.title AS episode_title
        FROM generated_images gi
        JOIN series s ON s.id = gi.series_id
        LEFT JOIN episodes e ON e.id = gi.episode_id
        WHERE gi.image_role IN ('carousel_slide', 'individual_page', 'character_ref')
    """
    params: List[Any] = []
    if series_id is not None:
        query += " AND gi.series_id = ?"
        params.append(series_id)
    if genre:
        query += " AND s.primary_genre = ?"
        params.append(genre)
    if image_role:
        query += " AND gi.image_role = ?"
        params.append(image_role)
    query += " ORDER BY gi.id DESC LIMIT 120"

    with get_db() as conn:
        rows = rows_to_list(conn.execute(query, params).fetchall())

    for r in rows:
        try:
            rel = Path(r["file_path"]).resolve().relative_to(settings.generated_dir.resolve()).as_posix()
            r["media_url"] = f"/media/{rel}"
        except Exception:
            r["media_url"] = ""
    return rows


@app.get("/api/images/{image_id}/download")
def download_image(image_id: int):
    with get_db() as conn:
        img = row_to_dict(conn.execute("SELECT * FROM generated_images WHERE id = ?", (image_id,)).fetchone())
    if not img or not Path(img["file_path"]).exists():
        raise HTTPException(status_code=404, detail="Image not found")
    file_path = Path(img["file_path"])
    media_type = "image/jpeg" if file_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    return FileResponse(img["file_path"], filename=file_path.name, media_type=media_type)


@app.get("/api/publishing/queue")
def get_publishing_queue() -> List[Dict[str, Any]]:
    with get_db() as conn:
        return rows_to_list(
            conn.execute(
                """
                SELECT pq.*, s.title AS series_title, e.episode_number, e.title AS episode_title
                FROM publishing_queue pq
                JOIN series s ON s.id = pq.series_id
                JOIN episodes e ON e.id = pq.episode_id
                ORDER BY pq.id DESC LIMIT 100
                """
            ).fetchall()
        )


@app.get("/api/publishing/logs")
def get_publishing_logs() -> List[Dict[str, Any]]:
    with get_db() as conn:
        return rows_to_list(conn.execute("SELECT * FROM publishing_logs ORDER BY id DESC LIMIT 100").fetchall())


@app.post("/api/publishing/retry/{queue_id}")
def retry_queue_item(queue_id: int) -> Dict[str, Any]:
    with get_db() as conn:
        item = row_to_dict(conn.execute("SELECT * FROM publishing_queue WHERE id = ?", (queue_id,)).fetchone())
        if not item:
            raise HTTPException(status_code=404, detail="Queue item not found")
        conn.execute(
            "UPDATE publishing_queue SET status = 'pending', scheduled_for = datetime('now'), updated_at = datetime('now') WHERE id = ?",
            (queue_id,),
        )
    return orchestrator.publisher.publish_queue_item(queue_id)


@app.post("/api/publishing/publish-now/{queue_id}")
def publish_now(queue_id: int) -> Dict[str, Any]:
    return orchestrator.publisher.publish_queue_item(queue_id)


@app.post("/api/publishing/run-due")
def run_due_publishing() -> Dict[str, Any]:
    return orchestrator.run_due_publishing_workflow(trigger_source="api")


@app.post("/api/scheduler/pause")
def pause_scheduler() -> Dict[str, Any]:
    cfg = update_app_settings({"scheduler_paused": True})
    return {"scheduler_paused": cfg["scheduler_paused"]}


@app.post("/api/scheduler/resume")
def resume_scheduler() -> Dict[str, Any]:
    cfg = update_app_settings({"scheduler_paused": False})
    return {"scheduler_paused": cfg["scheduler_paused"]}


@app.get("/api/settings")
def get_settings_endpoint() -> Dict[str, Any]:
    return get_app_settings()


@app.put("/api/settings")
def update_settings_endpoint(req: SettingsUpdateRequest) -> Dict[str, Any]:
    return update_app_settings(req.updates)


@app.get("/api/genres")
def list_genres() -> List[Dict[str, Any]]:
    with get_db() as conn:
        return rows_to_list(conn.execute("SELECT * FROM genres ORDER BY name").fetchall())


@app.get("/api/art-styles")
def list_art_styles() -> List[str]:
    return ART_STYLES
