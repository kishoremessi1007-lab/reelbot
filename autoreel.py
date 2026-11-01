"""
Auto AI story reels: writes a 6-part story, makes one part per run
(voice + images + burned-in captions) and posts it to Instagram as a Reel.

pip install edge-tts requests   (and ffmpeg must be installed)

Env vars: GEMINI_API_KEY, IG_USER_ID, IG_ACCESS_TOKEN, optional GENRE
"""
import os, json, asyncio, subprocess, time, random, requests
import edge_tts

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
IG_USER_ID = os.environ["IG_USER_ID"]
IG_TOKEN = os.environ["IG_ACCESS_TOKEN"]
GENRE = os.environ.get("GENRE", "horror mystery")
PARTS = 6
VOICE = "en-US-AndrewNeural"
STATE = "state.json"
GRAPH = "https://graph.facebook.com/v21.0"
WORK = "work"
os.makedirs(WORK, exist_ok=True)


# ---------- 1. story ----------
def gen_story():
    prompt = f"""Write an original, gripping {GENRE} story split into exactly {PARTS} parts for Instagram Reels.
Rules:
- Each part: 90-130 words of narration, simple spoken language, no stage directions.
- Part 1 opens with a shocking one-sentence hook.
- Parts 1 to {PARTS - 1} end on a cliffhanger. The last part resolves everything.
- Each part has 4 image prompts (vivid scenes) and 4 matching stock_keywords (2-3 word photo search terms, e.g. 'dark forest night', 'old empty house').
Return ONLY JSON:
{{"title": "...", "hashtags": ["#a","#b","#c","#d","#e"],
 "parts": [{{"narration": "...", "image_prompts": ["...","...","...","..."]}}]}}"""
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json"}},
        timeout=120)
    r.raise_for_status()
    story = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    assert len(story["parts"]) == PARTS
    return story


# ---------- 2. voice + word timings ----------
async def tts(text, path):
    comm = edge_tts.Communicate(text, VOICE, boundary="WordBoundary")
    words = []
    with open(path, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                start = ch["offset"] / 1e7
                words.append((start, start + ch["duration"] / 1e7, ch["text"]))
    return words


def duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path])
    return float(out.strip())


# ---------- 3. captions (ASS, 3 words at a time) ----------
def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def make_ass(words, path):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,DejaVu Sans,84,&H0000FFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,7,0,5,60,60,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = []
    for i in range(0, len(words), 3):
        g = words[i:i + 3]
        end = words[i + 3][0] if i + 3 < len(words) else g[-1][1]
        text = " ".join(w[2] for w in g).upper()
        lines.append(f"Dialogue: 0,{ass_time(g[0][0])},{ass_time(end)},Default,,0,0,0,,{text}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines))


# ---------- 4. images ----------
def get_image(prompt, path, keywords=None):
    # 1) Pixabay stock photo (free key from pixabay.com/api/docs/)
    key = os.environ.get("PIXABAY_API_KEY")
    if key:
        try:
            q = keywords or " ".join(prompt.split()[:4])
            r = requests.get("https://pixabay.com/api/",
                             params={"key": key, "q": q, "image_type": "photo",
                                     "orientation": "vertical", "per_page": 20,
                                     "safesearch": "true"}, timeout=60)
            hits = r.json().get("hits", [])
            if hits:
                img = requests.get(random.choice(hits)["largeImageURL"], timeout=120)
                if img.ok:
                    with open(path, "wb") as f:
                        f.write(img.content)
                    return
            print("Pixabay: no photos for", q, r.status_code)
        except Exception as e:
            print("Pixabay failed:", e)
    # 2) Pollinations AI image
    url = ("https://image.pollinations.ai/prompt/"
           + requests.utils.quote(prompt + ", cinematic, dramatic lighting, vertical")
           + f"?width=1080&height=1920&nologo=true&seed={random.randint(1, 99999)}")
    for _ in range(2):
        try:
            r = requests.get(url, timeout=120)
            if r.ok and r.headers.get("content-type", "").startswith("image"):
                with open(path, "wb") as f:
                    f.write(r.content)
                return
            print("Pollinations status:", r.status_code)
        except requests.RequestException as e:
            print("Pollinations failed:", e)
        time.sleep(5)
    # 3) last resort: dark plain frame so the run never crashes
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x14141f:s=1080x1920",
                    "-frames:v", "1", path], check=True, capture_output=True)


# ---------- 5. build video ----------
def build_video(part, out_path):
    audio = f"{WORK}/voice.mp3"
    words = asyncio.run(tts(part["narration"], audio))
    dur = duration(audio)
    if not words:  # fallback: spread words evenly
        toks = part["narration"].split()
        step = dur / len(toks)
        words = [(i * step, (i + 1) * step, w) for i, w in enumerate(toks)]
    make_ass(words, f"{WORK}/cap.ass")

    prompts = part["image_prompts"]
    clip_len = (dur + 0.5) / len(prompts)
    frames = int(clip_len * 30)
    clips = []
    for i, p in enumerate(prompts):
        img, clip = f"{WORK}/img{i}.jpg", f"{WORK}/clip{i}.mp4"
        kws = part.get('stock_keywords', [None] * len(prompts))
        get_image(p, img, kws[i] if i < len(kws) else None)
        subprocess.run(
            ["ffmpeg", "-y", "-i", img, "-vf",
             f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0007,1.25)':d={frames}:s=1080x1920:fps=30,format=yuv420p",
             "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", clip],
            check=True, capture_output=True)
        clips.append(clip)

    with open(f"{WORK}/list.txt", "w") as f:
        for c in clips:
            f.write(f"file '{os.path.basename(c)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{WORK}/list.txt",
         "-i", audio, "-vf", f"subtitles={WORK}/cap.ass",
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
         "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path],
        check=True, capture_output=True)


# ---------- 6. post to Instagram ----------
def post_reel(path, caption):
    r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
        "media_type": "REELS", "upload_type": "resumable",
        "caption": caption, "access_token": IG_TOKEN})
    r.raise_for_status()
    cid = r.json()["id"]
    uri = r.json().get("uri") or f"https://rupload.facebook.com/ig-api-upload/v21.0/{cid}"
    with open(path, "rb") as f:
        u = requests.post(uri, headers={
            "Authorization": f"OAuth {IG_TOKEN}", "offset": "0",
            "file_size": str(os.path.getsize(path))}, data=f, timeout=600)
    u.raise_for_status()
    for _ in range(60):
        s = requests.get(f"{GRAPH}/{cid}", params={
            "fields": "status_code", "access_token": IG_TOKEN}).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"IG processing error: {s}")
        time.sleep(10)
    p = requests.post(f"{GRAPH}/{IG_USER_ID}/media_publish", data={
        "creation_id": cid, "access_token": IG_TOKEN})
    p.raise_for_status()
    print("Posted:", p.json())


# ---------- main ----------
def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else None
    if not state or state["next"] > PARTS:
        state = {"story": gen_story(), "next": 1}
    story, n = state["story"], state["next"]
    part = story["parts"][n - 1]

    out = f"{WORK}/part{n}.mp4"
    build_video(part, out)

    hook = part["narration"].split(".")[0].strip() + "."
    tail = f"Follow for Part {n + 1}/{PARTS} 👇" if n < PARTS else "The end. Want another story? Follow! 🔔"
    caption = f"{story['title']} | Part {n}/{PARTS}\n\n{hook}\n\n{tail}\n\n{' '.join(story['hashtags'])}"
    post_reel(out, caption)

    state["next"] = n + 1
    json.dump(state, open(STATE, "w"), indent=2)


if __name__ == "__main__":
    main()
