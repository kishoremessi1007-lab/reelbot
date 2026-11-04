"""
Zero-dependency YouTube Shorts Uploader using pure `requests`.
Uploads 9:16 vertical video directly to YouTube Shorts with #Shorts.
Requires: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN.
"""
import os
import sys
import json
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

def get_youtube_access_token(client_id, client_secret, refresh_token):
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id.strip(),
        "client_secret": client_secret.strip(),
        "refresh_token": refresh_token.strip(),
        "grant_type": "refresh_token"
    }
    r = requests.post(url, data=data, timeout=30)
    if not r.ok:
        print(f"❌ YouTube token refresh failed [{r.status_code}]: {r.text}")
        r.raise_for_status()
    return r.json()["access_token"]

def upload_youtube_short(video_path, title, description, tags=None):
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")

    if not (client_id and client_secret and refresh_token):
        print("⚠️ YouTube credentials not configured (YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN). Skipping YouTube upload.")
        return None

    print(f"🚀 Preparing YouTube Shorts upload: {title}")
    access_token = get_youtube_access_token(client_id, client_secret, refresh_token)

    # Metadata
    # Shorts must have #Shorts in title or description
    if "#Shorts" not in title and "#shorts" not in title:
        title = f"{title} #Shorts"

    metadata = {
        "snippet": {
            "title": title[:100],
            "description": f"{description}\n\n#Shorts #TamilAIComedy #Comedy #Reels",
            "tags": tags or ["tamil comedy", "ai comedy", "shorts", "thakkali", "urulai"],
            "categoryId": "23" # 23 = Comedy
        },
        "status": {
            "privacyStatus": os.environ.get("YOUTUBE_PRIVACY", "public"),
            "selfDeclaredMadeForKids": False
        }
    }

    # Step 1: Initialize Resumable Upload Session
    init_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Type": "video/mp4",
        "X-Upload-Content-Length": str(os.path.getsize(video_path))
    }

    init_r = requests.post(init_url, headers=headers, json=metadata, timeout=30)
    if not init_r.ok:
        print(f"❌ Failed to initiate YouTube upload session [{init_r.status_code}]: {init_r.text}")
        init_r.raise_for_status()

    upload_url = init_r.headers.get("Location")
    if not upload_url:
        raise RuntimeError("YouTube API did not return an upload Location URL")

    # Step 2: Upload Video File
    file_size = os.path.getsize(video_path)
    print(f"Uploading {file_size:,} bytes to YouTube...")
    with open(video_path, "rb") as f:
        video_data = f.read()

    up_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "video/mp4",
        "Content-Length": str(file_size)
    }

    up_r = requests.put(upload_url, headers=up_headers, data=video_data, timeout=600)
    if not up_r.ok:
        print(f"❌ YouTube video binary upload failed [{up_r.status_code}]: {up_r.text}")
        up_r.raise_for_status()

    res = up_r.json()
    video_id = res.get("id")
    print(f"🎉 Successfully posted to YouTube Shorts! Video ID: {video_id}")
    print(f"🔗 URL: https://www.youtube.com/shorts/{video_id}")
    return video_id
