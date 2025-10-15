
# YTMP3 Telegram Bot — Render Ready

## Deploy via GitHub → Render
1) Push this folder to a new GitHub repo.
2) On https://dashboard.render.com/ → New → Background Worker → Connect your repo.
3) Environment:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
   - Add Env Var: `TOKEN=<your_telegram_bot_token>`
4) Click Deploy.

Notes:
- Uses imageio-ffmpeg to bundle an ffmpeg binary at runtime (no apt-get needed).
- Runs as a **Background Worker** (no HTTP port needed for polling).
