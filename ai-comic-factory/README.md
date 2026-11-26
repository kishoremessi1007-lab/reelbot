# AI Comic Factory — Autonomous AI Instagram Comic Studio

A complete **₹0 / zero-cost**, local-first autonomous comic production and Instagram publishing platform built with **React + Vite**, **Python + FastAPI**, **SQLite**, **Ollama**, **ComfyUI**, **Pillow**, **n8n Community Edition**, and the **Official Instagram Graph API**.

## Architecture

- **Story Engine (`backend/engines/story_engine/`)**: Rotates across 24 genres, pairs with 10 distinct art styles, avoids repetition, and writes original multi-episode series bibles into SQLite.
- **Character Engine (`backend/engines/character_engine/`)**: Generates detailed character profiles with fixed visual tokens, seeds, and character reference sheets.
- **Continuity Engine (`backend/engines/continuity_engine/`)**: Tracks episode summaries, cliffhangers, unresolved mysteries, published post IDs, and automatic series completion/rotation.
- **Script Engine (`backend/engines/script_engine/`)**: Produces visual scripts for **both** a 5–8 slide Instagram Carousel (`1080×1350`) and a distinct standalone Individual Comic Page (`1080×1350`).
- **Art & Composition Engines (`backend/engines/art_engine/`, `backend/engines/composition_engine/`)**: Uses ComfyUI workflows (`comfyui/workflows/`) with a built-in local Pillow fallback renderer when ComfyUI is offline, then renders speech bubbles, narration boxes, SFX, series headers, and runs `QualityController` checks before queuing.
- **Publishing & Media Hosting (`backend/engines/publishing_engine/`, `backend/storage/`)**: Official Instagram Graph API container workflow (`media` -> `FINISHED` -> `media_publish`), idempotency keys, exponential backoff retries, and zero-cost media hosting (`local`, `local_tunnel` via Cloudflare Tunnel, or `cloudflare_r2` free tier).
- **Automation**: Built-in APScheduler + importable n8n Community Edition workflow (`n8n/autonomous_comic_factory_workflow.json`).

---

## Quick Start (Local Windows / Linux / macOS)

### 1. Backend Setup
```powershell
cd ai-comic-factory
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\uvicorn.exe backend.api.main:app --host 0.0.0.0 --port 8000
```

### 2. Frontend Dashboard Setup
```powershell
cd ai-comic-factory\frontend
npm install
npm run dev
```
Open **http://localhost:5173** in your browser.

### 3. Local AI Engines (Optional but Recommended for Full AI Generation)
- **Ollama**: Install Ollama, then run `ollama pull llama3.1:8b` and ensure `ollama serve` is running on `http://localhost:11434`.
- **ComfyUI**: Run ComfyUI locally on `http://127.0.0.1:8188` with a checkpoint such as `dreamshaper_8.safetensors`.
  *(If Ollama or ComfyUI is offline, the built-in fallback generators allow you to test the full pipeline, UI, and composition engine without errors.)*

### 4. Official Instagram Graph API & Public Media URL Setup (₹0)
Instagram requires public HTTPS image URLs:
- **Option A (Cloudflare Tunnel — Free)**: Run `cloudflared tunnel --url http://localhost:8000` and set `MEDIA_HOSTING_PROVIDER=local_tunnel` and `CLOUDFLARE_TUNNEL_URL=https://your-tunnel.trycloudflare.com` in `.env`.
- **Option B (Cloudflare R2 — Free Tier 10 GB/mo)**: Set `MEDIA_HOSTING_PROVIDER=cloudflare_r2` and fill `R2_*` variables in `.env`.

Set `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_ACCOUNT_ID` in `.env` from your Meta Developer App (Instagram Business/Creator account with `instagram_basic` and `instagram_content_publish` permissions).

### 5. Self-Hosted n8n (Optional)
Run `docker compose up -d` and import `n8n/autonomous_comic_factory_workflow.json` in n8n at `http://localhost:5678`.

---

## Running Automated Tests
```powershell
cd ai-comic-factory
.\.venv\Scripts\pytest.exe backend\tests\test_comic_factory.py -v
```
