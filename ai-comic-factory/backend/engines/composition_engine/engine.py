from __future__ import annotations

import hashlib
import json
import logging
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

from backend.config import settings
from backend.database.db import get_db, rows_to_list
from backend.engines.story_engine.engine import STYLE_PALETTES

logger = logging.getLogger(__name__)


def _load_font(size: int, bold: bool = False, style: str = "") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: List[str] = []
    if "noir" in style.lower() or "western" in style.lower():
        candidates = ["C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/georgiab.ttf"] if not bold else ["C:/Windows/Fonts/georgiab.ttf"]
    elif "cyberpunk" in style.lower():
        candidates = ["C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf"]
    else:
        candidates = ["C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/segoeuib.ttf"]

    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


class CompositionEngine:
    """Renders speech bubbles, narration boxes, branding, and borders onto 1080x1350 comic pages."""

    TARGET_W = 1080
    TARGET_H = 1350

    def compose_episode(self, series: Dict[str, Any], episode: Dict[str, Any]) -> Dict[str, Any]:
        series_id = series["id"]
        episode_id = episode["id"]
        ep_num = episode["episode_number"]
        art_style = series["art_style"]

        carousel_dir = settings.generated_dir / "carousel" / f"series_{series_id}_ep_{ep_num:02d}"
        indiv_dir = settings.generated_dir / "individual_pages" / f"series_{series_id}_ep_{ep_num:02d}"
        carousel_dir.mkdir(parents=True, exist_ok=True)
        indiv_dir.mkdir(parents=True, exist_ok=True)

        with get_db() as conn:
            panels = rows_to_list(
                conn.execute(
                    "SELECT * FROM comic_panels WHERE episode_id = ? ORDER BY format_type, panel_order",
                    (episode_id,),
                ).fetchall()
            )
            raw_imgs = rows_to_list(
                conn.execute(
                    "SELECT * FROM generated_images WHERE episode_id = ? AND image_role = 'raw_panel'",
                    (episode_id,),
                ).fetchall()
            )

        raw_by_panel = {r["panel_id"]: r for r in raw_imgs}
        carousel_panels = [p for p in panels if p["format_type"] == "carousel"]
        indiv_panels = [p for p in panels if p["format_type"] == "individual"]

        carousel_images: List[Dict[str, Any]] = []
        individual_image: Optional[Dict[str, Any]] = None

        total_slides = len(carousel_panels)
        with get_db() as conn:
            for idx, panel in enumerate(carousel_panels, start=1):
                raw = raw_by_panel.get(panel["id"])
                if not raw:
                    raise RuntimeError(f"Missing raw artwork for carousel panel {panel['id']}")
                out_path = carousel_dir / f"slide_{idx:02d}.png"
                self._compose_page(
                    raw_path=Path(raw["file_path"]),
                    out_path=out_path,
                    series_title=series["title"],
                    episode_number=ep_num,
                    episode_title=episode["title"],
                    art_style=art_style,
                    panel=panel,
                    slide_index=idx,
                    total_slides=total_slides,
                    is_individual=False,
                )
                row = self._save_composed_record(
                    conn, series_id, episode_id, panel["id"], "carousel_slide", idx, out_path
                )
                carousel_images.append(row)

            if indiv_panels:
                indiv_panel = indiv_panels[0]
                raw = raw_by_panel.get(indiv_panel["id"])
                if not raw:
                    raise RuntimeError(f"Missing raw artwork for individual panel {indiv_panel['id']}")
                out_path = indiv_dir / f"episode_{ep_num:02d}_page.png"
                self._compose_page(
                    raw_path=Path(raw["file_path"]),
                    out_path=out_path,
                    series_title=series["title"],
                    episode_number=ep_num,
                    episode_title=episode["title"],
                    art_style=art_style,
                    panel=indiv_panel,
                    slide_index=1,
                    total_slides=1,
                    is_individual=True,
                )
                individual_image = self._save_composed_record(
                    conn, series_id, episode_id, indiv_panel["id"], "individual_page", 1, out_path
                )

            conn.execute(
                "UPDATE episodes SET status = 'composed', updated_at = datetime('now') WHERE id = ?",
                (episode_id,),
            )

        return {
            "carousel_images": carousel_images,
            "individual_image": individual_image,
        }

    def _save_composed_record(
        self,
        conn: Any,
        series_id: int,
        episode_id: int,
        panel_id: int,
        image_role: str,
        slide_number: int,
        out_path: Path,
    ) -> Dict[str, Any]:
        data_bytes = out_path.read_bytes()
        checksum = hashlib.sha256(data_bytes).hexdigest()
        with Image.open(out_path) as im:
            w, h = im.size

        existing = conn.execute(
            "SELECT id FROM generated_images WHERE episode_id = ? AND image_role = ? AND slide_number = ?",
            (episode_id, image_role, slide_number),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE generated_images
                SET file_path = ?, width = ?, height = ?, file_size_bytes = ?, checksum_sha256 = ?, qc_passed = 0
                WHERE id = ?
                """,
                (str(out_path), w, h, len(data_bytes), checksum, existing["id"]),
            )
            row = conn.execute("SELECT * FROM generated_images WHERE id = ?", (existing["id"],)).fetchone()
        else:
            cur = conn.execute(
                """
                INSERT INTO generated_images (
                    series_id, episode_id, panel_id, image_role, slide_number,
                    file_path, width, height, file_size_bytes, checksum_sha256,
                    generator_backend, qc_passed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pillow_composer', 0)
                """,
                (series_id, episode_id, panel_id, image_role, slide_number, str(out_path), w, h, len(data_bytes), checksum),
            )
            row = conn.execute("SELECT * FROM generated_images WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    def _compose_page(
        self,
        raw_path: Path,
        out_path: Path,
        series_title: str,
        episode_number: int,
        episode_title: str,
        art_style: str,
        panel: Dict[str, Any],
        slide_index: int,
        total_slides: int,
        is_individual: bool,
    ) -> None:
        bg, accent, fg = STYLE_PALETTES.get(art_style, ((20, 24, 34), (230, 120, 70), (248, 248, 248)))
        with Image.open(raw_path) as src:
            canvas = src.convert("RGB").resize((self.TARGET_W, self.TARGET_H), Image.Resampling.LANCZOS)

        draw = ImageDraw.Draw(canvas, "RGBA")

        # Outer comic frame & gutter
        border = 22
        draw.rectangle((0, 0, self.TARGET_W, border), fill=bg)
        draw.rectangle((0, self.TARGET_H - border, self.TARGET_W, self.TARGET_H), fill=bg)
        draw.rectangle((0, 0, border, self.TARGET_H), fill=bg)
        draw.rectangle((self.TARGET_W - border, 0, self.TARGET_W, self.TARGET_H), fill=bg)
        draw.rectangle((border, border, self.TARGET_W - border, self.TARGET_H - border), outline=accent, width=5)

        # Header bar (Series title + Episode badge + Page/Slide number)
        header_h = 84
        draw.rectangle((border, border, self.TARGET_W - border, border + header_h), fill=(bg[0], bg[1], bg[2], 230))
        title_font = _load_font(30, bold=True, style=art_style)
        badge_font = _load_font(24, bold=True, style=art_style)

        draw.text((border + 24, border + 24), series_title.upper()[:34], fill=fg, font=title_font)
        badge_text = f"EP {episode_number:02d}" + (" • FEATURE" if is_individual else f" • {slide_index}/{total_slides}")
        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        bw = bbox[2] - bbox[0] + 32
        bx = self.TARGET_W - border - bw - 18
        draw.rounded_rectangle((bx, border + 18, bx + bw, border + 64), radius=10, fill=accent)
        draw.text((bx + 16, border + 26), badge_text, fill=(15, 15, 20), font=badge_font)

        # Narration box in upper safe zone (below header, above character faces)
        narration = (panel.get("narration") or "").strip()
        y_cursor = border + header_h + 18
        if narration:
            narr_font = _load_font(26, bold=True, style=art_style)
            wrapped = textwrap.wrap(narration, width=46)[:3]
            box_h = 26 + len(wrapped) * 34
            draw.rectangle((border + 26, y_cursor, self.TARGET_W - border - 26, y_cursor + box_h), fill=(250, 242, 205, 240), outline=(20, 20, 24), width=4)
            ty = y_cursor + 12
            for line in wrapped:
                draw.text((border + 44, ty), line, fill=(20, 20, 24), font=narr_font)
                ty += 34
            y_cursor += box_h + 16

        # Sound Effects (SFX) in upper-right safe zone
        try:
            sfx_list = json.loads(panel.get("sound_effects_json") or "[]")
        except json.JSONDecodeError:
            sfx_list = []
        if sfx_list:
            sfx_text = str(sfx_list[0]).upper()
            sfx_font = _load_font(42, bold=True, style=art_style)
            draw.text((self.TARGET_W - 260, y_cursor + 8), sfx_text, fill=(15, 15, 20), font=sfx_font)
            draw.text((self.TARGET_W - 264, y_cursor + 4), sfx_text, fill=accent, font=sfx_font)

        # Speech bubbles in lower safe zone (y >= 930) so character faces in center are never covered
        try:
            dialogues = json.loads(panel.get("dialogue_json") or "[]")
        except json.JSONDecodeError:
            dialogues = []

        bubble_font = _load_font(27, bold=False, style=art_style)
        speaker_font = _load_font(20, bold=True, style=art_style)

        bubble_y = self.TARGET_H - border - 46
        for idx, d in enumerate(reversed(dialogues[:2])):
            speaker = str(d.get("speaker", "")).strip()
            text = str(d.get("text", "")).strip()
            if not text:
                continue
            wrapped = textwrap.wrap(text, width=38)[:3]
            bh = 52 + len(wrapped) * 34
            bw = min(820, max(380, max(len(l) for l in wrapped) * 16 + 70))
            bx1 = border + 32 if idx % 2 == 0 else self.TARGET_W - border - 32 - bw
            by1 = bubble_y - bh
            by2 = bubble_y

            draw.rounded_rectangle((bx1, by1, bx1 + bw, by2), radius=28, fill=(255, 255, 255, 246), outline=(18, 18, 22), width=4)
            # Tail pointing up toward character
            tail_x = bx1 + 85 if idx % 2 == 0 else bx1 + bw - 85
            draw.polygon([(tail_x - 16, by1 + 2), (tail_x + 16, by1 + 2), (tail_x, by1 - 28)], fill=(255, 255, 255, 246))
            draw.line([(tail_x - 16, by1), (tail_x, by1 - 28), (tail_x + 16, by1)], fill=(18, 18, 22), width=4)

            if speaker:
                draw.text((bx1 + 24, by1 + 12), speaker.upper(), fill=accent if bg[0] > 40 else (180, 45, 65), font=speaker_font)
            ty = by1 + 40
            for line in wrapped:
                draw.text((bx1 + 24, ty), line, fill=(18, 18, 22), font=bubble_font)
                ty += 34
            bubble_y = by1 - 22

        # Footer episode title strip
        footer_font = _load_font(19, bold=True, style=art_style)
        footer_label = f"{episode_title} • Swipe →" if (not is_individual and slide_index < total_slides) else episode_title
        draw.text((border + 24, self.TARGET_H - border - 30), footer_label[:55], fill=fg, font=footer_font)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_path, format="PNG")


class QualityController:
    """Validates generated comic slides and standalone pages before publishing."""

    EXPECTED_W = 1080
    EXPECTED_H = 1350

    def validate_episode(self, episode_id: int) -> Tuple[bool, Dict[str, Any]]:
        errors: List[str] = []
        with get_db() as conn:
            episode = conn.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,)).fetchone()
            if not episode:
                return False, {"passed": False, "errors": ["Episode not found"]}

            carousel = rows_to_list(
                conn.execute(
                    "SELECT * FROM generated_images WHERE episode_id = ? AND image_role = 'carousel_slide' ORDER BY slide_number",
                    (episode_id,),
                ).fetchall()
            )
            indiv = rows_to_list(
                conn.execute(
                    "SELECT * FROM generated_images WHERE episode_id = ? AND image_role = 'individual_page'",
                    (episode_id,),
                ).fetchall()
            )

        if not (5 <= len(carousel) <= 8):
            errors.append(f"Expected 5-8 carousel slides, got {len(carousel)}")
        if len(indiv) != 1:
            errors.append(f"Expected exactly 1 individual comic page, got {len(indiv)}")

        seen_hashes: set[str] = set()
        for idx, img_row in enumerate(carousel, start=1):
            if img_row["slide_number"] != idx:
                errors.append(f"Slide ordering mismatch at position {idx}: got {img_row['slide_number']}")
            ok, msg = self._check_image_file(Path(img_row["file_path"]))
            if not ok:
                errors.append(f"Carousel slide {idx}: {msg}")
            if img_row["checksum_sha256"] in seen_hashes:
                errors.append(f"Duplicate carousel slide detected at slide {idx}")
            seen_hashes.add(img_row["checksum_sha256"])

        for img_row in indiv:
            ok, msg = self._check_image_file(Path(img_row["file_path"]))
            if not ok:
                errors.append(f"Individual page: {msg}")
            if img_row["checksum_sha256"] in seen_hashes:
                errors.append("Individual page is a duplicate of a carousel slide")

        passed = len(errors) == 0
        report = {"passed": passed, "errors": errors, "carousel_count": len(carousel), "individual_count": len(indiv)}

        with get_db() as conn:
            conn.execute(
                """
                UPDATE episodes
                SET status = ?, qc_report_json = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                ("qc_passed" if passed else "qc_failed", json.dumps(report), episode_id),
            )
            if passed:
                conn.execute(
                    """
                    UPDATE generated_images SET qc_passed = 1
                    WHERE episode_id = ? AND image_role IN ('carousel_slide', 'individual_page')
                    """,
                    (episode_id,),
                )

        return passed, report

    def _check_image_file(self, path: Path) -> Tuple[bool, str]:
        if not path.exists():
            return False, f"File missing: {path}"
        if path.stat().st_size < 1024:
            return False, f"File too small / corrupted: {path}"
        try:
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                w, h = im.size
                if (w, h) != (self.EXPECTED_W, self.EXPECTED_H):
                    return False, f"Invalid dimensions {w}x{h}, expected {self.EXPECTED_W}x{self.EXPECTED_H}"
        except Exception as exc:
            return False, f"Corrupted image: {exc}"
        return True, "OK"
