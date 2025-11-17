import os
import threading
from flask import Flask
from bot import main as run_bot

app = Flask(__name__)

@app.route("/")
def index():
    return "YTMP3 Telegram bot is running on Render."

def start_bot():
    # Run the Telegram bot (blocking) in a background thread
    run_bot()

if __name__ == "__main__":
    # Start Telegram bot in a separate daemon thread
    t = threading.Thread(target=start_bot, daemon=True)
    t.start()

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
