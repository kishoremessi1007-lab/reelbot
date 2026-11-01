"""
Auto AI story reels: writes a 6-part story, makes one part per run
(voice + images + burned-in captions) and posts it to Instagram as a Reel.

pip install edge-tts requests   (and ffmpeg must be installed)

Env vars: GEMINI_API_KEY, IG_USER_ID, IG_ACCESS_TOKEN, optional GENRE
"""
import os, json, asyncio, subprocess, time, random, glob, base64, requests
import edge_tts

GEMINI_KEY = os.environ["GEMINI_API_KEY"]
IG_USER_ID = os.environ["IG_USER_ID"]
IG_TOKEN = os.environ["IG_ACCESS_TOKEN"]
GENRE = os.environ.get("GENRE", "horror mystery")
PARTS = 6
N_IMAGES = int(os.environ.get("N_IMAGES", "6"))          # scenes per video (more = faster cuts)
VOICE = os.environ.get("VOICE", "en-US-ChristopherNeural")
VOICE_RATE = os.environ.get("VOICE_RATE", "-6%")          # slower = more dramatic
VOICE_PITCH = os.environ.get("VOICE_PITCH", "-4Hz")
IMAGE_STYLE = os.environ.get(
    "IMAGE_STYLE",
    "dark cinematic digital painting, moody dramatic lighting, highly detailed, vertical 9:16, no text")
MUSIC_VOLUME = float(os.environ.get("MUSIC_VOLUME", "0.16"))
STATE = "state.json"
GRAPH = "https://graph.facebook.com/v21.0"
WORK = "work"
os.makedirs(WORK, exist_ok=True)


# ---------- 1. story ----------
def gen_story():
    ph = ", ".join(['"..."'] * N_IMAGES)
    prompt = f"""Write an original, gripping {GENRE} story split into exactly {PARTS} parts for Instagram Reels.
Rules:
- Each part: 90-130 words of narration, simple spoken language, no stage directions.
- Part 1 opens with a shocking one-sentence hook.
- Parts 1 to {PARTS - 1} end on a cliffhanger. The last part resolves everything.
- Give a short "visual_style" for the whole story (art style, color palette, mood) so all images look consistent.
- Each part has {N_IMAGES} image prompts (one per scene, in story order). Each prompt must describe the scene AND restate the main character's look (age, clothes, hair) so the character stays consistent. No text in images.
- Each part also has {N_IMAGES} matching stock_keywords (2-3 word photo search terms, e.g. 'dark forest night').
Return ONLY JSON:
{{"title": "...", "hashtags": ["#a","#b","#c","#d","#e"], "visual_style": "...",
 "parts": [{{"narration": "...", "image_prompts": [{ph}], "stock_keywords": [{ph}]}}]}}"""
    r = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers={"x-goog-api-key": GEMINI_KEY.strip()},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json"}},
        timeout=120)
    if not r.ok:
        print("Gemini error", r.status_code, r.text[:500])
    r.raise_for_status()
    story = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
    assert len(story["parts"]) == PARTS
    return story


# ---------- 2. voice + word timings ----------
async def tts(text, path):
    comm = edge_tts.Communicate(text, VOICE, rate=VOICE_RATE, pitch=VOICE_PITCH,
                                boundary="WordBoundary")
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


# ---------- 3. captions: big, word-by-word highlight ----------
def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def make_ass(words, path, group=3):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,DejaVu Sans,92,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,10,4,5,50,50,0,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    hi = "{\\c&H00E5FF&\\fscx120\\fscy120}"   # current word: yellow + pop
    lo = "{\\c&HFFFFFF&\\fscx100\\fscy100}"
    lines = []
    for gi in range(0, len(words), group):
        g = words[gi:gi + group]
        for wi, (st, en, _) in enumerate(g):
            idx = gi + wi
            end = words[idx + 1][0] if idx + 1 < len(words) else en
            end = max(end, st + 0.05)
            parts = []
            for j, (_, _, t) in enumerate(g):
                t = t.upper().replace("{", "").replace("}", "")
                parts.append(f"{hi}{t}{lo}" if j == wi else t)
            lines.append(f"Dialogue: 0,{ass_time(st)},{ass_time(end)},Default,,0,0,0,,{' '.join(parts)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines))


# ---------- 4. images: AI first, stock photo, then plain frame ----------
def _save_if_image(r, path):
    if r.ok and r.headers.get("content-type", "").startswith("image"):
        with open(path, "wb") as f:
            f.write(r.content)
        return True
    return False


HF_DEAD = False   # set True after a rate-limit so we stop wasting time on it


def cf_image(full, path):
    """Cloudflare Workers AI FLUX (free: 10,000 units/day)."""
    acc, tok = os.environ.get("CF_ACCOUNT_ID"), os.environ.get("CF_API_TOKEN")
    if not (acc and tok):
        return False
    try:
        r = requests.post(
            f"https://api.cloudflare.com/client/v4/accounts/{acc.strip()}/ai/run/@cf/black-forest-labs/flux-1-schnell",
            headers={"Authorization": f"Bearer {tok.strip()}"},
            json={"prompt": (full + ", vertical composition, subject centered")[:2000], "steps": 4},
            timeout=180)
        if r.ok:
            with open(path, "wb") as f:
                f.write(base64.b64decode(r.json()["result"]["image"]))
            return True
        print("Cloudflare status:", r.status_code, r.text[:200])
    except Exception as e:
        print("Cloudflare failed:", e)
    return False


DISABLED = set()   # image sources that failed once this run are skipped afterwards


def gemini_image(prompt, path):
    """AI image using the same Gemini key (works only if your plan allows image models)."""
    if "gemini" in DISABLED:
        return False
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": GEMINI_KEY.strip()},
            json={"contents": [{"parts": [{"text": f"Generate a vertical 9:16 image. {prompt}"}]}],
                  "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}}, timeout=120)
        if r.ok:
            for c in r.json().get("candidates", []):
                for p in c.get("content", {}).get("parts", []):
                    d = p.get("inlineData") or p.get("inline_data")
                    if d:
                        with open(path, "wb") as f:
                            f.write(base64.b64decode(d["data"]))
                        return True
        print("Gemini image failed:", r.status_code, r.text[:200])
    except Exception as e:
        print("Gemini image error:", e)
    DISABLED.add("gemini")
    return False


def get_image(prompt, path, keywords=None):
    global HF_DEAD
    full = f"{prompt}, {IMAGE_STYLE}"
    # 1) Cloudflare Workers AI (only used if CF_ACCOUNT_ID and CF_API_TOKEN are set)
    if cf_image(full, path):
        return
    # 2) Gemini image model (same key as the story; may not be allowed on the free plan)
    if gemini_image(full, path):
        return
    # 3) Hugging Face FLUX (only used if HF_TOKEN is set)
    tok = os.environ.get("HF_TOKEN")
    if tok and not HF_DEAD:
        try:
            r = requests.post(
                "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell",
                headers={"Authorization": f"Bearer {tok}", "Accept": "image/jpeg"},
                json={"inputs": full, "parameters": {"width": 768, "height": 1344}}, timeout=180)
            if _save_if_image(r, path):
                return
            print("HF status:", r.status_code, r.text[:200])
            if r.status_code in (402, 429):
                HF_DEAD = True
        except Exception as e:
            print("HF failed:", e)
    # 4) Pollinations
    url = ("https://image.pollinations.ai/prompt/" + requests.utils.quote(full)
           + f"?width=1080&height=1920&nologo=true&model=flux&seed={random.randint(1, 99999)}")
    for _ in range(2):
        try:
            r = requests.get(url, timeout=120)
            if _save_if_image(r, path):
                return
            print("Pollinations status:", r.status_code)
        except requests.RequestException as e:
            print("Pollinations failed:", e)
        time.sleep(4)
    # 5) Pixabay stock photo
    key = os.environ.get("PIXABAY_API_KEY")
    if key:
        try:
            q = keywords or " ".join(prompt.split()[:4])
            r = requests.get("https://pixabay.com/api/", params={
                "key": key, "q": q, "image_type": "photo", "orientation": "vertical",
                "per_page": 20, "safesearch": "true"}, timeout=60)
            hits = r.json().get("hits", [])
            if hits:
                img = requests.get(random.choice(hits)["largeImageURL"], timeout=120)
                if img.ok:
                    with open(path, "wb") as f:
                        f.write(img.content)
                    return
            print("Pixabay: no photos for", q)
        except Exception as e:
            print("Pixabay failed:", e)
    # 6) last resort: plain dark frame
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x14141f:s=1080x1920",
                    "-frames:v", "1", path], check=True, capture_output=True)


# ---------- 5. audio: background music + whoosh sound effects ----------
def make_music(dur, out):
    """Use your own royalty-free tracks from the music/ folder if any,
    otherwise synthesize a dark ambient drone."""
    files = [f for ext in ("mp3", "wav", "m4a", "ogg") for f in glob.glob(f"music/*.{ext}")]
    if files:
        src = random.choice(files)
        subprocess.run(
            ["ffmpeg", "-y", "-stream_loop", "-1", "-i", src, "-t", f"{dur:.2f}",
             "-af", f"afade=t=in:d=1.5,afade=t=out:st={max(dur - 2, 0):.2f}:d=2",
             "-ar", "44100", "-ac", "2", out], check=True, capture_output=True)
        return
    d = f"{dur:.2f}"
    subprocess.run(
        ["ffmpeg", "-y",
         "-f", "lavfi", "-i", f"sine=f=55:d={d}",
         "-f", "lavfi", "-i", f"sine=f=82.4:d={d}",
         "-f", "lavfi", "-i", f"sine=f=110.5:d={d}",
         "-f", "lavfi", "-i", f"anoisesrc=d={d}:c=brown:a=0.2",
         "-filter_complex",
         "[0][1][2]amix=inputs=3:normalize=0,tremolo=f=0.2:d=0.5[t];"
         "[3]lowpass=f=300[n];"
         "[t][n]amix=inputs=2:normalize=0,aformat=sample_rates=44100:channel_layouts=stereo,"
         f"afade=t=in:d=1.5,afade=t=out:st={max(dur - 2, 0):.2f}:d=2",
         out], check=True, capture_output=True)


def make_sfx(out):
    """Short whoosh + low hit, used at every scene change."""
    subprocess.run(
        ["ffmpeg", "-y",
         "-f", "lavfi", "-i", "anoisesrc=d=0.7:c=white:a=0.5",
         "-f", "lavfi", "-i", "sine=f=60:d=0.7",
         "-filter_complex",
         "[0]highpass=f=500,lowpass=f=6000,afade=t=in:d=0.35,afade=t=out:st=0.35:d=0.35[w];"
         "[1]afade=t=out:d=0.7,volume=1.2[b];"
         "[w][b]amix=inputs=2:normalize=0,aformat=sample_rates=44100:channel_layouts=stereo",
         out], check=True, capture_output=True)


# ---------- 6. build video ----------
def build_video(part, out_path, style=""):
    audio = f"{WORK}/voice.mp3"
    words = asyncio.run(tts(part["narration"], audio))
    dur = duration(audio)
    if not words:  # fallback: spread words evenly
        toks = part["narration"].split()
        step = dur / len(toks)
        words = [(i * step, (i + 1) * step, w) for i, w in enumerate(toks)]
    make_ass(words, f"{WORK}/cap.ass")

    prompts = part["image_prompts"]
    n = len(prompts)
    total = dur + 0.6
    clip_len = total / n
    frames = int(clip_len * 30)
    kws = part.get("stock_keywords", [None] * n)
    clips = []
    for i, p in enumerate(prompts):
        img, clip = f"{WORK}/img{i}.jpg", f"{WORK}/clip{i}.mp4"
        get_image(f"{p}, {style}" if style else p, img, kws[i] if i < len(kws) else None)
        # alternate slow zoom-in / zoom-out, centered
        z = ("min(1+0.0008*on,1.3)" if i % 2 == 0 else "max(1.3-0.0008*on,1.0)")
        subprocess.run(
            ["ffmpeg", "-y", "-i", img, "-vf",
             "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
             f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=1080x1920:fps=30,"
             "format=yuv420p",
             "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", clip],
            check=True, capture_output=True)
        clips.append(clip)

    with open(f"{WORK}/list.txt", "w") as f:
        for c in clips:
            f.write(f"file '{os.path.basename(c)}'\n")

    music, sfx = f"{WORK}/music.wav", f"{WORK}/sfx.wav"
    make_music(total, music)
    make_sfx(sfx)

    # whoosh at each scene change
    cuts = [int(i * clip_len * 1000) for i in range(1, n)]
    fc = ["[0:v]subtitles=" + f"{WORK}/cap.ass" + "[v]"]
    sfx_labels = ""
    if cuts:
        split_labels = "".join(f"[s{i}]" for i in range(len(cuts)))
        fc.append(f"[3:a]volume=0.55,asplit={len(cuts)}{split_labels}" if len(cuts) > 1
                  else "[3:a]volume=0.55[s0]")
        for i, t in enumerate(cuts):
            fc.append(f"[s{i}]adelay={t}|{t}[d{i}]")
            sfx_labels += f"[d{i}]"
    fc.append(f"[1:a]apad[vo];[2:a]volume={MUSIC_VOLUME}[mu]")
    fc.append(f"[vo][mu]{sfx_labels}amix=inputs={2 + len(cuts)}:normalize=0:duration=longest[a]")

    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", f"{WORK}/list.txt",
         "-i", audio, "-i", music, "-i", sfx,
         "-filter_complex", ";".join(fc),
         "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}",
         "-c:v", "libx264", "-preset", "veryfast",
         "-pix_fmt", "yuv420p", "-r", "30", "-profile:v", "high", "-level", "4.0",
         "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
         "-movflags", "+faststart", out_path],
        check=True, capture_output=True)


# ---------- 7. post to Instagram ----------
def upload_public(path):
    """Put the video on a free temporary public link (no account needed)."""
    hosts = [
        ("https://litterbox.catbox.moe/resources/internals/api.php", {"reqtype": "fileupload", "time": "1h"}),
        ("https://catbox.moe/user/api.php", {"reqtype": "fileupload"}),
    ]
    for url, extra in hosts:
        try:
            with open(path, "rb") as f:
                r = requests.post(url, data=extra,
                                  files={"fileToUpload": ("reel.mp4", f, "video/mp4")}, timeout=300)
            print("Host", url.split("/")[2], r.status_code, r.text[:200])
            if r.ok and r.text.strip().startswith("http"):
                return r.text.strip()
        except Exception as e:
            print("Host failed:", url, e)
    raise RuntimeError("no public host worked")


def container_from_url(path, caption):
    video_url = upload_public(path)
    print("Public video URL:", video_url)
    r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
        "media_type": "REELS", "video_url": video_url,
        "caption": caption, "access_token": IG_TOKEN})
    print("Container (url) response:", r.status_code, r.text[:300])
    r.raise_for_status()
    return r.json()["id"]


def container_resumable(path, caption):
    r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
        "media_type": "REELS", "upload_type": "resumable",
        "caption": caption, "access_token": IG_TOKEN})
    print("Container (resumable) response:", r.status_code, r.text[:300])
    r.raise_for_status()
    cid = r.json()["id"]
    uri = r.json().get("uri") or f"https://rupload.facebook.com/ig-api-upload/v21.0/{cid}"
    with open(path, "rb") as f:
        data = f.read()
    u = requests.post(uri, headers={
        "Authorization": f"OAuth {IG_TOKEN}", "offset": "0",
        "file_size": str(len(data)),
        "Content-Type": "application/octet-stream"}, data=data, timeout=900)
    print("Upload response:", u.status_code, u.text[:500])
    u.raise_for_status()
    return cid


def post_reel(path, caption):
    cid = None
    for attempt in range(1, 6):          # Meta's direct upload fails at random, so retry
        try:
            cid = container_resumable(path, caption)
            break
        except Exception as e:
            print(f"Direct upload attempt {attempt}/5 failed:", e)
            time.sleep(25)
    if cid is None:
        print("Trying public-link method as a last resort")
        cid = container_from_url(path, caption)
    for _ in range(60):
        s = requests.get(f"{GRAPH}/{cid}", params={
            "fields": "status_code,status", "access_token": IG_TOKEN}).json()
        print("Status:", s)
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"IG processing error: {s}")
        time.sleep(10)
    p = requests.post(f"{GRAPH}/{IG_USER_ID}/media_publish", data={
        "creation_id": cid, "access_token": IG_TOKEN})
    print("Publish response:", p.status_code, p.text[:300])
    p.raise_for_status()
    print("Posted:", p.json())


# ---------- main ----------
def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else None
    if not state or state["next"] > PARTS:
        state = {"story": gen_story(), "next": 1}
        json.dump(state, open(STATE, "w"), indent=2)   # keep the story even if posting fails
    story, n = state["story"], state["next"]
    part = story["parts"][n - 1]

    out = f"{WORK}/part{n}.mp4"
    build_video(part, out, story.get("visual_style", ""))

    hook = part["narration"].split(".")[0].strip() + "."
    tail = f"Follow for Part {n + 1}/{PARTS} 👇" if n < PARTS else "The end. Want another story? Follow! 🔔"
    caption = f"{story['title']} | Part {n}/{PARTS}\n\n{hook}\n\n{tail}\n\n{' '.join(story['hashtags'])}"
    post_reel(out, caption)

    state["next"] = n + 1
    json.dump(state, open(STATE, "w"), indent=2)


if __name__ == "__main__":
    main()
