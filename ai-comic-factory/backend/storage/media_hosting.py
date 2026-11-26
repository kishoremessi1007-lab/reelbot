from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import boto3
import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class MediaHostingService:
    """Zero-cost media hosting abstraction: local, Cloudflare Tunnel, or Cloudflare R2."""

    def get_public_url(self, local_path: Path) -> str:
        provider = settings.media_hosting_provider.lower().strip()
        rel_path = self._relative_generated_path(local_path)

        if provider == "github_raw" and settings.github_repository:
            import os
            branch = settings.github_branch or "main"
            gh_ws = os.environ.get("GITHUB_WORKSPACE")
            if gh_ws:
                try:
                    repo_rel = settings.generated_dir.resolve().relative_to(Path(gh_ws).resolve()).as_posix()
                    return f"https://raw.githubusercontent.com/{settings.github_repository}/{branch}/{repo_rel}/{rel_path}"
                except ValueError:
                    pass
            return f"https://raw.githubusercontent.com/{settings.github_repository}/{branch}/generated/{rel_path}"

        if provider == "cloudflare_r2" and settings.r2_account_id and settings.r2_access_key_id and settings.r2_secret_access_key:
            return self._upload_to_r2(local_path, rel_path)

        if provider == "local_tunnel" and settings.cloudflare_tunnel_url:
            base = settings.cloudflare_tunnel_url.rstrip("/")
            return f"{base}/media/{rel_path}"

        base = settings.public_base_url.rstrip("/")
        return f"{base}/media/{rel_path}"

    @staticmethod
    def _relative_generated_path(local_path: Path) -> str:
        try:
            rel = local_path.resolve().relative_to(settings.generated_dir.resolve())
            return rel.as_posix()
        except ValueError:
            return local_path.name

    @staticmethod
    def _upload_to_r2(local_path: Path, object_key: str) -> str:
        endpoint = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
        client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )
        content_type = "image/png" if local_path.suffix.lower() == ".png" else "image/jpeg"
        client.upload_file(
            str(local_path),
            settings.r2_bucket_name,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )
        public_base = settings.r2_public_url.rstrip("/")
        if not public_base:
            raise RuntimeError("R2_PUBLIC_URL must be set when using cloudflare_r2")
        return f"{public_base}/{object_key}"

    @staticmethod
    def verify_public_url(url: str) -> bool:
        if not url.startswith(("http://", "https://")):
            return False
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.head(url, follow_redirects=True)
                if resp.status_code == 200:
                    return True
                resp_get = client.get(url, follow_redirects=True)
                return resp_get.status_code == 200
        except Exception as exc:
            logger.warning("Public URL check failed for %s: %s", url, exc)
            return False
