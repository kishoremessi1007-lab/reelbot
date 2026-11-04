"""
Helper script to generate YOUTUBE_REFRESH_TOKEN.
Run this ONCE locally on your PC:
1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Create a project, enable "YouTube Data API v3"
3. Go to "Credentials" -> "Create Credentials" -> "OAuth Client ID" (Application Type: Web Application or Desktop app)
4. Add redirect URI: http://localhost:8080/
5. Enter Client ID and Client Secret below and run this script.
6. Copy the printed Refresh Token to GitHub Secrets!
"""
import os
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

auth_code = None

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<h1>Success! You can close this browser tab now and return to terminal.</h1>")
        else:
            self.send_response(400)
            self.end_headers()

def main():
    print("=== YouTube OAuth Refresh Token Generator ===")
    client_id = input("Enter your Google Client ID: ").strip()
    client_secret = input("Enter your Google Client Secret: ").strip()

    redirect_uri = "http://localhost:8080/"
    scope = "https://www.googleapis.com/auth/youtube.upload"

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
            "access_type": "offline",
            "prompt": "consent"
        })
    )

    print("\nOpening your browser to authorize access to YouTube...")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8080), OAuthHandler)
    print("Waiting for authentication callback on http://localhost:8080/ ...")
    while not auth_code:
        server.handle_request()

    # Exchange authorization code for refresh token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri
    }
    r = requests.post(token_url, data=data)
    if not r.ok:
        print("Error exchanging code:", r.text)
        return

    tokens = r.json()
    refresh_token = tokens.get("refresh_token")
    print("\n" + "="*50)
    print("🎉 SUCCESS! Add these secrets to your GitHub Repo:")
    print(f"YOUTUBE_CLIENT_ID: {client_id}")
    print(f"YOUTUBE_CLIENT_SECRET: {client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN: {refresh_token}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()

