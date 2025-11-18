import logging, os
from typing import Union
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
import yt_dlp

TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ytmp3-bot")

ASK_LINK, ASK_FILENAME = range(2)

def is_single_video(url: str) -> bool:
    return not ("playlist" in url or "list=" in url)

async def send_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE, text: str):
    if update.message:
        return await update.message.reply_text(text)
    return None

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎧 YTMP3 Bot (โหมดดาวน์โหลดอย่างเดียว)\n\n"
        "คำสั่งที่ใช้ได้:\n"
        "/ytmp3 - ดาวน์โหลด YouTube เป็น MP3\n\n"
        "วิธีใช้:\n"
        "1️⃣ พิมพ์ /ytmp3\n"
        "2️⃣ ส่งลิงก์ YouTube (วิดีโอเดี่ยว)\n"
        "3️⃣ ใส่ชื่อไฟล์ หรือพิมพ์ No เพื่อใช้ชื่อเดิมจาก YouTube\n\n"
        "📌 ถ้าใช้คำสั่งในแชทส่วนตัว: ส่งไฟล์กลับในแชทนี้\n"
        "📌 ถ้าใช้คำสั่งในกลุ่ม: บอทจะส่งไฟล์ให้ทางแชทส่วนตัว (DM)"
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
        await update.message.reply_text("❌ กรุณาส่งลิงก์วิดีโอเดี่ยว")
        return ConversationHandler.END
    ctx.user_data["url"] = url
    await update.message.reply_text(
        "📝 ตั้งชื่อไฟล์ (ไม่ต้องใส่ .mp3)\nพิมพ์ No ถ้าจะใช้ชื่อเดิมจาก YouTube"
    )
    return ASK_FILENAME

async def do_download(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = ctx.user_data.get("url")
    if not url:
        await update.message.reply_text("❌ ไม่มีลิงก์ กรุณาพิมพ์ /ytmp3 ใหม่")
        return ConversationHandler.END

    filename_input = (update.message.text or "").strip() or "No"
    ctx.user_data["filename"] = filename_input

    user = update.effective_user
    chat = update.effective_chat
    chat_type = chat.type
    target_chat_id = user.id

    if chat_type == "private":
        status_msg = await update.message.reply_text("⏳ กำลังดาวน์โหลด ...")
    else:
        status_msg = await update.message.reply_text(
            "⏳ จะส่งไฟล์ให้คุณทางแชทส่วนตัว (DM)..."
        )

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
            ],
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            out_file = ydl.prepare_filename(info)
            if out_file.endswith(".webm"):
                out_file = out_file[:-5] + ".mp3"
            elif out_file.endswith(".m4a"):
                out_file = out_file[:-4] + ".mp3"

        display_name = info.get("title", "Audio")
        if filename_input.lower() != "no":
            display_name = filename_input

        with open(out_file, "rb") as f:
            await ctx.bot.send_document(
                chat_id=target_chat_id,
                document=f,
                filename=f"{display_name}.mp3",
            )

        await status_msg.edit_text("✅ เสร็จสิ้น! ไฟล์ถูกส่งไปยังแชทส่วนตัวแล้ว")

    except Exception as e:
        await status_msg.edit_text(f"❌ ผิดพลาด: {e}")

    return ConversationHandler.END

def main():
    app = Application.builder().token(TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("ytmp3", ytmp3)],
        states={
            ASK_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_filename)],
            ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, do_download)],
        },
        fallbacks=[],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
