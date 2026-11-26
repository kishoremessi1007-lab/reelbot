from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import os
import random
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image, ImageDraw, ImageFilter

from backend.config import settings
from backend.database.db import get_db, rows_to_list
from backend.engines.story_engine.engine import STYLE_PALETTES
from backend.services.comfyui_client import ComfyUIClient

logger = logging.getLogger(__name__)


class ArtEngine:
    """Generates character reference sheets and raw comic panel artwork via ComfyUI (or local fallback)."""

    def __init__(self, comfyui: Optional[ComfyUIClient] = None) -> None:
        self.comfyui = comfyui or ComfyUIClient()

    def generate_character_references(self, series: Dict[str, Any], characters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        series_id = series["id"]
        art_style = series["art_style"]
        out_dir = settings.generated_dir / "characters" / f"series_{series_id}"
        out_dir.mkdir(parents=True, exist_ok=True)

        results: List[Dict[str, Any]] = []
        comfy_online = self.comfyui.is_available()

        with get_db() as conn:
            for char in characters:
                existing = conn.execute(
                    "SELECT * FROM character_references WHERE character_id = ?",
                    (char["id"],),
                ).fetchone()
                if existing:
                    results.append(dict(existing))
                    continue

                out_path = out_dir / f"{char['character_uid']}.png"
                positive_prompt = (
                    f"character reference sheet, turnaround, front view and three-quarter view, "
                    f"{art_style} style, {char['visual_prompt_token']}, clean background, "
                    f"consistent design, high detail, no text, no watermark"
                )
                negative_prompt = "text, letters, speech bubble, watermark, signature, blurry, deformed, extra limbs"

                backend_used = "comfyui"
                success = False
                if comfy_online:
                    success = self.comfyui.generate_image(
                        workflow_name="character_sheet",
                        positive_prompt=positive_prompt,
                        negative_prompt=negative_prompt,
                        seed=int(char["seed"]),
                        width=settings.comfyui_width,
                        height=settings.comfyui_height,
                        output_path=out_path,
                    )

                if not success and settings.enable_pollinations_fallback and "PYTEST_CURRENT_TEST" not in os.environ:
                    success = self._generate_pollinations_image(
                        prompt=positive_prompt,
                        seed=int(char["seed"]),
                        width=settings.comfyui_width,
                        height=settings.comfyui_height,
                        out_path=out_path,
                    )
                    if success:
                        backend_used = "pollinations_flux"

                if not success:
                    if not settings.comfyui_enable_fallback_renderer:
                        raise RuntimeError(f"ComfyUI unavailable and fallback disabled for character {char['name']}")
                    backend_used = "local_fallback_renderer"
                    self._render_fallback_character_sheet(out_path, char, art_style)

                conn.execute(
                    """
                    INSERT INTO character_references (
                        character_id, series_id, image_path, prompt_used,
                        negative_prompt, seed, width, height, generator_backend
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        char["id"],
                        series_id,
                        str(out_path),
                        positive_prompt,
                        negative_prompt,
                        int(char["seed"]),
                        settings.comfyui_width,
                        settings.comfyui_height,
                        backend_used,
                    ),
                )
                row = conn.execute(
                    "SELECT * FROM character_references WHERE character_id = ? ORDER BY id DESC LIMIT 1",
                    (char["id"],),
                ).fetchone()
                if row:
                    results.append(dict(row))

        return results

    def generate_episode_artwork(self, series: Dict[str, Any], episode: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate raw artwork for all carousel panels and the individual page panel."""
        series_id = series["id"]
        episode_id = episode["id"]
        ep_num = episode["episode_number"]
        art_style = series["art_style"]

        raw_dir = settings.generated_dir / "episodes" / f"series_{series_id}_ep_{ep_num:02d}"
        raw_dir.mkdir(parents=True, exist_ok=True)

        with get_db() as conn:
            panels = rows_to_list(
                conn.execute(
                    "SELECT * FROM comic_panels WHERE episode_id = ? ORDER BY format_type, panel_order",
                    (episode_id,),
                ).fetchall()
            )
            characters = rows_to_list(
                conn.execute("SELECT * FROM characters WHERE series_id = ?", (series_id,)).fetchall()
            )
            char_refs = rows_to_list(
                conn.execute("SELECT * FROM character_references WHERE series_id = ?", (series_id,)).fetchall()
            )

        char_by_name = {c["name"].lower(): c for c in characters}
        ref_by_char_id = {r["character_id"]: r for r in char_refs}
        comfy_online = self.comfyui.is_available()

        generated: List[Dict[str, Any]] = []
        with get_db() as conn:
            for panel in panels:
                existing = conn.execute(
                    "SELECT * FROM generated_images WHERE panel_id = ? AND image_role = 'raw_panel'",
                    (panel["id"],),
                ).fetchone()
                if existing and Path(existing["file_path"]).exists():
                    generated.append(dict(existing))
                    continue

                try:
                    present_names = json.loads(panel.get("characters_present_json") or "[]")
                except json.JSONDecodeError:
                    present_names = []

                present_chars = [char_by_name[n.lower()] for n in present_names if n.lower() in char_by_name]
                if not present_chars and characters:
                    present_chars = [characters[0]]

                char_tokens = "; ".join(c["visual_prompt_token"] for c in present_chars)
                ref_image_name: Optional[str] = None
                if comfy_online and present_chars:
                    ref_row = ref_by_char_id.get(present_chars[0]["id"])
                    if ref_row:
                        ref_image_name = self.comfyui.upload_image(Path(ref_row["image_path"]))

                positive_prompt = (
                    f"{art_style} comic illustration, {panel['camera_angle']}, "
                    f"{panel['panel_description']}, {panel['character_expressions']}, "
                    f"background: {panel['background_description']}, "
                    f"characters: {char_tokens}, dramatic lighting, no text, no speech bubbles, no letters"
                )
                negative_prompt = "speech bubble, text, letters, caption, watermark, signature, blurry, deformed"
                seed = (series.get("seed", 42) + ep_num * 1000 + panel["id"] * 17) % 2_000_000_000

                prefix = "carousel" if panel["format_type"] == "carousel" else "individual"
                out_path = raw_dir / f"{prefix}_{panel['panel_order']:02d}.png"

                backend_used = "comfyui"
                success = False
                if comfy_online:
                    success = self.comfyui.generate_image(
                        workflow_name="comic_panel",
                        positive_prompt=positive_prompt,
                        negative_prompt=negative_prompt,
                        seed=seed,
                        width=settings.comfyui_width,
                        height=settings.comfyui_height,
                        output_path=out_path,
                        reference_image_name=ref_image_name,
                    )

                if not success and settings.enable_pollinations_fallback and "PYTEST_CURRENT_TEST" not in os.environ:
                    success = self._generate_pollinations_image(
                        prompt=positive_prompt,
                        seed=seed,
                        width=settings.comfyui_width,
                        height=settings.comfyui_height,
                        out_path=out_path,
                    )
                    if success:
                        backend_used = "pollinations_flux"

                if not success:
                    if not settings.comfyui_enable_fallback_renderer:
                        raise RuntimeError(f"ComfyUI unavailable for panel #{panel['id']}")
                    backend_used = "local_fallback_renderer"
                    self._render_fallback_panel_art(
                        out_path=out_path,
                        art_style=art_style,
                        panel=panel,
                        present_chars=present_chars,
                        seed=seed,
                    )

                data_bytes = out_path.read_bytes()
                checksum = hashlib.sha256(data_bytes).hexdigest()

                cur = conn.execute(
                    """
                    INSERT INTO generated_images (
                        series_id, episode_id, panel_id, image_role, slide_number,
                        file_path, width, height, file_size_bytes, checksum_sha256,
                        prompt_used, seed, generator_backend, qc_passed
                    )
                    VALUES (?, ?, ?, 'raw_panel', ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        series_id,
                        episode_id,
                        panel["id"],
                        panel["panel_order"],
                        str(out_path),
                        settings.comfyui_width,
                        settings.comfyui_height,
                        len(data_bytes),
                        checksum,
                        positive_prompt,
                        seed,
                        backend_used,
                    ),
                )
                row = conn.execute("SELECT * FROM generated_images WHERE id = ?", (cur.lastrowid,)).fetchone()
                if row:
                    generated.append(dict(row))

            conn.execute(
                "UPDATE episodes SET status = 'art_generated', updated_at = datetime('now') WHERE id = ?",
                (episode_id,),
            )

        return generated

    @staticmethod
    def _generate_pollinations_image(
        prompt: str,
        seed: int,
        width: int,
        height: int,
        out_path: Path,
    ) -> bool:
        """Generate real AI comic artwork via free Pollinations.ai Flux endpoint when ComfyUI is offline."""
        encoded = urllib.parse.quote(prompt[:900], safe="")
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width={width}&height={height}&seed={seed}&model=flux&nologo=true"
        )
        for attempt in range(2):
            try:
                with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                    resp = client.get(url)
                    if resp.status_code == 200 and len(resp.content) > 5000:
                        with Image.open(io.BytesIO(resp.content)) as im:
                            rgb = im.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
                            out_path.parent.mkdir(parents=True, exist_ok=True)
                            rgb.save(out_path, format="PNG")
                        return True
                    logger.warning("Pollinations HTTP %d (attempt %d)", resp.status_code, attempt + 1)
            except Exception as exc:
                logger.warning("Pollinations generation failed (attempt %d): %s", attempt + 1, exc)
        return False

    @staticmethod
    def _color_from_name(name: str, fallback: Tuple[int, int, int]) -> Tuple[int, int, int]:
        lowered = name.lower()
        mapping = {
            "blue": (55, 115, 215),
            "cobalt": (42, 86, 195),
            "silver": (205, 212, 222),
            "white": (235, 238, 245),
            "crimson": (195, 42, 62),
            "red": (205, 50, 50),
            "amber": (230, 165, 45),
            "gold": (235, 185, 65),
            "emerald": (45, 175, 115),
            "green": (55, 165, 95),
            "brown": (125, 82, 54),
            "chestnut": (135, 76, 48),
            "black": (32, 34, 42),
            "dark": (42, 44, 54),
        }
        for key, rgb in mapping.items():
            if key in lowered:
                return rgb
        return fallback

    def _render_fallback_character_sheet(self, out_path: Path, char: Dict[str, Any], art_style: str) -> None:
        w, h = settings.comfyui_width, settings.comfyui_height
        bg, accent, fg = STYLE_PALETTES.get(art_style, ((24, 28, 42), (220, 120, 80), (245, 245, 245)))
        img = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(img)

        # Subtle grid
        for x in range(0, w, 60):
            draw.line([(x, 0), (x, h)], fill=(bg[0] + 10, bg[1] + 10, bg[2] + 10), width=1)
        for y in range(0, h, 60):
            draw.line([(0, y), (w, y)], fill=(bg[0] + 10, bg[1] + 10, bg[2] + 10), width=1)

        hair_rgb = self._color_from_name(char.get("hair_color", ""), accent)
        eye_rgb = self._color_from_name(char.get("eye_color", ""), (240, 200, 90))

        # Front silhouette + bust
        cx, cy = w // 2, int(h * 0.48)
        draw.ellipse((cx - 170, cy - 260, cx + 170, cy + 80), fill=hair_rgb)
        draw.ellipse((cx - 125, cy - 210, cx + 125, cy + 50), fill=(235, 208, 188))
        # Eyes
        draw.ellipse((cx - 65, cy - 110, cx - 25, cy - 82), fill=eye_rgb)
        draw.ellipse((cx + 25, cy - 110, cx + 65, cy - 82), fill=eye_rgb)
        # Shoulders / outfit
        draw.polygon([(cx - 220, cy + 320), (cx - 150, cy + 75), (cx + 150, cy + 75), (cx + 220, cy + 320)], fill=accent)
        draw.rectangle((40, 40, w - 40, h - 40), outline=accent, width=6)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, format="PNG")

    def _render_fallback_panel_art(
        self,
        out_path: Path,
        art_style: str,
        panel: Dict[str, Any],
        present_chars: List[Dict[str, Any]],
        seed: int,
    ) -> None:
        w, h = settings.comfyui_width, settings.comfyui_height
        bg, accent, _ = STYLE_PALETTES.get(art_style, ((24, 28, 42), (220, 120, 80), (245, 245, 245)))
        rng = random.Random(seed)

        img = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(img)

        # Vertical gradient sky/backdrop
        for y in range(0, h, 4):
            t = y / h
            r = int(bg[0] * (1 - t) + min(255, bg[0] + 45) * t)
            g = int(bg[1] * (1 - t) + min(255, bg[1] + 35) * t)
            b = int(bg[2] * (1 - t) + min(255, bg[2] + 55) * t)
            draw.rectangle((0, y, w, y + 4), fill=(r, g, b))

        # Atmospheric cityscape / terrain silhouettes
        horizon = int(h * 0.62)
        for bx in range(0, w, rng.randint(70, 130)):
            bw = rng.randint(60, 120)
            bh = rng.randint(140, 380)
            shade = (max(0, bg[0] - 8), max(0, bg[1] - 8), max(0, bg[2] - 4))
            draw.rectangle((bx, horizon - bh, bx + bw, h), fill=shade)
            # Glowing windows
            for wy in range(horizon - bh + 20, horizon - 20, 34):
                if rng.random() < 0.45:
                    draw.rectangle((bx + 14, wy, bx + 26, wy + 14), fill=accent)

        # Dramatic light source / moon / portal
        lx = rng.randint(int(w * 0.2), int(w * 0.8))
        ly = rng.randint(int(h * 0.22), int(h * 0.42))
        rad = rng.randint(90, 160)
        draw.ellipse((lx - rad, ly - rad, lx + rad, ly + rad), fill=accent)

        # Dynamic speedlines for action/cliffhanger feel
        for _ in range(18):
            angle = rng.uniform(0, math.tau)
            x1 = lx + int(math.cos(angle) * (rad + 40))
            y1 = ly + int(math.sin(angle) * (rad + 40))
            x2 = lx + int(math.cos(angle) * 750)
            y2 = ly + int(math.sin(angle) * 750)
            draw.line([(x1, y1), (x2, y2)], fill=(255, 255, 255), width=2)

        # Character focal figure(s) in center zone (leaving top & bottom safe for bubbles/narration)
        num_chars = max(1, min(2, len(present_chars)))
        for idx in range(num_chars):
            char = present_chars[idx] if idx < len(present_chars) else {}
            hair_rgb = self._color_from_name(char.get("hair_color", ""), accent)
            eye_rgb = self._color_from_name(char.get("eye_color", ""), (255, 215, 90))
            cx = w // 2 if num_chars == 1 else int(w * (0.34 if idx == 0 else 0.68))
            cy = int(h * 0.56)

            # Shoulders / coat
            draw.polygon([(cx - 170, cy + 290), (cx - 115, cy + 60), (cx + 115, cy + 60), (cx + 170, cy + 290)], fill=(30, 32, 44))
            draw.polygon([(cx - 95, cy + 290), (cx - 60, cy + 75), (cx + 60, cy + 75), (cx + 95, cy + 290)], fill=accent)
            # Head & hair
            draw.ellipse((cx - 110, cy - 165, cx + 110, cy + 55), fill=hair_rgb)
            draw.ellipse((cx - 82, cy - 125, cx + 82, cy + 45), fill=(236, 208, 186))
            # Expressive eyes
            draw.ellipse((cx - 44, cy - 62, cx - 16, cy - 42), fill=eye_rgb)
            draw.ellipse((cx + 16, cy - 62, cx + 44, cy - 42), fill=eye_rgb)

        img = img.filter(ImageFilter.SMOOTH_MORE)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, format="PNG")
