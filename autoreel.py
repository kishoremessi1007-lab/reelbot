"""
=============================================================================
🎬 Auto ReelBot: Serialized 3D Character Comedy & Story Generator
=============================================================================
Generates 100% zero-blink, viral serialized multi-part comedy reels matching
the viral format: Urulai Inspector (Potato Cop 🥔) vs Thaluku Thakkali (Tomato 🍅),
plus supporting cast: Thengai Akka (Coconut 🥥), Maangai (Mango 🥭),
Paavakkai (Bitter Gourd 🥒), Vengayam (Onion 🧅), and Strawberry 🍓!

Features:
- 🎭 Multiple Serialized Comedy Series (3-part sagas with cliffhangers):
  1. Series 1: The Auto Signal Speed Trap (ஆட்டோ பஞ்சாயத்து)
  2. Series 2: The Great Chutney Conspiracy (சட்னி சதித்திட்டம்)
  3. Series 3: Tomato Billionaire - Gold Rate Crisis (விலை உயர்வு கலாட்டா)
  * Advances automatically Part 1 -> Part 2 -> Part 3 -> Next Series!
- 🎬 100% Zero-Blink 30 FPS Ping-Pong Video Loops of Real 3D Characters
- 🎙️ Natural Human Voices (Zero Robotic Distortion):
  * Tamil: ta-IN-ValluvarNeural (Cop) + ta-IN-PallaviNeural (Tomato/Cast)
  * English: en-US-ChristopherNeural (Cop) + en-US-GuyNeural (Tomato)
  * Pluggable ElevenLabs support (ELEVENLABS_API_KEY)
- 🔊 Dynamic Sound Effects (Whistles, punches, boings, dramatic hits) + BGM
- 🏷️ Styled Speaker Badges + 2-Line Subtitles with Drop Shadows
- 📲 Automated Daily Posting to Instagram Stories, Instagram Reels & YouTube Shorts
=============================================================================
"""
import os
import sys
import json
import asyncio
import subprocess
import time
import requests
from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = "ffmpeg"

import edge_tts
from youtube_uploader import upload_youtube_short

# Configuration & Secrets
IG_USER_ID = os.environ.get("IG_USER_ID", "").strip()
IG_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "").strip()
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
LANGUAGE = os.environ.get("LANGUAGE", "tamil").lower().strip() # "tamil" or "english"

POST_TO_STORIES = os.environ.get("POST_TO_STORIES", "1") == "1"
POST_TO_REELS = os.environ.get("POST_TO_REELS", "1") == "1"
POST_TO_YOUTUBE = os.environ.get("POST_TO_YOUTUBE", "1") == "1"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR = os.path.join(BASE_DIR, "assets", "video_clips")
SFX_DIR = os.path.join(BASE_DIR, "assets", "sfx")
MUSIC_DIR = os.path.join(BASE_DIR, "assets", "music")
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")
FONT_PATH = os.path.join(FONTS_DIR, "TamilFont.ttf")
WORK_DIR = os.path.join(BASE_DIR, "work")
STATE_FILE = os.path.join(BASE_DIR, "state.json")
GRAPH = "https://graph.facebook.com/v21.0"

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(SFX_DIR, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)
os.makedirs(WORK_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. HILARIOUS CHARACTER COMEDY SERIES CATALOG (Multiple Episodes)
# ---------------------------------------------------------------------------
COMEDY_SERIES_CATALOG = [
    # SERIES 1: The Auto Signal Speed Trap
    {
        "series_id": "auto_speed_trap",
        "series_title": "Urulai Cop vs Thaluku Thakkali",
        "tamil_title": "உரிச்ச உருளை vs தளுக்கு தக்காளி",
        "tags": ["tamilcomedy", "urulaicop", "thakkali", "comedyreels", "shorts", "reels", "viralcomedy"],
        "parts": [
            {
                "part_num": 1,
                "title": "Part 1: The Auto Signal Speed Trap",
                "cliffhanger": {
                    "question_en": "Will Thakkali escape the Sambar pot?",
                    "question_ta": "தக்காளி தப்பிப்பானா? மாட்டிக்கொள்வானா?",
                    "cta": "Follow & Subscribe for Part 2 Tomorrow! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "urulai_cop",
                        "badge": "URULAI INSPECTOR",
                        "clip_src": "urulai_talk_1.mp4",
                        "tamil_text": "டேய் தளுக்கு முழுக்கு தக்காளி! ஒழுங்கா நில்லுடா!",
                        "tanglish_text": "Dei Thaluku Muluku Thakkali!\nOzhunga Nilluda!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "police_whistle.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "THALUKU THAKKALI",
                        "clip_src": "thakkali_talk_1.mp4",
                        "tamil_text": "சார் நான் ஒன்னும் தப்பு பண்ணல சார்! ஆட்டோ ஓட்டி பொழப்பு நடத்துறேன்!",
                        "tanglish_text": "Sir naan onnum thappu pannala sir!\nAuto otti pozhappu nadathuren!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "funny_whistle.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "URULAI INSPECTOR",
                        "clip_src": "urulai_point_finger.mp4",
                        "tamil_text": "ஆட்டோ ஓட்டுறதுக்கும் உன் அடைமொழிக்கும் என்னலே சம்பந்தம்?! இன்னும் பேசுனா சாம்பார்ல வேக வச்சுருவேன்!",
                        "tanglish_text": "Auto otturadhukkum ada mozhikkum\nennale sambandham?! Sambar-la vendhuruva!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "punch_thud.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "THALUKU THAKKALI",
                        "clip_src": "thakkali_talk_2.mp4",
                        "tamil_text": "சார் தக்காளி விலை ஏறுனா நாங்க என்ன பண்ணுவோம்? எங்களை குருமாவுல போடுங்க, சாம்பார் வேண்டாம்!",
                        "tanglish_text": "Thakkali rate yeruna naanga enna pannuvom?\nKurma-la podunga, sambar vendaam!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "boing.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "URULAI INSPECTOR",
                        "clip_src": "urulai_talk_3.mp4",
                        "tamil_text": "டேய் சைலன்ஸ்! உனக்கு நாளைக்கு இருக்கு தண்டனை! ஜெயில்ல தள்ளுறேன்டா!",
                        "tanglish_text": "Dei Silence! Unakku naalaikku\nirukku thandanai! Jail-la thalluren da!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            },
            {
                "part_num": 2,
                "title": "Part 2: The Witnesses Arrive",
                "cliffhanger": {
                    "question_en": "What secret will Bitter Gourd reveal?",
                    "question_ta": "பாகற்காய் என்ன ரகசியம் சொல்ல போகிறான்?",
                    "cta": "Watch Final Part 3 Tomorrow! Follow! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "thakkali",
                        "badge": "THALUKU THAKKALI",
                        "clip_src": "thakkali_ooh.mp4",
                        "tamil_text": "சார்! நான் சாட்சிக்கு தேங்காய் அக்காவையும் மாங்காய் அண்ணியையும் கூட்டிட்டு வந்துட்டேன்!",
                        "tanglish_text": "Sir! Saatchikku Thengai akkavaiyum\nMaangai anniyaiyum koottitu vandhutten!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "funny_whistle.wav"
                    },
                    {
                        "speaker": "thengai",
                        "badge": "THENGAI AKKA",
                        "clip_src": "thengai_shy.mp4",
                        "tamil_text": "ஆமாங்க சார், தக்காளி தம்பி நேத்து முழுக்க சட்னி அரைக்க கூட போகல, ரொம்ப நல்ல பையன் சார்!",
                        "tanglish_text": "Aamanga sir, Thakkali thambi nalla paiyan!\nChutney araikka kooda pogala!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-JennyNeural",
                        "sfx": "boing.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "URULAI INSPECTOR",
                        "clip_src": "urulai_mustache.mp4",
                        "tamil_text": "ஏய் சட்னி கில்டி கதையெல்லாம் என்கிட்ட விடாதீங்க! நான் யாரு தெரியுமா? உரிச்சு வச்ச உருளைடா!",
                        "tanglish_text": "Chutney story-ellam enkitta vendaam!\nNaan yaaru theriyuma? Urulai da!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "police_whistle.wav"
                    },
                    {
                        "speaker": "vengayam",
                        "badge": "VENGAYAM",
                        "clip_src": "vengayam_talk.mp4",
                        "tamil_text": "சார் நீங்க பேசாம இவனை பிரியாணில சேர்க்க சொல்லுங்க, சாம்பார விட அங்க தான் கௌரவம்!",
                        "tanglish_text": "Sir ivana Biryani-la serkka sollunga!\nSambar-a vida anga dhaan gethu!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "punch_thud.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "URULAI INSPECTOR",
                        "clip_src": "urulai_angry_stop.mp4",
                        "tamil_text": "டேய் வெங்காயம்! நடுவுல வந்து அழுது கண்ணீர் வர வைக்காத! நாளைக்கு பாக்ஸ்ல பூட்டுறேன்டா!",
                        "tanglish_text": "Dei Vengayam! Naduvula azhadha!\nNaalaikku box-la pooturen da!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            },
            {
                "part_num": 3,
                "title": "Part 3: The Secret in the Potato Bowl",
                "cliffhanger": {
                    "question_en": "Who is the next vegetable criminal?",
                    "question_ta": "அடுத்த எபிசோடில் யார் சிக்குவார்கள்?",
                    "cta": "Follow for Brand New Episode Tomorrow! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "paavakkai",
                        "badge": "PAAVAKKAI",
                        "clip_src": "paavakkai_cry.mp4",
                        "tamil_text": "சார் சார்! நான் ஒரு பெரிய உண்மையை கண்டுபுடிச்சிட்டேன்! உருளை சாருக்கு தோல் உரிக்கவே இல்லையாம்!",
                        "tanglish_text": "Sir sir! Oru periya unmai kandupidichitten!\nUrulai sir thol urikkave illaiyam!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "funny_whistle.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "URULAI INSPECTOR",
                        "clip_src": "urulai_potato_bowl.mp4",
                        "tamil_text": "டேய் பாகற்காய்! இந்த மேஜைல இருக்குற வேகவச்ச உருளையை பாரு! என் மாமனாரையே வேக வச்சுட்டாங்கடா!",
                        "tanglish_text": "Dei Paavakkai! Indha bowl-a paaru!\nEn maamanaare vendhuttaaru da!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "punch_thud.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "THALUKU THAKKALI",
                        "clip_src": "thakkali_laugh.mp4",
                        "tamil_text": "அப்போ நாங்க யாரும் ஜெயிலுக்கு போக வேண்டாமா சார்? நாங்க பொரியல் ஆகாம தப்பிச்சுட்டோமா?!",
                        "tanglish_text": "Appo naanga jail-ku poga vendaama sir?\nPoriyal aagama thappichuttoma?!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "boing.wav"
                    },
                    {
                        "speaker": "split_laugh",
                        "badge": "VEGGIE GANG",
                        "clip_src": "split_laugh.mp4",
                        "tamil_text": "ஹா ஹா ஹா! உருளை போலீஸ்காரர் மாமனாரு உருளைக்கிழங்கு போண்டாவா போய்ட்டாராம்!",
                        "tanglish_text": "Ha ha ha! Urulai Police maamanaaru\nBonda aayittaaraam!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-JennyNeural",
                        "sfx": "funny_whistle.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "URULAI INSPECTOR",
                        "clip_src": "urulai_talk_3.mp4",
                        "tamil_text": "டேய் தக்காளி! நீ தப்பிச்சுட்டன்னு குதிக்காத! அடுத்த எபிசோட்ல உன்ன மறுபடியும் மடக்குறேன்டா!",
                        "tanglish_text": "Dei Thakkali! Next episode-la unna\nmarubadiyum madakkuren da!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            }
        ]
    },

    # SERIES 2: The Great Chutney Conspiracy
    {
        "series_id": "chutney_conspiracy",
        "series_title": "The Great Chutney Conspiracy",
        "tamil_title": "சட்னி சதித்திட்டம்: யார் திருடன்?",
        "tags": ["tamilcomedy", "urulaicop", "foodcomedy", "reels", "shorts", "tamilfunny"],
        "parts": [
            {
                "part_num": 1,
                "title": "Part 1: The Missing Mustard Seeds",
                "cliffhanger": {
                    "question_en": "Did Tomato steal the curry leaves?",
                    "question_ta": "கருவேப்பிலையை தக்காளி திருடினானா?",
                    "cta": "Follow for Part 2 Tomorrow! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "urulai_cop",
                        "badge": "URULAI INSPECTOR",
                        "clip_src": "urulai_talk_1.mp4",
                        "tamil_text": "அனைவரும் அமைதி! நேத்து ராத்திரி கிச்சன்ல கடுகு தாளிச்சது யார்?! உண்மையை சொல்லுங்க!",
                        "tanglish_text": "Anaivarum amaidhi! Night kitchen-la\nkadugu thalichadhu yaaru?! Sollunga!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "police_whistle.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "THALUKU THAKKALI",
                        "clip_src": "thakkali_talk_1.mp4",
                        "tamil_text": "சார்! எனக்கு சட்னினா பயம் சார்! நான் சாம்பார்ல மட்டுமே குளிக்கிற டீசன்ட் தக்காளி!",
                        "tanglish_text": "Sir! Enakku chutneena bayam sir!\nNaan Sambar-la mattum dhaan kulippen!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "funny_whistle.wav"
                    },
                    {
                        "speaker": "thengai",
                        "badge": "THENGAI AKKA",
                        "clip_src": "thengai_shy.mp4",
                        "tamil_text": "பொய் சொல்றான் சார்! இவன் தான் மிக்ஸி ஜார் பக்கத்துல ஒளிஞ்சு நின்னுட்டு இருந்தான்!",
                        "tanglish_text": "Poi solraan sir! Ivan dhaan mixie jar\npakkathula olichu ninnuttu irundhaan!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-JennyNeural",
                        "sfx": "boing.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "URULAI INSPECTOR",
                        "clip_src": "urulai_point_finger.mp4",
                        "tamil_text": "அடிப்பாவி! மிக்ஸில போட்டா நீ சட்னி ஆயிருவன்னு தெரிஞ்சும் அங்க போனியாடா?!",
                        "tanglish_text": "Mixie-la potta chutney aayiduva-nu\ntherinjum anga ponaiya da?!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "punch_thud.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "THALUKU THAKKALI",
                        "clip_src": "thakkali_ooh.mp4",
                        "tamil_text": "சார் நான் மிக்ஸிய ஆன் பண்ணல! செல்பி எடுக்க தான் சார் போனேன்!",
                        "tanglish_text": "Sir naan mixie-a on pannala!\nSelfie edukka dhaan sir ponen!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            }
        ]
    }
]

# ---------------------------------------------------------------------------
# 2. AUDIO SYNTHESIS (Zero Robotic Pitch Distortion)
# ---------------------------------------------------------------------------
def get_audio_duration(path):
    p = subprocess.run([FFMPEG, "-i", path], stderr=subprocess.PIPE, text=True, errors="ignore")
    for line in p.stderr.splitlines():
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
    return 3.0

async def synthesize_edge(text, voice, out_path):
    """Zero pitch distortion ensures smooth, natural human cadence."""
    for attempt in range(4):
        try:
            c = edge_tts.Communicate(text, voice, pitch="+0Hz", rate="+0%")
            await c.save(out_path)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                return
        except Exception as e:
            if attempt == 3:
                raise e
            await asyncio.sleep(1.2)

def generate_speech(text, voice_ta, voice_en, out_path):
    # ElevenLabs Hyper-realistic voice option
    if ELEVENLABS_KEY:
        try:
            el_voice = "pNInz6obpgDQGcFmaJgB" if "Valluvar" in voice_ta else "EXAVITQu4vr4xnSDxMaL"
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{el_voice}"
            headers = {"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json"}
            body = {"text": text, "model_id": "eleven_multilingual_v2"}
            r = requests.post(url, json=body, headers=headers, timeout=25)
            if r.ok:
                with open(out_path, "wb") as f: f.write(r.content)
                print(f"🎙️ [ElevenLabs Human Voice] Synthesized: {os.path.basename(out_path)}")
                return
        except Exception as e:
            print("ElevenLabs fallback to natural Edge-TTS:", e)

    # Edge-TTS Natural Voice
    chosen_voice = voice_ta if LANGUAGE == "tamil" else voice_en
    asyncio.run(synthesize_edge(text, chosen_voice, out_path))
    print(f"🎙️ [Natural Neural Voice: {chosen_voice}] Synthesized: {os.path.basename(out_path)}")

# ---------------------------------------------------------------------------
# 3. ZERO-BLINK PING-PONG VIDEO ENGINE
# ---------------------------------------------------------------------------
def make_smooth_pingpong_video(src_clip, target_dur, out_path):
    """
    Creates a 100% seamless forward+reverse pingpong loop of the character video.
    Zero frame blinking, zero strobe, zero jitter at 30 fps!
    """
    pp_unit = os.path.join(WORK_DIR, f"pp_{os.path.basename(src_clip)}")
    if not os.path.exists(pp_unit):
        cmd1 = [
            FFMPEG, "-y", "-i", src_clip,
            "-filter_complex", "[0:v]split[f][r];[r]reverse[rev];[f][rev]concat=n=2:v=1:a=0[v]",
            "-map", "[v]",
            "-c:v", "libx264", "-preset", "ultrafast",
            pp_unit
        ]
        subprocess.run(cmd1, check=True, capture_output=True)

    cmd2 = [
        FFMPEG, "-y",
        "-stream_loop", "-1", "-i", pp_unit,
        "-t", f"{target_dur:.2f}",
        "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,format=yuv420p",
        "-r", "30",
        "-c:v", "libx264", "-preset", "ultrafast",
        out_path
    ]
    subprocess.run(cmd2, check=True, capture_output=True)

def render_dialogue_shot(d, idx):
    audio_path = os.path.join(WORK_DIR, f"audio_{idx}.mp3")
    spoken_text = d["tamil_text"] if LANGUAGE == "tamil" else d["tanglish_text"]
    generate_speech(spoken_text, d["voice_ta"], d["voice_en"], audio_path)
    dur = get_audio_duration(audio_path)
    total_dur = dur + 0.35

    # Character Video
    src_clip = os.path.join(CLIPS_DIR, d["clip_src"])
    if not os.path.exists(src_clip):
        src_clip = os.path.join(CLIPS_DIR, "urulai_talk_1.mp4" if "urulai" in d["speaker"] else "thakkali_talk_1.mp4")

    smooth_video = os.path.join(WORK_DIR, f"smooth_shot_{idx}.mp4")
    make_smooth_pingpong_video(src_clip, total_dur, smooth_video)

    # Subtitle Overlay
    W, H = 720, 1280
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.truetype(FONT_PATH, 32)
    badge_font = ImageFont.truetype(FONT_PATH, 24)

    is_cop = "urulai" in d["speaker"]
    badge_border = (255, 205, 50) if is_cop else (255, 80, 80)
    badge_bg = (30, 25, 10, 230) if is_cop else (35, 10, 10, 230)

    b_box = draw.textbbox((0, 0), d["badge"], font=badge_font)
    bw = b_box[2] - b_box[0] + 32
    bh = b_box[3] - b_box[1] + 14
    bx = (W - bw) // 2
    by = H - 240
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=badge_bg, outline=badge_border, width=2)
    draw.text((bx + 16, by + 6), d["badge"], font=badge_font, fill=(255, 255, 255))

    # Centered 2-line Subtitle with Drop Shadow
    lines = d["tanglish_text"].split("\n")
    sy = H - 170
    for l in lines:
        s_box = draw.textbbox((0, 0), l, font=font)
        sw = s_box[2] - s_box[0]
        sx = (W - sw) // 2
        for ox, oy in [(-2,-2),(2,2),(-2,2),(2,-2),(0,2),(2,0),(0,-2),(-2,0)]:
            draw.text((sx+ox, sy+oy), l, font=font, fill=(0, 0, 0, 255))
        draw.text((sx, sy), l, font=font, fill=(255, 235, 50, 255))
        sy += 44

    overlay_png = os.path.join(WORK_DIR, f"overlay_{idx}.png")
    overlay.save(overlay_png)

    out_clip = os.path.join(WORK_DIR, f"shot_{idx}.mp4")
    sfx_file = os.path.join(SFX_DIR, d.get("sfx", "funny_whistle.wav"))

    # Explicit 44100Hz Stereo normalization
    cmd = [
        FFMPEG, "-y",
        "-i", smooth_video,
        "-i", audio_path,
        "-i", sfx_file,
        "-i", overlay_png,
        "-filter_complex",
        "[0:v][3:v]overlay=0:0[v];"
        "[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=1.0[v_a];"
        "[2:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.55[s_a];"
        "[v_a][s_a]amix=inputs=2:normalize=0[a]",
        "-map", "[v]", "-map", "[a]",
        "-t", f"{total_dur:.2f}",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        out_clip
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"✅ Rendered dialogue shot {idx+1}: {d['speaker']} ({total_dur:.2f}s)")
    return out_clip

def render_cta_card(part_num, cliffhanger, out_clip):
    dur = 4.0
    W, H = 720, 1280
    img = Image.new("RGB", (W, H), (15, 12, 25))
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(FONT_PATH, 38)
    f_mid = ImageFont.truetype(FONT_PATH, 30)
    f_call = ImageFont.truetype(FONT_PATH, 28)

    card_x1, card_y1, card_x2, card_y2 = 45, 340, W - 45, H - 340
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=24, fill=(25, 22, 38), outline=(255, 205, 50), width=3)

    draw.text((W//2, 410), f"PART {part_num} ENDS HERE!", font=f_title, fill=(255, 230, 50), anchor="mm")
    draw.text((W//2, 490), cliffhanger["question_en"], font=f_mid, fill=(255, 255, 255), anchor="mm")
    draw.text((W//2, 535), cliffhanger["question_ta"], font=f_mid, fill=(220, 220, 220), anchor="mm")
    draw.text((W//2, 620), f"PART {part_num + 1} TOMORROW!", font=f_title, fill=(255, 90, 90), anchor="mm")
    draw.text((W//2, 700), cliffhanger["cta"], font=f_call, fill=(255, 215, 0), anchor="mm")

    cta_img_path = os.path.join(WORK_DIR, "cta.jpg")
    img.save(cta_img_path)

    sfx_file = os.path.join(SFX_DIR, "funny_whistle.wav")
    subprocess.run([
        FFMPEG, "-y",
        "-loop", "1", "-i", cta_img_path,
        "-i", sfx_file,
        "-t", str(dur),
        "-vf", "zoompan=z='min(1.0+0.0006*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=120:s=720x1280:fps=30,format=yuv420p",
        "-af", "aformat=sample_rates=44100:channel_layouts=stereo",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        out_clip
    ], check=True, capture_output=True)
    print("✅ Rendered Cliffhanger CTA card")

def build_comedy_episode(part_data, out_final_mp4):
    clip_files = []
    for idx, d in enumerate(part_data["dialogues"]):
        c = render_dialogue_shot(d, idx)
        clip_files.append(c)

    cta_clip = os.path.join(WORK_DIR, "shot_cta.mp4")
    render_cta_card(part_data["part_num"], part_data["cliffhanger"], cta_clip)
    clip_files.append(cta_clip)

    concat_list = os.path.join(WORK_DIR, "concat_smooth.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for c in clip_files:
            f.write(f"file '{c.replace(chr(92), '/')}'\n")

    temp_concat = os.path.join(WORK_DIR, "temp_concat_smooth.mp4")
    subprocess.run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", temp_concat
    ], check=True, capture_output=True)

    total_dur = get_audio_duration(temp_concat)
    bgm_file = os.path.join(MUSIC_DIR, "comedy_bouncy_loop.wav")

    subprocess.run([
        FFMPEG, "-y",
        "-i", temp_concat,
        "-stream_loop", "-1", "-i", bgm_file,
        "-filter_complex",
        f"[1:a]aformat=sample_rates=44100:channel_layouts=stereo,volume=0.14,afade=t=in:d=1,afade=t=out:st={max(total_dur-2, 0):.2f}:d=2[bgm];"
        f"[0:a][bgm]amix=inputs=2:normalize=0:duration=first[a]",
        "-map", "0:v", "-map", "[a]",
        "-t", f"{total_dur:.2f}",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out_final_mp4
    ], check=True, capture_output=True)

    print(f"\n🎉 ZERO-BLINK COMEDY EPISODE GENERATED: {out_final_mp4} ({total_dur:.2f}s)")
    return total_dur

# ---------------------------------------------------------------------------
# 4. SOCIAL MEDIA AUTO-PUBLISHING
# ---------------------------------------------------------------------------
def publish_meta_container(creation_id):
    for _ in range(60):
        s = requests.get(f"{GRAPH}/{creation_id}", params={"fields": "status_code,status", "access_token": IG_TOKEN}).json()
        print("Meta processing status:", s)
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"Instagram media processing failed: {s}")
        time.sleep(10)
    p = requests.post(f"{GRAPH}/{IG_USER_ID}/media_publish", data={"creation_id": creation_id, "access_token": IG_TOKEN})
    p.raise_for_status()
    print("🎉 Instagram published successfully:", p.json())

def post_instagram_story(video_path):
    if not (IG_USER_ID and IG_TOKEN):
        print("ℹ️ IG_USER_ID / IG_ACCESS_TOKEN not set; skipping Instagram Story auto-upload.")
        return
    print("📲 Posting to Instagram Story...")
    r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
        "media_type": "STORIES", "upload_type": "resumable", "access_token": IG_TOKEN
    })
    r.raise_for_status()
    cid = r.json()["id"]
    uri = r.json().get("uri") or f"https://rupload.facebook.com/ig-api-upload/v21.0/{cid}"
    with open(video_path, "rb") as f:
        data = f.read()
    requests.post(uri, headers={
        "Authorization": f"OAuth {IG_TOKEN}", "offset": "0",
        "file_size": str(len(data)), "Content-Type": "application/octet-stream"
    }, data=data, timeout=600).raise_for_status()
    publish_meta_container(cid)

def post_instagram_reel(video_path, caption):
    if not (IG_USER_ID and IG_TOKEN):
        print("ℹ️ IG_USER_ID / IG_ACCESS_TOKEN not set; skipping Instagram Reel auto-upload.")
        return
    print("🎥 Posting to Instagram Reel...")
    r = requests.post(f"{GRAPH}/{IG_USER_ID}/media", data={
        "media_type": "REELS", "upload_type": "resumable", "caption": caption, "access_token": IG_TOKEN
    })
    r.raise_for_status()
    cid = r.json()["id"]
    uri = r.json().get("uri") or f"https://rupload.facebook.com/ig-api-upload/v21.0/{cid}"
    with open(video_path, "rb") as f:
        data = f.read()
    requests.post(uri, headers={
        "Authorization": f"OAuth {IG_TOKEN}", "offset": "0",
        "file_size": str(len(data)), "Content-Type": "application/octet-stream"
    }, data=data, timeout=600).raise_for_status()
    publish_meta_container(cid)

# ---------------------------------------------------------------------------
# 5. STATE & MULTI-SERIES PROGRESSION CONTROLLER
# ---------------------------------------------------------------------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def get_next_series(history):
    used = set(history[-len(COMEDY_SERIES_CATALOG)+1:]) if history else set()
    available = [s for s in COMEDY_SERIES_CATALOG if s["series_id"] not in used]
    if not available:
        available = COMEDY_SERIES_CATALOG
    return available[0]

def main():
    state = load_state()
    history = (state or {}).get("series_history", [])

    # Check if we need to initialize or advance to next comedy series
    if not state or "series_id" not in state or state.get("next_part", 1) > len(state.get("parts", [])):
        new_series = get_next_series(history)
        state = {
            "series_id": new_series["series_id"],
            "series_title": new_series["series_title"],
            "next_part": 1,
            "parts": new_series["parts"],
            "tags": new_series.get("tags", ["tamilcomedy", "shorts", "reels"]),
            "series_history": history + [new_series["series_id"]]
        }
        save_state(state)
        print(f"\n🌟 ROTATED TO NEW COMEDY SERIES: {state['series_title']}")

    curr_part_num = state["next_part"]
    part_data = state["parts"][curr_part_num - 1]
    total_parts = len(state["parts"])

    print(f"\n=======================================================")
    print(f"🎬 SERIES: {state['series_title']} | Part {curr_part_num}/{total_parts}")
    print(f"=======================================================\n")

    out_video = os.path.join(WORK_DIR, f"episode_part_{curr_part_num}.mp4")
    build_comedy_episode(part_data, out_video)

    # Save to root sample path
    root_sample = os.path.join(os.path.dirname(BASE_DIR), f"sample_generated_tamil_comedy_part{curr_part_num}.mp4")
    try:
        import shutil
        shutil.copyfile(out_video, root_sample)
    except Exception:
        pass

    # Captions & Tags
    hook = part_data["cliffhanger"]["question_ta"] if LANGUAGE == "tamil" else part_data["cliffhanger"]["question_en"]
    title = f"{state['series_title']} - Part {curr_part_num}/{total_parts}"
    tag_str = " ".join([f"#{t}" for t in state.get("tags", ["tamilcomedy", "shorts", "reels"])])
    caption = (
        f"{title} 😂🍅🥔\n\n"
        f"🔥 {part_data['title']}\n"
        f"❓ {hook}\n\n"
        f"🔔 Follow for Part {curr_part_num + 1} tomorrow at 7 PM!\n\n"
        f"{tag_str}"
    )

    # 1. Instagram Story
    if POST_TO_STORIES:
        try:
            post_instagram_story(out_video)
        except Exception as e:
            print("⚠️ Instagram Story error:", e)

    # 2. Instagram Reel
    if POST_TO_REELS:
        try:
            post_instagram_reel(out_video, caption)
        except Exception as e:
            print("⚠️ Instagram Reel error:", e)

    # 3. YouTube Shorts
    if POST_TO_YOUTUBE:
        try:
            upload_youtube_short(
                video_path=out_video,
                title=f"{state['series_title']} - Part {curr_part_num}/{total_parts} #Shorts",
                description=caption,
                tags=state.get("tags", ["tamilcomedy", "shorts", "reels"])
            )
        except Exception as e:
            print("⚠️ YouTube Shorts error:", e)

    # Advance state to next part
    state["next_part"] += 1
    save_state(state)
    print(f"\n✨ Successfully completed Part {curr_part_num}! Next automated run will progress.")

if __name__ == "__main__":
    main()
