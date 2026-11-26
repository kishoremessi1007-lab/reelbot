from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from backend.config import settings
from backend.database.db import get_db, init_db
from backend.engines.publishing_engine.engine import PublishingEngine
from backend.workflows.orchestrator import ComicFactoryOrchestrator


@pytest.fixture()
def temp_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "test_comic_factory.db"
    gen_dir = tmp_path / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "sqlite_db_path", str(db_file))
    # Patch BASE_DIR / generated_dir via monkeypatch on Settings property if needed
    monkeypatch.setattr(type(settings), "generated_dir", property(lambda self: gen_dir))
    init_db()
    return tmp_path


def test_full_series_and_episode_production_and_qc(temp_env: Path):
    orch = ComicFactoryOrchestrator()
    # Force a 2-episode series to test continuity and series completion -> rotation
    res_series = orch.run_new_series_workflow(trigger_source="test", episode_count=2)
    series_id = res_series["series"]["id"]
    assert res_series["characters_count"] == 3
    assert res_series["references_count"] == 3

    # Produce Episode 1
    ep1 = orch.run_episode_production_workflow(series_id=series_id, trigger_source="test", queue_for_publishing=True)
    assert ep1["episode_number"] == 1
    assert ep1["qc_passed"] is True
    assert 5 <= ep1["carousel_slides"] <= 8
    assert ep1["individual_page"] is True
    assert ep1["series_completed"] is False

    # Verify 1080x1350 dimensions and distinct files
    with get_db() as conn:
        slides = conn.execute(
            "SELECT * FROM generated_images WHERE episode_id = ? AND image_role = 'carousel_slide' ORDER BY slide_number",
            (ep1["episode_id"],),
        ).fetchall()
        indiv = conn.execute(
            "SELECT * FROM generated_images WHERE episode_id = ? AND image_role = 'individual_page'",
            (ep1["episode_id"],),
        ).fetchone()
        assert len(slides) == ep1["carousel_slides"]
        assert indiv is not None
        for s in slides:
            with Image.open(s["file_path"]) as im:
                assert im.size == (1080, 1350)
        with Image.open(indiv["file_path"]) as im:
            assert im.size == (1080, 1350)
        # Ensure individual page is not a duplicate of any carousel slide
        assert indiv["checksum_sha256"] not in {s["checksum_sha256"] for s in slides}

    # Produce Episode 2 -> should complete the series
    ep2 = orch.run_episode_production_workflow(series_id=series_id, trigger_source="test", queue_for_publishing=True)
    assert ep2["episode_number"] == 2
    assert ep2["qc_passed"] is True
    assert ep2["series_completed"] is True

    # Verify story continuity updated
    with get_db() as conn:
        cont = conn.execute("SELECT * FROM story_continuity WHERE series_id = ?", (series_id,)).fetchone()
        assert cont["current_episode_number"] == 2
        assert cont["last_episode_summary"] != ""

    # Continuation workflow should automatically start a brand new series
    ep_next = orch.run_continuation_workflow(trigger_source="test")
    assert ep_next["series_id"] != series_id
    assert ep_next["episode_number"] == 1


def test_publishing_idempotency_and_mocked_instagram_api(temp_env: Path, monkeypatch: pytest.MonkeyPatch):
    orch = ComicFactoryOrchestrator()
    res = orch.run_new_series_workflow(trigger_source="test", episode_count=5)
    ep = orch.run_episode_production_workflow(series_id=res["series"]["id"], trigger_source="test", queue_for_publishing=True)
    assert ep["queued"] is not None

    # Preparing again should not create duplicate queue entries
    with get_db() as conn:
        series = dict(conn.execute("SELECT * FROM series WHERE id = ?", (res["series"]["id"],)).fetchone())
        episode = dict(conn.execute("SELECT * FROM episodes WHERE id = ?", (ep["episode_id"],)).fetchone())
    orch.publisher.prepare_episode_posts(series, episode)

    with get_db() as conn:
        q_rows = conn.execute("SELECT * FROM publishing_queue WHERE episode_id = ?", (ep["episode_id"],)).fetchall()
        assert len(q_rows) == 2  # 1 carousel + 1 individual

    # Mock Instagram Graph API & URL reachability
    monkeypatch.setattr(settings, "instagram_access_token", "fake-token")
    monkeypatch.setattr(settings, "instagram_account_id", "17841400000000000")

    pub = PublishingEngine()
    with patch.object(pub.media_host, "verify_public_url", return_value=True), \
         patch.object(pub, "_wait_for_container", return_value=None), \
         patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        def fake_post(url, data=None, **kwargs):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if url.endswith("/media_publish"):
                resp.json.return_value = {"id": "ig_published_999"}
            else:
                resp.json.return_value = {"id": "ig_container_123"}
            return resp

        mock_client.post.side_effect = fake_post

        indiv_q = next(dict(r) for r in q_rows if r["post_format"] == "individual")
        first_res = pub.publish_queue_item(indiv_q["id"])
        assert first_res["status"] == "published"
        assert first_res["instagram_media_id"] == "ig_published_999"

        # Second call must be idempotent and NOT re-publish
        second_res = pub.publish_queue_item(indiv_q["id"])
        assert second_res["status"] == "already_published"
        assert second_res["instagram_media_id"] == "ig_published_999"
