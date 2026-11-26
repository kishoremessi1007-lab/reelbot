from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from backend.config import settings
from backend.database.db import get_app_settings

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Zero-cost local ComfyUI REST API client with workflow template injection."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or settings.comfyui_base_url).rstrip("/")
        self.client_id = uuid.uuid4().hex

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/system_stats")
                return resp.status_code == 200
        except Exception:
            return False

    def upload_image(self, image_path: Path) -> Optional[str]:
        """Upload a character reference image to ComfyUI input folder."""
        if not image_path.exists():
            return None
        try:
            with httpx.Client(timeout=30.0) as client:
                with open(image_path, "rb") as f:
                    files = {"image": (image_path.name, f, "image/png")}
                    resp = client.post(f"{self.base_url}/upload/image", files=files)
                    resp.raise_for_status()
                    return resp.json().get("name")
        except Exception as exc:
            logger.warning("ComfyUI image upload failed: %s", exc)
            return None

    def generate_image(
        self,
        workflow_name: str,
        positive_prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        output_path: Path,
        reference_image_name: Optional[str] = None,
        timeout_seconds: int = 180,
    ) -> bool:
        """Queue a ComfyUI workflow prompt, wait for completion, and save output image."""
        workflow_path = settings.comfyui_workflows_dir / f"{workflow_name}.json"
        if not workflow_path.exists():
            logger.error("ComfyUI workflow template not found: %s", workflow_path)
            return False

        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        app_cfg = get_app_settings()
        checkpoint = str(app_cfg.get("comfyui_checkpoint") or settings.comfyui_checkpoint)

        self._inject_workflow_params(
            workflow=workflow,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            seed=seed,
            width=width,
            height=height,
            checkpoint=checkpoint,
            reference_image_name=reference_image_name,
        )

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{self.base_url}/prompt",
                    json={"prompt": workflow, "client_id": self.client_id},
                )
                resp.raise_for_status()
                prompt_id = resp.json()["prompt_id"]

            deadline = time.time() + timeout_seconds
            while time.time() < deadline:
                with httpx.Client(timeout=15.0) as client:
                    hist_resp = client.get(f"{self.base_url}/history/{prompt_id}")
                    if hist_resp.status_code == 200:
                        hist = hist_resp.json()
                        if prompt_id in hist:
                            outputs = hist[prompt_id].get("outputs", {})
                            for node_out in outputs.values():
                                images = node_out.get("images", [])
                                if images:
                                    img_info = images[0]
                                    img_resp = client.get(
                                        f"{self.base_url}/view",
                                        params={
                                            "filename": img_info["filename"],
                                            "subfolder": img_info.get("subfolder", ""),
                                            "type": img_info.get("type", "output"),
                                        },
                                    )
                                    img_resp.raise_for_status()
                                    output_path.parent.mkdir(parents=True, exist_ok=True)
                                    output_path.write_bytes(img_resp.content)
                                    return True
                time.sleep(1.5)
            logger.warning("ComfyUI timed out waiting for prompt_id=%s", prompt_id)
            return False
        except Exception as exc:
            logger.warning("ComfyUI generation failed: %s", exc)
            return False

    @staticmethod
    def _inject_workflow_params(
        workflow: Dict[str, Any],
        positive_prompt: str,
        negative_prompt: str,
        seed: int,
        width: int,
        height: int,
        checkpoint: str,
        reference_image_name: Optional[str],
    ) -> None:
        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            class_type = node.get("class_type", "")
            inputs = node.get("inputs", {})
            meta_title = (node.get("_meta") or {}).get("title", "").lower()

            if class_type == "CheckpointLoaderSimple":
                inputs["ckpt_name"] = checkpoint
            elif class_type == "CLIPTextEncode":
                if "negative" in meta_title:
                    inputs["text"] = negative_prompt
                else:
                    inputs["text"] = positive_prompt
            elif class_type == "EmptyLatentImage":
                inputs["width"] = width
                inputs["height"] = height
            elif class_type == "KSampler":
                inputs["seed"] = seed
                inputs["steps"] = settings.comfyui_steps
                inputs["cfg"] = settings.comfyui_cfg
            elif class_type == "LoadImage" and reference_image_name:
                inputs["image"] = reference_image_name
