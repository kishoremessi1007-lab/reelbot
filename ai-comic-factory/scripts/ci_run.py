from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import get_db, init_db, row_to_dict
from backend.workflows.orchestrator import ComicFactoryOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ci_run")


def publish_next_of_format(orch: ComicFactoryOrchestrator, post_format: str) -> dict:
    with get_db() as conn:
        item = row_to_dict(
            conn.execute(
                """
                SELECT * FROM publishing_queue
                WHERE status = 'pending' AND post_format = ?
                ORDER BY id ASC LIMIT 1
                """,
                (post_format,),
            ).fetchone()
        )
    if not item:
        logger.info("No pending '%s' post found in publishing_queue.", post_format)
        return {"status": "no_pending_post", "post_format": post_format}
    return orch.publisher.publish_queue_item(item["id"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous AI Comic Factory CI Runner")
    parser.add_argument(
        "--mode",
        choices=["produce", "publish_carousel", "publish_individual", "publish_due"],
        required=True,
    )
    args = parser.parse_args()

    init_db()
    orch = ComicFactoryOrchestrator()

    if args.mode == "produce":
        res = orch.run_continuation_workflow(trigger_source="github_actions")
        print(json.dumps(res, indent=2))
        if not res.get("qc_passed"):
            sys.exit(1)
    elif args.mode == "publish_carousel":
        res = publish_next_of_format(orch, "carousel")
        print(json.dumps(res, indent=2))
        if res.get("status") == "failed":
            sys.exit(1)
    elif args.mode == "publish_individual":
        res = publish_next_of_format(orch, "individual")
        print(json.dumps(res, indent=2))
        if res.get("status") == "failed":
            sys.exit(1)
    elif args.mode == "publish_due":
        res = orch.run_due_publishing_workflow(trigger_source="github_actions")
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
