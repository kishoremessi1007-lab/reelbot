from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from backend.config import settings
from backend.database.db import get_app_settings, get_db, row_to_dict, rows_to_list
from backend.engines.continuity_engine.engine import ContinuityEngine
from backend.engines.publishing_engine.caption_generator import CaptionGenerator
from backend.storage.media_hosting import MediaHostingService

logger = logging.getLogger(__name__)


class PublishingEngine:
    """Official Instagram Graph API publisher with idempotency, retries, and logging."""

    def __init__(
        self,
        media_host: Optional[MediaHostingService] = None,
        caption_gen: Optional[CaptionGenerator] = None,
        continuity: Optional[ContinuityEngine] = None,
    ) -> None:
        self.media_host = media_host or MediaHostingService()
        self.caption_gen = caption_gen or CaptionGenerator()
        self.continuity = continuity or ContinuityEngine()

    @property
    def graph_base(self) -> str:
        return f"https://graph.facebook.com/{settings.instagram_graph_api_version}"

    def prepare_episode_posts(self, series: Dict[str, Any], episode: Dict[str, Any]) -> Dict[str, Any]:
        """Create carousel_posts, individual_posts, and idempotent publishing_queue entries."""
        series_id = series["id"]
        episode_id = episode["id"]
        app_cfg = get_app_settings()

        with get_db() as conn:
            carousel_imgs = rows_to_list(
                conn.execute(
                    "SELECT * FROM generated_images WHERE episode_id = ? AND image_role = 'carousel_slide' ORDER BY slide_number",
                    (episode_id,),
                ).fetchall()
            )
            indiv_img = row_to_dict(
                conn.execute(
                    "SELECT * FROM generated_images WHERE episode_id = ? AND image_role = 'individual_page' LIMIT 1",
                    (episode_id,),
                ).fetchone()
            )

        if not carousel_imgs or not indiv_img:
            raise RuntimeError(f"Episode #{episode_id} is missing composed carousel or individual images.")

        carousel_urls = [self.media_host.get_public_url(Path(img["file_path"])) for img in carousel_imgs]
        indiv_url = self.media_host.get_public_url(Path(indiv_img["file_path"]))

        with get_db() as conn:
            for img, url in zip(carousel_imgs, carousel_urls):
                conn.execute("UPDATE generated_images SET public_url = ? WHERE id = ?", (url, img["id"]))
            conn.execute("UPDATE generated_images SET public_url = ? WHERE id = ?", (indiv_url, indiv_img["id"]))

        carousel_caption, carousel_tags = self.caption_gen.generate(series, episode, "carousel")
        indiv_caption, indiv_tags = self.caption_gen.generate(series, episode, "individual")

        now = datetime.now(timezone.utc)
        c_hour = int(app_cfg.get("carousel_publish_hour", 10))
        i_hour = int(app_cfg.get("individual_publish_hour", 18))
        c_sched = now.replace(hour=c_hour, minute=0, second=0, microsecond=0)
        if c_sched < now:
            c_sched += timedelta(days=1)
        i_sched = c_sched.replace(hour=i_hour)
        if i_sched <= c_sched:
            i_sched += timedelta(hours=8)

        with get_db() as conn:
            # Carousel post
            existing_c = row_to_dict(conn.execute("SELECT * FROM carousel_posts WHERE episode_id = ?", (episode_id,)).fetchone())
            if existing_c:
                carousel_post_id = existing_c["id"]
            else:
                cur = conn.execute(
                    """
                    INSERT INTO carousel_posts (
                        series_id, episode_id, caption, hashtags, slide_image_ids_json, slide_urls_json, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'scheduled')
                    """,
                    (
                        series_id,
                        episode_id,
                        carousel_caption,
                        carousel_tags,
                        json.dumps([i["id"] for i in carousel_imgs]),
                        json.dumps(carousel_urls),
                    ),
                )
                carousel_post_id = cur.lastrowid

            # Individual post
            existing_i = row_to_dict(conn.execute("SELECT * FROM individual_posts WHERE episode_id = ?", (episode_id,)).fetchone())
            if existing_i:
                indiv_post_id = existing_i["id"]
            else:
                cur = conn.execute(
                    """
                    INSERT INTO individual_posts (
                        series_id, episode_id, caption, hashtags, image_id, public_url, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'scheduled')
                    """,
                    (
                        series_id,
                        episode_id,
                        indiv_caption,
                        indiv_tags,
                        indiv_img["id"],
                        indiv_url,
                    ),
                )
                indiv_post_id = cur.lastrowid

            # Idempotent queue entries
            conn.execute(
                """
                INSERT OR IGNORE INTO publishing_queue (
                    idempotency_key, series_id, episode_id, post_format, post_ref_id, scheduled_for, status
                )
                VALUES (?, ?, ?, 'carousel', ?, ?, 'pending')
                """,
                (f"series-{series_id}-ep-{episode_id}-carousel", series_id, episode_id, carousel_post_id, c_sched.isoformat()),
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO publishing_queue (
                    idempotency_key, series_id, episode_id, post_format, post_ref_id, scheduled_for, status
                )
                VALUES (?, ?, ?, 'individual', ?, ?, 'pending')
                """,
                (f"series-{series_id}-ep-{episode_id}-individual", series_id, episode_id, indiv_post_id, i_sched.isoformat()),
            )

        return {"carousel_post_id": carousel_post_id, "individual_post_id": indiv_post_id}

    def check_token_health(self) -> Dict[str, Any]:
        """Verify Instagram Graph API token validity and expiry if configured."""
        token = settings.resolved_instagram_access_token
        ig_id = settings.resolved_instagram_account_id
        if not token or not ig_id:
            return {"configured": False, "valid": False, "message": "Instagram credentials not configured in .env"}

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    f"{self.graph_base}/{ig_id}",
                    params={"fields": "id,username,account_type", "access_token": token},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    with get_db() as conn:
                        conn.execute(
                            """
                            INSERT INTO instagram_accounts (ig_user_id, username, account_type, last_token_check_at)
                            VALUES (?, ?, ?, datetime('now'))
                            ON CONFLICT(ig_user_id) DO UPDATE SET
                                username = excluded.username,
                                last_token_check_at = datetime('now')
                            """,
                            (data.get("id", ig_id), data.get("username", ""), data.get("account_type", "BUSINESS")),
                        )
                    return {"configured": True, "valid": True, "account": data}
                return {"configured": True, "valid": False, "message": resp.text}
        except Exception as exc:
            return {"configured": True, "valid": False, "message": str(exc)}

    def publish_queue_item(self, queue_id: int) -> Dict[str, Any]:
        """Publish a single queued item via the Official Instagram Graph API with idempotency."""
        with get_db() as conn:
            item = row_to_dict(conn.execute("SELECT * FROM publishing_queue WHERE id = ?", (queue_id,)).fetchone())
            if not item:
                raise ValueError(f"Queue item #{queue_id} not found")
            if item["status"] == "published" and item.get("instagram_media_id"):
                return {"status": "already_published", "instagram_media_id": item["instagram_media_id"]}

            conn.execute(
                "UPDATE publishing_queue SET status = 'processing', updated_at = datetime('now') WHERE id = ?",
                (queue_id,),
            )

        token = settings.resolved_instagram_access_token
        ig_id = settings.resolved_instagram_account_id
        if not token or not ig_id:
            err = "Instagram Graph API credentials missing (INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_ACCOUNT_ID)."
            self._mark_queue_failed(item, err)
            return {"status": "failed", "error": err}

        try:
            if item["post_format"] == "carousel":
                media_id = self._publish_carousel(item, ig_id, token)
            else:
                media_id = self._publish_individual(item, ig_id, token)

            with get_db() as conn:
                conn.execute(
                    """
                    UPDATE publishing_queue
                    SET status = 'published', instagram_media_id = ?, last_error = NULL, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (media_id, queue_id),
                )
                table = "carousel_posts" if item["post_format"] == "carousel" else "individual_posts"
                conn.execute(
                    f"""
                    UPDATE {table}
                    SET status = 'published', instagram_media_id = ?, published_at = datetime('now')
                    WHERE id = ?
                    """,
                    (media_id, item["post_ref_id"]),
                )
                self._log_action(conn, item, "publish", "success", 200, {"id": media_id}, None)

            self.continuity.record_published_post(item["series_id"], media_id)
            return {"status": "published", "instagram_media_id": media_id}
        except Exception as exc:
            self._mark_queue_failed(item, str(exc))
            return {"status": "failed", "error": str(exc)}

    @staticmethod
    def _post_graph(client: httpx.Client, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        resp = client.post(url, data=data)
        if resp.status_code >= 400:
            raise RuntimeError(f"Instagram Graph API {resp.status_code} on {url}: {resp.text}")
        return resp.json()

    def _publish_carousel(self, item: Dict[str, Any], ig_id: str, token: str) -> str:
        with get_db() as conn:
            post = row_to_dict(conn.execute("SELECT * FROM carousel_posts WHERE id = ?", (item["post_ref_id"],)).fetchone())
        if not post:
            raise RuntimeError("Carousel post record not found")

        urls: List[str] = json.loads(post["slide_urls_json"] or "[]")
        if len(urls) < 2:
            raise RuntimeError("Carousel requires at least 2 slide URLs")

        child_ids: List[str] = []
        with httpx.Client(timeout=30.0) as client:
            for url in urls:
                if not self.media_host.verify_public_url(url):
                    raise RuntimeError(f"Slide URL is not publicly reachable: {url}")
                child_data = self._post_graph(
                    client,
                    f"{self.graph_base}/{ig_id}/media",
                    {"image_url": url, "is_carousel_item": "true", "access_token": token},
                )
                child_id = child_data["id"]
                self._wait_for_container(client, child_id, token)
                child_ids.append(child_id)

            parent_data = self._post_graph(
                client,
                f"{self.graph_base}/{ig_id}/media",
                {
                    "media_type": "CAROUSEL",
                    "children": ",".join(child_ids),
                    "caption": post["caption"],
                    "access_token": token,
                },
            )
            parent_id = parent_data["id"]
            self._wait_for_container(client, parent_id, token)

            pub_data = self._post_graph(
                client,
                f"{self.graph_base}/{ig_id}/media_publish",
                {"creation_id": parent_id, "access_token": token},
            )
            return pub_data["id"]

    def _publish_individual(self, item: Dict[str, Any], ig_id: str, token: str) -> str:
        with get_db() as conn:
            post = row_to_dict(conn.execute("SELECT * FROM individual_posts WHERE id = ?", (item["post_ref_id"],)).fetchone())
        if not post:
            raise RuntimeError("Individual post record not found")

        url = post["public_url"]
        if not url or not self.media_host.verify_public_url(url):
            raise RuntimeError(f"Individual page URL is not publicly reachable: {url}")

        with httpx.Client(timeout=30.0) as client:
            cont_data = self._post_graph(
                client,
                f"{self.graph_base}/{ig_id}/media",
                {"image_url": url, "caption": post["caption"], "access_token": token},
            )
            container_id = cont_data["id"]
            self._wait_for_container(client, container_id, token)

            pub_data = self._post_graph(
                client,
                f"{self.graph_base}/{ig_id}/media_publish",
                {"creation_id": container_id, "access_token": token},
            )
            return pub_data["id"]

    def _wait_for_container(self, client: httpx.Client, container_id: str, token: str, timeout: int = 60) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = client.get(
                f"{self.graph_base}/{container_id}",
                params={"fields": "status_code,status", "access_token": token},
            )
            if resp.status_code == 200:
                status_code = resp.json().get("status_code")
                if status_code == "FINISHED":
                    return
                if status_code == "ERROR":
                    raise RuntimeError(f"Instagram container {container_id} failed: {resp.json()}")
            time.sleep(2.0)
        raise TimeoutError(f"Timed out waiting for Instagram container {container_id}")

    def _mark_queue_failed(self, item: Dict[str, Any], error_msg: str) -> None:
        retry_count = int(item.get("retry_count", 0)) + 1
        max_retries = int(item.get("max_retries", 3))
        new_status = "pending" if retry_count < max_retries else "failed"
        backoff_minutes = 5 * (2 ** (retry_count - 1))
        next_try = (datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)).isoformat()

        with get_db() as conn:
            conn.execute(
                """
                UPDATE publishing_queue
                SET status = ?, retry_count = ?, last_error = ?, scheduled_for = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (new_status, retry_count, error_msg, next_try if new_status == "pending" else item["scheduled_for"], item["id"]),
            )
            table = "carousel_posts" if item["post_format"] == "carousel" else "individual_posts"
            conn.execute(f"UPDATE {table} SET status = 'failed' WHERE id = ?", (item["post_ref_id"],))
            self._log_action(conn, item, "publish", "failed", None, None, error_msg)

    @staticmethod
    def _log_action(
        conn: Any,
        item: Dict[str, Any],
        action: str,
        status: str,
        http_status: Optional[int],
        response_payload: Optional[Dict[str, Any]],
        error_message: Optional[str],
    ) -> None:
        conn.execute(
            """
            INSERT INTO publishing_logs (
                queue_id, series_id, episode_id, post_format, action, status,
                http_status, response_payload, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["series_id"],
                item["episode_id"],
                item["post_format"],
                action,
                status,
                http_status,
                json.dumps(response_payload) if response_payload else None,
                error_message,
            ),
        )
