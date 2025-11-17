import os
import threading
from flask import Flask
from bot import main as run_bot

app = Flask(__name__)

@app.route("/")
def index():
    return "Telegram YTMP3 Bot is running on Render (Web Service Mode)."

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start Flask in background thread
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

    # Run Telegram bot in main thread (so asyncio signals work correctly)
    run_bot()
