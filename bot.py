
import logging, asyncio, os, base64, threading, time
from typing import Union, Optional
from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler,
    ContextTypes, filters
)
import yt_dlp

# Provide ffmpeg via imageio-ffmpeg if available
try:
    import imageio_ffmpeg
    _ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    _ffmpeg_dir = os.path.dirname(_ffmpeg_bin)
except Exception:
    _ffmpeg_dir = None

# Flask lightweight health endpoint to keep a port open (runs in a separate thread)
from flask import Flask, jsonify
flask_app = Flask("health")
@flask_app.route("/")
def health():
    return jsonify({"status":"ok","service":"ytmp3-bot"}), 200

def start_flask_in_thread():
    port = int(os.getenv("PORT", os.getenv("RENDER_PORT", "8080")))
    def run():
        # Suppress Flask log noise a bit
        import logging as _logging
        _logging.getLogger('werkzeug').setLevel(_logging.ERROR)
        flask_app.run(host="0.0.0.0", port=port, threaded=True)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    # Give it a moment to bind
    time.sleep(0.5)

# ---------- Config ----------
TOKEN = os.getenv("TOKEN")  # set this on Render
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ytmp3-bot")

ASK_LINK, ASK_FILENAME, ASK_SENDTO, ASK_ADMIN_CMD = range(4)
CURRENT_TASK: Optional[asyncio.Task] = None
CURRENT_OWNER_ID: Optional[int] = None
CURRENT_ORIGIN_CHAT_ID: Optional[int] = None
HELP_COMMANDS: dict[str, str] = {}

# ---------- Helpers ----------
def get_user_id(u: Union[Update, CallbackQuery]) -> int:
    if isinstance(u, CallbackQuery):
        return u.from_user.id
    return u.effective_user.id

def get_chat_id(u: Union[Update, CallbackQuery]) -> Optional[int]:
    if isinstance(u, CallbackQuery):
        return u.message.chat.id if u.message else None
    return u.effective_chat.id

async def send_text(u: Union[Update, CallbackQuery], ctx: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        if isinstance(u, CallbackQuery):
            if u.message:
                return await u.edit_message_text(text)
            return await ctx.bot.send_message(chat_id=u.from_user.id, text=text)
        else:
            return await u.message.reply_text(text)
    except Exception:
        if isinstance(u, CallbackQuery):
            return await ctx.bot.send_message(chat_id=u.from_user.id, text=text)

def is_single_video(url: str) -> bool:
    return not ("playlist" in url or "list=" in url)

def _write_cookies_from_env() -> Optional[str]:
    """Decode base64 cookies from env YT_COOKIES_B64 into /tmp/yt_cookies.txt"""
    b64 = os.getenv("YT_COOKIES_B64")
    if not b64:
        return None
    path = "/tmp/yt_cookies.txt"
    try:
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return path
    except Exception as e:
        logger.warning("Failed to decode cookies: %s", e)
        return None

# ---------- Commands ----------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎧 YTMP3 Bot v6 (Render)\n\n"
        "คำสั่งที่ใช้ได้:\n"
        "/ytmp3 - ดาวน์โหลด YouTube เป็น MP3\n"
        "/cancel - ยกเลิกงานที่กำลังทำ\n"
        "/sethelp - ตั้งคำสั่งช่วยเหลือพิเศษ (Admin)\n"
        "พิมพ์คำสั่งพิเศษที่ Admin ตั้งเอง (ไม่ต้องใช้ / ขึ้นหน้า)\n"
    )
    await update.message.reply_text(text)

async def ytmp3(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📎 กรุณาส่งลิงก์ YouTube (วิดีโอเดี่ยวเท่านั้น)")
    return ASK_LINK

async def ask_filename(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ ลิงก์ต้องขึ้นต้นด้วย http หรือ https")
        return ConversationHandler.END
    if not is_single_video(url):
        await update.message.reply_text("❌ ลิงก์นี้ไม่ใช่วิดีโอเดี่ยว กรุณาส่งใหม่")
        return ConversationHandler.END
    ctx.user_data["url"] = url
    await update.message.reply_text("📝 ตั้งชื่อไฟล์ (ไม่ต้องใส่ .mp3)\nพิมพ์ No ถ้าจะใช้ชื่อจาก YouTube")
    return ASK_FILENAME

async def ask_sendto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    filename = (update.message.text or "").strip() or "No"
    ctx.user_data["filename"] = filename
    keyboard = [[
        InlineKeyboardButton("📥 ส่งส่วนตัว", callback_data="dm"),
        InlineKeyboardButton("👥 ส่งในกลุ่ม", callback_data="group"),
    ]]
    await update.message.reply_text("📤 จะให้ส่งไฟล์ที่ไหนครับ?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ASK_SENDTO

async def ask_sendto_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    choice = query.data
    await query.answer("⏳ กำลังเตรียมดาวน์โหลด...", show_alert=False)
    if query.message:
        await query.edit_message_text(f"⏳ คุณเลือก: {'ส่งส่วนตัว' if choice=='dm' else 'ส่งในกลุ่ม'}\nกำลังดำเนินการ...")
    return await start_download(update, ctx, sendto=choice)

async def start_download(u: Union[Update, CallbackQuery], ctx: ContextTypes.DEFAULT_TYPE, sendto: str):
    global CURRENT_TASK, CURRENT_OWNER_ID, CURRENT_ORIGIN_CHAT_ID
    if CURRENT_TASK:
        await send_text(u, ctx, "⛔ มีงานกำลังทำอยู่ กรุณารอก่อน")
        return ConversationHandler.END
    uid = get_user_id(u)
    cid = get_chat_id(u)
    CURRENT_OWNER_ID, CURRENT_ORIGIN_CHAT_ID = uid, cid
    url = ctx.user_data["url"]
    filename = (ctx.user_data.get("filename") or "No").strip()
    status_msg = await send_text(u, ctx, "⏳ กำลังดาวน์โหลด...")

    async def task():
        global CURRENT_TASK, CURRENT_OWNER_ID, CURRENT_ORIGIN_CHAT_ID
        try:
            cookiefile = _write_cookies_from_env()

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "postprocessors": [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
                ],
                "retries": 10,
                "fragment_retries": 10,
                "concurrent_fragment_downloads": 1,
                "http_headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                "extractor_args": {
                    "youtube": {"player_client": ["android", "web"]}
                },
                "quiet": True,
            }
            if cookiefile:
                ydl_opts["cookiefile"] = cookiefile
            if _ffmpeg_dir:
                ydl_opts["ffmpeg_location"] = _ffmpeg_dir

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                out_file = ydl.prepare_filename(info)
                if out_file.endswith(".webm"):
                    out_file = out_file[:-5] + ".mp3"
                elif out_file.endswith(".m4a"):
                    out_file = out_file[:-4] + ".mp3"

            display_name = info.get("title", "Audio") if filename.lower() == "no" else filename
            target_chat = CURRENT_OWNER_ID if sendto == "dm" else (u.effective_chat.id if isinstance(u, Update) else u.message.chat.id)
            with open(out_file, "rb") as f:
                await ctx.bot.send_document(chat_id=target_chat, document=f, filename=f"{display_name}.mp3")
            if status_msg:
                await status_msg.edit_text("✅ เสร็จสิ้น!")
        except Exception as e:
            logger.exception("Download error")
            if status_msg:
                await status_msg.edit_text(f"❌ ผิดพลาด: {e}")
        finally:
            CURRENT_TASK = None
            CURRENT_OWNER_ID = None
            CURRENT_ORIGIN_CHAT_ID = None

    CURRENT_TASK = asyncio.create_task(task())
    return ConversationHandler.END

async def sethelp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        chat_member = await update.effective_chat.get_member(update.effective_user.id)
        if not (getattr(chat_member, "can_manage_chat", False) or chat_member.status in ("administrator", "creator")):
            await update.message.reply_text("⛔ เฉพาะแอดมินที่ตั้งค่าได้")
            return
    except Exception:
        pass
    await update.message.reply_text("🛠 พิมพ์ชื่อคำสั่งช่วยเหลือที่ต้องการตั้ง")
    return ASK_ADMIN_CMD

async def ask_admin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.strip()
    ctx.user_data["pending_cmd"] = cmd
    await update.message.reply_text(f"🔧 กำดข้อความสำหรับคำสั่ง '{cmd}'")
    return ASK_ADMIN_CMD + 1

async def save_admin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cmd = ctx.user_data.get("pending_cmd")
    if not cmd:
        await update.message.reply_text("❌ เกิดข้อผิดพลาด")
        return ConversationHandler.END
    HELP_COMMANDS[cmd] = update.message.text.strip()
    await update.message.reply_text(f"✅ ตั้งคำสั่ง '{cmd}' เรียบร้อยแล้ว")
    return ConversationHandler.END

async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global CURRENT_TASK, CURRENT_OWNER_ID
    if CURRENT_TASK and CURRENT_OWNER_ID == update.effective_user.id:
        CURRENT_TASK.cancel()
        CURRENT_TASK = None
        CURRENT_OWNER_ID = None
        await update.message.reply_text("🛑 ยกเลิกงานเรียบร้อย")
    else:
        await update.message.reply_text("ℹ️ ไม่มีงานที่กำลังทำ")

async def custom_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    if txt in HELP_COMMANDS:
        await update.message.reply_text(HELP_COMMANDS[txt])

def main():
    # start fake port listener so Render sees an open port
    start_flask_in_thread()

    if not TOKEN:
        raise RuntimeError("Missing TOKEN env var")
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("ytmp3", ytmp3), CommandHandler("sethelp", sethelp)],
        states={
            ASK_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_filename)],
            ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_sendto)],
            ASK_SENDTO: [CallbackQueryHandler(ask_sendto_callback)],
            ASK_ADMIN_CMD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_admin_cmd)],
            ASK_ADMIN_CMD+1: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_admin_cmd)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True,
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, custom_command))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
