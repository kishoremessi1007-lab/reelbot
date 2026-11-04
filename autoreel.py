"""
=============================================================================
🎬 Auto ReelBot: Multi-Genre 3D Character Saga Generator
=============================================================================
Generates 100% zero-blink, viral serialized multi-part reels across a rich mix
of genres starring our expressive 3D character cast:
- Urulai Inspector (Potato Cop / Detective / Judge / Agent 🥔)
- Thaluku Thakkali (Tomato / Suspect / Accused / Adventurer 🍅)
- Supporting Cast: Thengai Akka (Coconut 🥥), Maangai (Mango 🥭),
  Paavakkai (Bitter Gourd 🥒), Vengayam (Onion 🧅), Strawberry 🍓!

🎭 Dynamic Multi-Genre Catalog (Automatically Rotates Across Series):
  1. 🕵️ Crime & Suspense Thriller (குற்றப் புலனாய்வு) - Midnight Heist Investigation
  2. 👻 Horror & Paranormal Mystery (அமானுஷ்ய திகில்) - The Haunted Pantry Mystery
  3. ⚖️ Courtroom Drama & Objections (நீதிமன்ற யுத்தம்) - The Great Sambar Trial
  4. 🚀 Sci-Fi & Cyberpunk Mission (எதிர்கால அறிவியல்) - Smart Fridge AI Lockout
  5. 😂 Street Comedy & Satire (நகர கலாட்டா) - The Speed Trap & Price Crisis

Features:
- 🎬 100% Zero-Blink 30 FPS Ping-Pong Video Loops of Real 3D Characters
- 🎙️ Natural Human Voices (Zero Robotic Distortion):
  * Tamil: ta-IN-ValluvarNeural (Cop/Lead) + ta-IN-PallaviNeural (Tomato/Cast)
  * English: en-US-ChristopherNeural + en-US-GuyNeural / Jenny
  * Pluggable ElevenLabs support (ELEVENLABS_API_KEY)
- 🎵 Genre-Matched Background Music (Suspense Drone vs Bouncy Comedy)
- 🔊 Dynamic Sound Effects (Gavel strikes, dramatic hits, whistles, punches, impacts)
- 🏷️ Styled Speaker Badges + Genre Header Banner + 2-Line Subtitles with Drop Shadows
- 📲 Automated Publishing to Instagram Reels, Instagram Stories & YouTube Shorts
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

POST_TO_REELS = os.environ.get("POST_TO_REELS", "1") == "1"
POST_TO_STORIES = os.environ.get("POST_TO_STORIES", "1") == "1"
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
# 1. MULTI-GENRE CHARACTER SAGA CATALOG (Crime, Horror, Drama, Sci-Fi, Comedy)
# ---------------------------------------------------------------------------
SERIES_CATALOG = [
    # =======================================================================
    # GENRE 1: CRIME & SUSPENSE THRILLER (குற்றப் புலனாய்வு)
    # =======================================================================
    {
        "series_id": "crime_pantry_heist",
        "genre": "CRIME THRILLER",
        "genre_badge": "🕵️ CRIME THRILLER",
        "series_title": "The Midnight Pantry Heist",
        "tamil_title": "நள்ளிரவு திருடன்: களவு போன குங்குமப்பூ",
        "bgm": "comedy_bouncy_loop.wav",
        "tags": ["crimethriller", "detective", "tamilmystery", "shorts", "reels", "suspense"],
        "parts": [
            {
                "part_num": 1,
                "title": "Part 1: The Broken Lock at 2 AM",
                "cliffhanger": {
                    "question_en": "Who broke the safe at 2:00 AM?",
                    "question_ta": "நள்ளிரவு 2 மணிக்கு லாக்கரை உடைத்தது யார்?",
                    "cta": "Follow for Part 2 Tomorrow! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "urulai_cop",
                        "badge": "DETECTIVE URULAI",
                        "clip_src": "urulai_walk_in.mp4",
                        "tamil_text": "அனைவரும் அசையாமல் நில்லுங்கள்! கிச்சன் லாக்கர்ல இருந்த குங்குமப்பூ டப்பா காணாம போயிருக்கு!",
                        "tanglish_text": "Anaivarum asaiyaamal nillungal!\nKitchen safe kungumapoo box missing!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "SUSPECT THAKKALI",
                        "clip_src": "thakkali_ooh.mp4",
                        "tamil_text": "சார்! நான் நேத்து ராத்திரி முழுக்க ஃப்ரிட்ஜ் டோர் பின்னாடி தூங்கிட்டு தான் சார் இருந்தேன்!",
                        "tanglish_text": "Sir! Naan night fulla fridge door\npinnaadi dhaan thoongittu irundhen sir!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "impact.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "DETECTIVE URULAI",
                        "clip_src": "urulai_point_finger.mp4",
                        "tamil_text": "தூங்குனியா? அப்போ அந்த லாக்கர் பக்கத்துல கிடந்த சிவப்பு தக்காளி விதைகளுக்கு என்ன பதில்?!",
                        "tanglish_text": "Thoonguniya? Appo locker pakkathula\nkidantha red tomato seeds-ku enna badhil?!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "punch_thud.wav"
                    },
                    {
                        "speaker": "thengai",
                        "badge": "WITNESS THENGAI",
                        "clip_src": "thengai_shy.mp4",
                        "tamil_text": "இன்ஸ்பெக்டர் சார்! நான் ஒன்னு பார்த்தேன்... லாக்கர் பக்கம் ஒரு பெரிய நிழல் நடந்து போச்சு!",
                        "tanglish_text": "Inspector sir! Naan onnu paarthen...\nLocker pakkam oru periya shadow pochu!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-JennyNeural",
                        "sfx": "whoosh.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "DETECTIVE URULAI",
                        "clip_src": "urulai_talk_3.mp4",
                        "tamil_text": "பெரிய நிழலா?! இந்த கிச்சன்ல ஒரு பெரிய சதி நடக்குது! கைரேகை டெஸ்ட் எடுக்கிறேன்டா!",
                        "tanglish_text": "Periya shadow-va?! Indha kitchen-la\noru periya sadhi! Fingerprint edukkurom!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            },
            {
                "part_num": 2,
                "title": "Part 2: The Red Footprint Clue",
                "cliffhanger": {
                    "question_en": "Whose footprint was on the flour bag?",
                    "question_ta": "மைதா மாவு மூட்டை மேல இருந்தது யாருடைய காலடி?",
                    "cta": "Watch Climax Part 3 Tomorrow! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "paavakkai",
                        "badge": "PAAVAKKAI",
                        "clip_src": "paavakkai_cry.mp4",
                        "tamil_text": "சார்! மைதா மாவு மூட்டை மேல சின்னதா ஒரு விரல் தடம் இருக்கு சார்! யாரோ ஓடி போயிருக்காங்க!",
                        "tanglish_text": "Sir! Maida mookai mela oru footprint\nirukku sir! Yaaro odi poirukaanga!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "impact.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "DETECTIVE URULAI",
                        "clip_src": "urulai_mustache.mp4",
                        "tamil_text": "மீசையை முறுக்குறேன்... குற்றவாளி ரொம்ப பக்கத்துல தான் இருக்கான்! வெங்காயம்! முன்னாடி வா!",
                        "tanglish_text": "Meesaiyai murukkuren... Criminal romba\npakkathula dhaan irukaan! Vengayam come here!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "police_whistle.wav"
                    },
                    {
                        "speaker": "vengayam",
                        "badge": "VENGAYAM",
                        "clip_src": "vengayam_talk.mp4",
                        "tamil_text": "சார்! என் கண்ணுல வர்றது குற்ற உணர்ச்சி இல்ல சார், இயற்கை குணம்! நான் குங்குமப்பூவை தொடவே இல்ல!",
                        "tanglish_text": "Sir! En kanneer thappu illa sir!\nNaan saffron thodave illa sir!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "punch_thud.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "THALUKU THAKKALI",
                        "clip_src": "thakkali_talk_1.mp4",
                        "tamil_text": "சார் எனக்கு ஒரு சந்தேகம்! அந்த சிசிடிவி கேமரா பக்கத்துல நின்னது யாருன்னு பாருங்க!",
                        "tanglish_text": "Sir enakku oru doubt! CCTV camera\npakkathula ninnadhu yaaru-nu paarunga!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "whoosh.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "DETECTIVE URULAI",
                        "clip_src": "urulai_angry_stop.mp4",
                        "tamil_text": "சிசிடிவி ஃபுட்டேஜ் வந்துருச்சு! அடுத்த 10 நிமிஷத்துல திருடன் யாருன்னு வெளிச்சத்துக்கு வரும்!",
                        "tanglish_text": "CCTV footage vandhuruchu!\nNext 10 mins-la thief maatuvaan da!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            },
            {
                "part_num": 3,
                "title": "Part 3: The CCTV Revelation",
                "cliffhanger": {
                    "question_en": "Case Closed! Who will be the next suspect?",
                    "question_ta": "வழக்கு முடிந்தது! அடுத்த வழக்கில் யார் சிக்குவார்கள்?",
                    "cta": "Follow for Brand New Mystery Saga! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "urulai_cop",
                        "badge": "DETECTIVE URULAI",
                        "clip_src": "urulai_talk_1.mp4",
                        "tamil_text": "வீடியோவ பாருங்கடா! குங்குமப்பூவை எடுத்தது இந்த மாங்காய் அண்ணி தான்!",
                        "tanglish_text": "Video paarunga da! Kungumapoo\neduthadhu indha Maangai dhaan!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    },
                    {
                        "speaker": "maangai",
                        "badge": "MAANGAI",
                        "clip_src": "maangai_smile.mp4",
                        "tamil_text": "அய்யோ சார்! மாங்காய் பச்சடிக்கு கொஞ்சம் கலர் பத்தலன்னு தான் ஒரே ஒரு சிட்டிகை எடுத்தேன் சார்!",
                        "tanglish_text": "Aiyo sir! Pachadi-ku color pathala-nu\nore oru pinch dhaan eduthen sir!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-JennyNeural",
                        "sfx": "boing.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "THALUKU THAKKALI",
                        "clip_src": "thakkali_laugh.mp4",
                        "tamil_text": "அப்பாடா! அப்போ என் மேல தப்பு இல்ல! தக்காளி தம்பி நேர்மையானவன்னு ஊருக்கே தெரிஞ்சிருச்சு!",
                        "tanglish_text": "Appada! En mela thappu illa!\nThakkali honest-nu therinjuruchu!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "funny_whistle.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "DETECTIVE URULAI",
                        "clip_src": "urulai_talk_3.mp4",
                        "tamil_text": "டேய் தக்காளி ரொம்ப குதிக்காத! நாளைக்கு உனக்கு ஒரு புது கேஸ் காத்துட்டு இருக்குடா!",
                        "tanglish_text": "Dei Thakkali kudhikaadha!\nNaalaikku unakku pudhu case irukku da!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            }
        ]
    },

    # =======================================================================
    # GENRE 2: HORROR & PARANORMAL MYSTERY (அமானுஷ்ய திகில்)
    # =======================================================================
    {
        "series_id": "horror_haunted_pantry",
        "genre": "HORROR MYSTERY",
        "genre_badge": "👻 HORROR MYSTERY",
        "series_title": "The Haunted Kitchen at 3 AM",
        "tamil_title": "அமானுஷ்ய சமையலறை: நள்ளிரவு பேய் சத்தம்",
        "bgm": "comedy_bouncy_loop.wav",
        "tags": ["horrortamil", "hauntedkitchen", "paranormal", "shorts", "reels", "ghoststory"],
        "parts": [
            {
                "part_num": 1,
                "title": "Part 1: The Whispers in the Dark",
                "cliffhanger": {
                    "question_en": "What made the mixer turn on at 3 AM?",
                    "question_ta": "நள்ளிரவு 3 மணிக்கு மிக்ஸியை ஆன் செய்தது யார்?",
                    "cta": "Follow for Spine-Chilling Part 2! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "thakkali",
                        "badge": "TERRIFIED THAKKALI",
                        "clip_src": "thakkali_ooh.mp4",
                        "tamil_text": "சார்! யாராவது இருக்கீங்களா? நள்ளிரவு 3 மணிக்கு மிக்ஸி ஜார் தன்னால சுத்துது சார்!",
                        "tanglish_text": "Sir! Yaaraavadhu irukeengala?\nMidnight 3 AM mixie auto on aagudhu!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "whoosh.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "INSPECTOR URULAI",
                        "clip_src": "urulai_walk_in.mp4",
                        "tamil_text": "டேய் பயப்படாதடா! பேய் பிசாசு எல்லாம் கட்டுக்கதை! கரண்ட் லீக்கா இருக்கும்!",
                        "tanglish_text": "Dei bayapadadha da! Ghost-ellam myth!\nCurrent leak-a irukkum!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    },
                    {
                        "speaker": "crowd_shock",
                        "badge": "VEGGIE GANG",
                        "clip_src": "crowd_shock.mp4",
                        "tamil_text": "சார் கரண்ட் இல்ல சார்! மெயின் சுவிட்சே ஆஃப்ல இருக்கு! அப்புறம் எப்படி ஓடுது?!",
                        "tanglish_text": "Sir power illa sir! Main switch off!\nAppuram eppadi mixie running?!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-JennyNeural",
                        "sfx": "impact.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "INSPECTOR URULAI",
                        "clip_src": "urulai_potato_bowl.mp4",
                        "tamil_text": "என்னது?! கரண்ட் இல்லாம சுத்துதா?! இந்த மேஜைல இருக்குற வேகவச்ச உருளை கூட ஆட ஆரம்பிக்குதேடா!",
                        "tanglish_text": "Ennadhu?! Current illama running-a?!\nIndha boiled potato kooda aadhudhe da!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            },
            {
                "part_num": 2,
                "title": "Part 2: The Green Floating Mist",
                "cliffhanger": {
                    "question_en": "What emerged from behind the chimney?",
                    "question_ta": "புகைபோக்கிக்கு பின்னால் இருந்து வந்தது என்ன?",
                    "cta": "Watch Final Part 3 Tomorrow! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "paavakkai",
                        "badge": "SHIVERING BITTER GOURD",
                        "clip_src": "paavakkai_cry.mp4",
                        "tamil_text": "சார்! சிம்னிக்கு மேல ஒரு பச்சை கலர் புகை மெதக்குது சார்! காப்பாத்துங்க!",
                        "tanglish_text": "Sir! Chimney mela green color smoke\nfloating sir! Kaappaathunga!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "whoosh.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "INSPECTOR URULAI",
                        "clip_src": "urulai_point_finger.mp4",
                        "tamil_text": "யார்ரா அது புகைபோக்கிக்கு பின்னாடி ஒளிஞ்சிருக்கிறது?! முன்னாடி வாடா தைரியம் இருந்தா!",
                        "tanglish_text": "Yaar-ra adhu chimney pinnaadi?\nMunnadi vaa da dhairiyam irundha!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "punch_thud.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "TERRIFIED THAKKALI",
                        "clip_src": "thakkali_listen.mp4",
                        "tamil_text": "சார் அது பேச ஆரம்பிக்குது சார்! 'சட்னி... சட்னி...' ன்னு முனங்குது சார்!",
                        "tanglish_text": "Sir adhu pesudhu sir!\n'Chutney... Chutney...' nu soludhu sir!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "dramatic_hit.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "INSPECTOR URULAI",
                        "clip_src": "urulai_angry_stop.mp4",
                        "tamil_text": "டேய் பேயா இருந்தாலும் சரி, பிசாசா இருந்தாலும் சரி! சமையலறை ரூல்ஸ மீறினா ஜெயில் தான்டா!",
                        "tanglish_text": "Ghost-a irundhalum kitchen rules\nmeerina jail dhaan da!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "police_whistle.wav"
                    }
                ]
            },
            {
                "part_num": 3,
                "title": "Part 3: The Secret Behind the Mist",
                "cliffhanger": {
                    "question_en": "Mystery solved! Which genre do you want next?",
                    "question_ta": "மர்மம் விலகியது! அடுத்த எபிசோடில் எந்த கதை வேண்டும்?",
                    "cta": "Comment Below & Subscribe! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "vengayam",
                        "badge": "SNEAKY VENGAYAM",
                        "clip_src": "vengayam_talk.mp4",
                        "tamil_text": "ஹா ஹா ஹா! பேய் இல்ல சார்! நான்தான் புதினா இலையை சிம்னி ஃபேன்ல மாட்ட வச்சேன்!",
                        "tanglish_text": "Ha ha ha! Ghost illa sir!\nNaan dhaan mint leaves fan-la maatinein!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "boing.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "THALUKU THAKKALI",
                        "clip_src": "thakkali_laugh.mp4",
                        "tamil_text": "அடப்பாவி வெங்காயம்! எங்களை சாகடிச்சிட்டடா பயத்துல! உன்னை அறுத்து சாம்பார்ல போடணும்!",
                        "tanglish_text": "Adappaavi Vengayam! Bayathula\nsaavadichitta! Unna sambar-la podanum!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "funny_whistle.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "INSPECTOR URULAI",
                        "clip_src": "urulai_talk_3.mp4",
                        "tamil_text": "டேய் வெங்காயம்! ஊரையே பயமுறுத்திய குற்றத்துக்காக உனக்கு ஆயுள் தண்டனை! நடடா ஜெயிலுக்கு!",
                        "tanglish_text": "Dei Vengayam! Kitchen-ai bayamuruthina\nunerukku jail dhaan da! Nadada!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            }
        ]
    },

    # =======================================================================
    # GENRE 3: COURTROOM DRAMA & OBJECTIONS (நீதிமன்ற யுத்தம்)
    # =======================================================================
    {
        "series_id": "courtroom_sambar_trial",
        "genre": "COURTROOM DRAMA",
        "genre_badge": "⚖️ COURTROOM DRAMA",
        "series_title": "The Great Sambar Trial",
        "tamil_title": "நீதிமன்ற விசாரணை: தக்காளி குற்றவாளியா?",
        "bgm": "comedy_bouncy_loop.wav",
        "tags": ["courtroomdrama", "tamilcourt", "objection", "shorts", "reels", "lawyer"],
        "parts": [
            {
                "part_num": 1,
                "title": "Part 1: Order in the Court!",
                "cliffhanger": {
                    "question_en": "Will the Judge convict Tomato to the boiling pot?",
                    "question_ta": "தக்காளிக்கு கொதிக்கும் பாத்திர தண்டனை கிடைக்குமா?",
                    "cta": "Follow for Part 2 Tomorrow! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "urulai_cop",
                        "badge": "HONORABLE JUDGE URULAI",
                        "clip_src": "urulai_mustache.mp4",
                        "tamil_text": "சைலன்ஸ்! ஆர்டர் இன் தி கோர்ட்! தக்காளி மேல வைக்கப்பட்ட குற்றச்சாட்டை வாசியுங்கள்!",
                        "tanglish_text": "Silence! Order in the Court!\nRead the charges against Tomato!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    },
                    {
                        "speaker": "paavakkai",
                        "badge": "PUBLIC PROSECUTOR",
                        "clip_src": "paavakkai_cry.mp4",
                        "tamil_text": "யுவர் ஆனர்! இந்த தக்காளி சாம்பார், ரசம், பிரியாணினு எல்லாத்துலயும் அநாவசியமா நுழைஞ்சு ஆதிக்கம் பண்றான்!",
                        "tanglish_text": "Your Honor! Ivan Sambar, Rasam, Biryani-nu\nellaathulayum over dominance panraan!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "impact.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "DEFENSE THAKKALI",
                        "clip_src": "thakkali_talk_1.mp4",
                        "tamil_text": "அப்ஜெக்ஷன் யுவர் ஆனர்! நான் இல்லன்னா ரசத்துக்கு சுவை யார் தருவா?! இது என் திறமை சார்!",
                        "tanglish_text": "Objection Your Honor! Naan illana\nrasathukku taste yaaru tharuva?!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "punch_thud.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "HONORABLE JUDGE URULAI",
                        "clip_src": "urulai_point_finger.mp4",
                        "tamil_text": "அப்ஜெக்ஷன் ஓவர்ரூல்ட்! தக்காளி வாதம் எடுபடாது! சாட்சி கூண்டுக்கு தேங்காய் அக்காவை அழைக்கிறேன்!",
                        "tanglish_text": "Objection Overruled! Witness box-ku\nThengai Akka-vai azhaikkirom!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            },
            {
                "part_num": 2,
                "title": "Part 2: The Hostile Witness",
                "cliffhanger": {
                    "question_en": "What shocking evidence will turn the trial?",
                    "question_ta": "வழக்கை மாற்றப்போகும் அந்த அதிர்ச்சி ஆதாரம் என்ன?",
                    "cta": "Watch Final Part 3 Tomorrow! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "thengai",
                        "badge": "WITNESS THENGAI",
                        "clip_src": "thengai_shy.mp4",
                        "tamil_text": "யுவர் ஆனர்! தக்காளி தம்பி இல்லன்னா இந்த சமையலறையே இயங்காதுங்க, ரொம்ப நல்ல பையன்!",
                        "tanglish_text": "Your Honor! Thakkali illana\nindha kitchen-e nadakkaadhu, very good boy!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-JennyNeural",
                        "sfx": "boing.wav"
                    },
                    {
                        "speaker": "paavakkai",
                        "badge": "PUBLIC PROSECUTOR",
                        "clip_src": "paavakkai_cry.mp4",
                        "tamil_text": "பொய் சொல்றாங்க! இவங்களுக்குள்ள ரகசிய கூட்டணி இருக்கு! சாட்சியை குறுக்கு விசாரணை செய்ய அனுமதிக்கணும்!",
                        "tanglish_text": "Poi solraanga! Secret alliance irukku!\nCross examine panna allow pannunga!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "impact.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "DEFENSE THAKKALI",
                        "clip_src": "thakkali_ooh.mp4",
                        "tamil_text": "யுவர் ஆனர்! இதோ இந்த ரகசிய ரெசிபி டைரியை பாருங்க! உருளைக்கிழங்கு தான் எல்லாத்துலயும் கூட்டு சேருது!",
                        "tanglish_text": "Your Honor! Indha recipe diary paarunga!\nUrulai dhaan ellaathulayum partner!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "whoosh.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "HONORABLE JUDGE URULAI",
                        "clip_src": "urulai_angry_stop.mp4",
                        "tamil_text": "என்னது?! நீதிபதியையே குற்றம் சாட்டுறியா?! தீர்ப்பு நாளைக்கு காலைல 10 மணிக்கு வழங்கப்படும்!",
                        "tanglish_text": "Ennadhu?! Judge-aiye accuse panriya?!\nVerdict naalaikku 10 AM-ku varum!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            },
            {
                "part_num": 3,
                "title": "Part 3: The Historic Verdict",
                "cliffhanger": {
                    "question_en": "Verdict Delivered! Follow for Next Saga!",
                    "question_ta": "தீர்ப்பு வழங்கப்பட்டது! அடுத்த புதிய கதைக்கு Follow பண்ணுங்க!",
                    "cta": "Subscribe for Tomorrow's Brand New Series! 🔔"
                },
                "dialogues": [
                    {
                        "speaker": "urulai_cop",
                        "badge": "HONORABLE JUDGE URULAI",
                        "clip_src": "urulai_talk_1.mp4",
                        "tamil_text": "அனைத்து ஆதாரங்களையும் ஆராய்ந்ததில்... தக்காளி தம்பி சமையலறையின் இன்றியமையாத ராஜா என தீர்ப்பளிக்கிறேன்!",
                        "tanglish_text": "Ella evidence paarthadhil... Thakkali thambi\nkitchen-in King-nu theerppalikkirom!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    },
                    {
                        "speaker": "thakkali",
                        "badge": "VICTORIOUS THAKKALI",
                        "clip_src": "thakkali_laugh.mp4",
                        "tamil_text": "வெற்றி வெற்றி! நீதி வென்றது! தக்காளி தம்பிக்கு இனி சமையலறை முழுக்க ராஜ மரியாதை!",
                        "tanglish_text": "Vetri vetri! Justice wins!\nThakkali thambi-ku Royal Respect!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-GuyNeural",
                        "sfx": "funny_whistle.wav"
                    },
                    {
                        "speaker": "split_laugh",
                        "badge": "COURT AUDIENCE",
                        "clip_src": "split_laugh.mp4",
                        "tamil_text": "ஹா ஹா ஹா! பாகற்காயோட சதி திட்டம் சொதப்பிடுச்சு!",
                        "tanglish_text": "Ha ha ha! Paavakkai plan\ncompletely failed!",
                        "voice_ta": "ta-IN-PallaviNeural",
                        "voice_en": "en-US-JennyNeural",
                        "sfx": "boing.wav"
                    },
                    {
                        "speaker": "urulai_cop",
                        "badge": "HONORABLE JUDGE URULAI",
                        "clip_src": "urulai_talk_3.mp4",
                        "tamil_text": "நீதிமன்றம் கலைகிறது! அடுத்த வழக்கில் மற்றொரு சாகசம் ஆரம்பமாகும்!",
                        "tanglish_text": "Court adjourned! Next case-la\npudhu episode start aagum!",
                        "voice_ta": "ta-IN-ValluvarNeural",
                        "voice_en": "en-US-ChristopherNeural",
                        "sfx": "dramatic_hit.wav"
                    }
                ]
            }
        ]
    },

    # =======================================================================
    # GENRE 4: STREET COMEDY & SATIRE (நகர கலாட்டா)
    # =======================================================================
    {
        "series_id": "comedy_auto_speed_trap",
        "genre": "COMEDY SATIRE",
        "genre_badge": "😂 COMEDY SATIRE",
        "series_title": "Urulai Cop vs Thaluku Thakkali",
        "tamil_title": "உரிச்ச உருளை vs தளுக்கு தக்காளி: ஆட்டோ பஞ்சாயத்து",
        "bgm": "comedy_bouncy_loop.wav",
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
    for attempt in range(5):
        try:
            c = edge_tts.Communicate(text, voice, pitch="+0Hz", rate="+0%")
            await c.save(out_path)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 500:
                return
        except Exception as e:
            if attempt == 4:
                print(f"❌ Edge-TTS final failure after 5 attempts: {e}")
                raise e
            wait_time = 2.0 * (attempt + 1)
            print(f"⚠️ TTS retry {attempt+1}/5 in {wait_time}s due to: {e}")
            await asyncio.sleep(wait_time)

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
# 3. ZERO-BLINK MULTI-ANGLE CHARACTER VIDEO ENGINE (100% Forward Motion)
# ---------------------------------------------------------------------------
CHARACTER_CLIPS = {
    "urulai_cop": [
        "urulai_talk_1.mp4",
        "urulai_point_finger.mp4",
        "urulai_mustache.mp4",
        "urulai_talk_3.mp4",
        "urulai_talk_2.mp4",
        "urulai_angry_stop.mp4"
    ],
    "thakkali": [
        "thakkali_talk_1.mp4",
        "thakkali_listen.mp4",
        "thakkali_talk_2.mp4",
        "thakkali_smile.mp4",
        "thakkali_polite.mp4",
        "thakkali_ooh.mp4"
    ],
    "thengai": ["thengai_shy.mp4", "thakkali_listen.mp4", "thengai_shy.mp4"],
    "paavakkai": ["paavakkai_cry.mp4", "urulai_point_finger.mp4", "paavakkai_cry.mp4"],
    "vengayam": ["vengayam_talk.mp4", "urulai_angry_stop.mp4", "vengayam_talk.mp4"],
    "maangai": ["maangai_smile.mp4", "thakkali_talk_1.mp4", "maangai_smile.mp4"],
    "crowd_shock": ["crowd_shock.mp4", "urulai_potato_bowl.mp4", "crowd_shock.mp4"],
    "split_laugh": ["split_laugh.mp4", "thakkali_laugh.mp4", "split_laugh.mp4"]
}

def make_smooth_character_video(speaker, target_dur, out_path):
    """
    Plays real sequential camera angles forward at 30 fps.
    Zero reverse motion, zero ping-pong bouncing, zero blinking!
    """
    pool = CHARACTER_CLIPS.get(speaker, CHARACTER_CLIPS["urulai_cop"])
    selected = []
    total = 0.0
    idx = 0
    while total < target_dur:
        c_name = pool[idx % len(pool)]
        c_path = os.path.join(CLIPS_DIR, c_name)
        if os.path.exists(c_path):
            selected.append(c_path)
            p = subprocess.run([FFMPEG, "-i", c_path], stderr=subprocess.PIPE, text=True, errors="ignore")
            dur = 1.4
            for l in p.stderr.splitlines():
                if "Duration:" in l:
                    parts = l.split("Duration:")[1].split(",")[0].strip().split(":")
                    dur = float(parts[0])*3600 + float(parts[1])*60 + float(parts[2])
            total += dur
        idx += 1

    inputs = []
    filter_parts = []
    concat_inputs = ""
    for i, pth in enumerate(selected):
        inputs.extend(["-i", pth])
        filter_parts.append(f"[{i}:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,format=yuv420p,fps=30[v{i}];")
        concat_inputs += f"[v{i}]"
    filter_parts.append(f"{concat_inputs}concat=n={len(selected)}:v=1:a=0[v]")

    cmd = [FFMPEG, "-y"] + inputs + [
        "-filter_complex", "".join(filter_parts),
        "-map", "[v]",
        "-t", f"{target_dur:.2f}",
        "-c:v", "libx264", "-preset", "ultrafast",
        out_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)

def render_dialogue_shot(d, idx, genre_badge, part_str):
    audio_path = os.path.join(WORK_DIR, f"audio_{idx}.mp3")
    spoken_text = d["tamil_text"] if LANGUAGE == "tamil" else d["tanglish_text"]
    generate_speech(spoken_text, d["voice_ta"], d["voice_en"], audio_path)
    dur = get_audio_duration(audio_path)
    total_dur = dur + 0.35

    smooth_video = os.path.join(WORK_DIR, f"smooth_shot_{idx}.mp4")
    make_smooth_character_video(d["speaker"], total_dur, smooth_video)

    # Subtitle Overlay (Clean, uncluttered, no top banners blocking faces)
    W, H = 720, 1280
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.truetype(FONT_PATH, 32)
    badge_font = ImageFont.truetype(FONT_PATH, 24)

    # Speaker Badge
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
    print(f"✅ Rendered shot {idx+1}: {d['speaker']} ({total_dur:.2f}s)")
    return out_clip

def render_cta_card(part_num, cliffhanger, genre_badge, out_clip):
    dur = 4.0
    W, H = 720, 1280
    img = Image.new("RGB", (W, H), (15, 12, 25))
    draw = ImageDraw.Draw(img)

    f_badge = ImageFont.truetype(FONT_PATH, 24)
    f_title = ImageFont.truetype(FONT_PATH, 38)
    f_mid = ImageFont.truetype(FONT_PATH, 30)
    f_call = ImageFont.truetype(FONT_PATH, 28)

    card_x1, card_y1, card_x2, card_y2 = 45, 300, W - 45, H - 300
    draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=24, fill=(25, 22, 38), outline=(255, 205, 50), width=3)

    draw.text((W//2, 345), genre_badge, font=f_badge, fill=(255, 215, 0), anchor="mm")
    draw.text((W//2, 410), f"PART {part_num} ENDS HERE!", font=f_title, fill=(255, 230, 50), anchor="mm")
    draw.text((W//2, 490), cliffhanger["question_en"], font=f_mid, fill=(255, 255, 255), anchor="mm")
    draw.text((W//2, 535), cliffhanger["question_ta"], font=f_mid, fill=(220, 220, 220), anchor="mm")
    draw.text((W//2, 620), f"PART {part_num + 1} TOMORROW!", font=f_title, fill=(255, 90, 90), anchor="mm")
    draw.text((W//2, 700), cliffhanger["cta"], font=f_call, fill=(255, 215, 0), anchor="mm")

    cta_img_path = os.path.join(WORK_DIR, "cta.jpg")
    img.save(cta_img_path)

    sfx_file = os.path.join(SFX_DIR, "dramatic_hit.wav")
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

def build_episode(series_data, part_data, out_final_mp4):
    clip_files = []
    genre_badge = series_data.get("genre_badge", series_data.get("genre", "COMEDY"))
    part_str = f"PART {part_data['part_num']}/{len(series_data['parts'])}"

    for idx, d in enumerate(part_data["dialogues"]):
        c = render_dialogue_shot(d, idx, genre_badge, part_str)
        clip_files.append(c)

    cta_clip = os.path.join(WORK_DIR, "shot_cta.mp4")
    render_cta_card(part_data["part_num"], part_data["cliffhanger"], genre_badge, cta_clip)
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
    bgm_name = series_data.get("bgm", "comedy_bouncy_loop.wav")
    bgm_file = os.path.join(MUSIC_DIR, bgm_name)
    if not os.path.exists(bgm_file):
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

    print(f"\n🎉 ZERO-BLINK [{series_data.get('genre', 'EPISODE')}] GENERATED: {out_final_mp4} ({total_dur:.2f}s)")
    return total_dur

# ---------------------------------------------------------------------------
# 4. SOCIAL MEDIA AUTO-PUBLISHING (Robust Resumable Meta Protocol)
# ---------------------------------------------------------------------------
def publish_meta_container(creation_id):
    print(f"⏳ Waiting for Meta container {creation_id} to finish processing...")
    for attempt in range(40):
        time.sleep(6)
        s_res = requests.get(f"{GRAPH}/{creation_id}", params={"fields": "status_code,status", "access_token": IG_TOKEN})
        if not s_res.ok:
            print(f"⚠️ Meta status check [{s_res.status_code}]: {s_res.text}")
            continue
        s = s_res.json()
        status_code = s.get("status_code")
        print(f"Meta processing status [{attempt+1}/40]: {status_code}")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            raise RuntimeError(f"Instagram media processing failed: {s}")

    pub_res = requests.post(f"{GRAPH}/{IG_USER_ID}/media_publish", data={"creation_id": creation_id, "access_token": IG_TOKEN})
    if not pub_res.ok:
        print(f"❌ Failed to publish Instagram container [{pub_res.status_code}]:")
        print(pub_res.text)
        pub_res.raise_for_status()
    print("🎉 Instagram published successfully! Media ID:", pub_res.json().get("id"))

def post_instagram_reel(video_path, caption):
    if not (IG_USER_ID and IG_TOKEN):
        print("ℹ️ IG_USER_ID / IG_ACCESS_TOKEN not set; skipping Instagram Reel auto-upload.")
        return
    print("🎥 Initializing Instagram Reel upload...")
    init_url = f"{GRAPH}/{IG_USER_ID}/media"
    init_data = {
        "media_type": "REELS",
        "upload_type": "resumable",
        "caption": caption,
        "access_token": IG_TOKEN
    }
    r = requests.post(init_url, data=init_data)
    if not r.ok:
        print(f"❌ Failed to initialize Instagram Reel [{r.status_code}]:")
        print(r.text)
        r.raise_for_status()

    cid = r.json()["id"]
    uri = r.json().get("uri") or f"https://rupload.facebook.com/ig-api-upload/v21.0/{cid}"
    print(f"📦 Created Instagram Reel container: {cid}")

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    file_size = len(video_bytes)
    headers = {
        "Authorization": f"OAuth {IG_TOKEN}",
        "file_offset": "0",
        "offset": "0",
        "file_size": str(file_size),
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4"
    }
    print(f"📤 Uploading video binary ({file_size / (1024*1024):.2f} MB)...")
    upload_res = requests.post(uri, headers=headers, data=video_bytes, timeout=600)
    if not upload_res.ok:
        print(f"❌ Failed to upload video binary to Meta [{upload_res.status_code}]:")
        print(upload_res.text)
        upload_res.raise_for_status()

    publish_meta_container(cid)

def post_instagram_story(video_path):
    if not (IG_USER_ID and IG_TOKEN):
        print("ℹ️ IG_USER_ID / IG_ACCESS_TOKEN not set; skipping Instagram Story auto-upload.")
        return
    print("📲 Initializing Instagram Story upload...")
    try:
        init_url = f"{GRAPH}/{IG_USER_ID}/media"
        init_data = {
            "media_type": "STORIES",
            "upload_type": "resumable",
            "access_token": IG_TOKEN
        }
        r = requests.post(init_url, data=init_data)
        if not r.ok:
            print(f"ℹ️ Instagram Story init [{r.status_code}]: {r.text} (Note: Direct binary upload for Stories requires Instagram Partner approvals; Reels are published successfully).")
            return

        cid = r.json()["id"]
        uri = r.json().get("uri") or f"https://rupload.facebook.com/ig-api-upload/v21.0/{cid}"
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        file_size = len(video_bytes)
        headers = {
            "Authorization": f"OAuth {IG_TOKEN}",
            "file_offset": "0",
            "offset": "0",
            "file_size": str(file_size),
            "Content-Length": str(file_size),
            "Content-Type": "video/mp4"
        }
        upload_res = requests.post(uri, headers=headers, data=video_bytes, timeout=600)
        if upload_res.ok:
            publish_meta_container(cid)
    except Exception as e:
        print("ℹ️ Instagram Story note:", e)

# ---------------------------------------------------------------------------
# 5. STATE & MULTI-GENRE PROGRESSION CONTROLLER
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
    used = set(history[-len(SERIES_CATALOG)+1:]) if history else set()
    available = [s for s in SERIES_CATALOG if s["series_id"] not in used]
    if not available:
        available = SERIES_CATALOG
    return available[0]

def main():
    state = load_state()
    history = (state or {}).get("series_history", [])

    # Advance or initialize multi-genre series
    if not state or "series_id" not in state or state.get("next_part", 1) > len(state.get("parts", [])):
        new_series = get_next_series(history)
        state = {
            "series_id": new_series["series_id"],
            "genre": new_series.get("genre", "COMEDY"),
            "genre_badge": new_series.get("genre_badge", "🎬 COMEDY"),
            "series_title": new_series["series_title"],
            "bgm": new_series.get("bgm", "comedy_bouncy_loop.wav"),
            "next_part": 1,
            "parts": new_series["parts"],
            "tags": new_series.get("tags", ["tamil", "shorts", "reels"]),
            "series_history": history + [new_series["series_id"]]
        }
        save_state(state)
        print(f"\n🌟 ROTATED TO NEW GENRE & SERIES: [{state['genre']}] - {state['series_title']}")

    curr_part_num = state["next_part"]
    part_data = state["parts"][curr_part_num - 1]
    total_parts = len(state["parts"])

    print(f"\n=======================================================")
    print(f"🎬 GENRE: {state.get('genre', 'SERIES')} | {state['series_title']}")
    print(f"📖 Episode Part {curr_part_num}/{total_parts}")
    print(f"=======================================================\n")

    out_video = os.path.join(WORK_DIR, f"episode_part_{curr_part_num}.mp4")
    build_episode(state, part_data, out_video)

    # Save to root sample path
    root_sample = os.path.join(os.path.dirname(BASE_DIR), f"sample_generated_tamil_part{curr_part_num}.mp4")
    try:
        import shutil
        shutil.copyfile(out_video, root_sample)
    except Exception:
        pass

    # Captions & Tags
    hook = part_data["cliffhanger"]["question_ta"] if LANGUAGE == "tamil" else part_data["cliffhanger"]["question_en"]
    genre_badge = state.get("genre_badge", state.get("genre", "🎬 COMEDY"))
    title = f"{genre_badge}: {state['series_title']} - Part {curr_part_num}/{total_parts}"
    tag_str = " ".join([f"#{t}" for t in state.get("tags", ["tamilcomedy", "shorts", "reels"])])
    caption = (
        f"{title}\n\n"
        f"🔥 {part_data['title']}\n"
        f"❓ {hook}\n\n"
        f"🔔 Follow for Part {curr_part_num + 1} tomorrow at 7 PM!\n\n"
        f"{tag_str}"
    )

    # 1. Instagram Reel (Priority Feed Posting)
    if POST_TO_REELS:
        try:
            post_instagram_reel(out_video, caption)
        except Exception as e:
            print("⚠️ Instagram Reel error:", e)

    # 2. Instagram Story
    if POST_TO_STORIES:
        try:
            post_instagram_story(out_video)
        except Exception as e:
            print("⚠️ Instagram Story error:", e)

    # 3. YouTube Shorts
    if POST_TO_YOUTUBE:
        try:
            upload_youtube_short(
                video_path=out_video,
                title=f"[{state.get('genre', 'REELS')}] {state['series_title']} - Part {curr_part_num}/{total_parts} #Shorts",
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
