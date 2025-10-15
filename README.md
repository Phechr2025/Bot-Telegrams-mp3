
# YTMP3 Telegram Bot — Render Ready (Full + Fake Port)
This package starts a small Flask health endpoint (binds to $PORT) so Render detects an open port.
It still runs the Telegram bot with polling.

## Deploy
1) Push to GitHub.
2) Render → New → Web Service → select repo.
3) Build: pip install -r requirements.txt
4) Start: python bot.py
5) Env:
   - TOKEN (required)
   - YT_COOKIES_B64 (optional)
   - DOWNLOAD_DIR=downloads (optional)

## Notes
- The Flask server runs in a background thread and listens on $PORT (or 8080).
- This makes Render treat the service as a Web Service (open port detected) so logs won't show "No open ports detected".
- The Telegram bot continues to use polling and will function normally.
