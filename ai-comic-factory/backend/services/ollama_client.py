from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

from backend.config import settings
from backend.database.db import get_app_settings

logger = logging.getLogger(__name__)


class OllamaClient:
    """Local Ollama LLM client with optional Gemini free-tier mode for headless GitHub Actions."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._explicit_model = model

    @property
    def model(self) -> str:
        if self._explicit_model:
            return self._explicit_model
        app_cfg = get_app_settings()
        return str(app_cfg.get("ollama_model") or settings.ollama_model)

    def is_available(self) -> bool:
        if settings.llm_provider.lower() == "gemini" and settings.gemini_api_key:
            return True
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception as exc:
            logger.debug("Ollama list_models failed: %s", exc)
        return []

    def generate_json(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.8,
        max_retries: int = 2,
    ) -> Optional[Dict[str, Any]]:
        """Generate structured JSON using Ollama (default) or Gemini when LLM_PROVIDER=gemini."""
        if settings.llm_provider.lower() == "gemini" and settings.gemini_api_key:
            result = self._generate_json_gemini(prompt, system_prompt, temperature, max_retries)
            if result is not None:
                return result

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=float(settings.ollama_timeout_seconds)) as client:
                    resp = client.post(f"{self.base_url}/api/generate", json=payload)
                    resp.raise_for_status()
                    raw_text = resp.json().get("response", "").strip()
                    parsed = self._extract_json(raw_text)
                    if parsed is not None:
                        return parsed
                    logger.warning("Ollama returned non-JSON on attempt %d", attempt + 1)
            except Exception as exc:
                logger.warning("Ollama request failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)
        return None

    def _generate_json_gemini(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_retries: int,
    ) -> Optional[Dict[str, Any]]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
        full_prompt = f"{system_prompt}\n\n{prompt}".strip() if system_prompt else prompt
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(url, params={"key": settings.gemini_api_key}, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    raw_text = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    parsed = self._extract_json(raw_text)
                    if parsed is not None:
                        return parsed
            except Exception as exc:
                logger.warning("Gemini request failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)
        return None

    @staticmethod
    def _extract_json(raw_text: str) -> Optional[Dict[str, Any]]:
        if not raw_text:
            return None
        try:
            obj = json.loads(raw_text)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", raw_text)
        if match:
            try:
                obj = json.loads(match.group(0))
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                return None
        return None
