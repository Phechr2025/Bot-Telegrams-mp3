import logging
import asyncio
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import yt_dlp

# ---------------- ตั้งค่า ----------------
TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"  # 👈 แก้เป็น Token จริงของบอทคุณ

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ytmp3-bot")

ASK_LINK, ASK_FILENAME = range(2)


# ---------------- ฟังก์ชันช่วยเหลือ ----------------
def is_single_video(url: str) -> bool:
    """เช็คว่าลิงก์เป็นวิดีโอเดี่ยว ไม่ใช่ playlist"""
    return not ("playlist" in url or "list=" in url)


async def send_status(update: Update, text: str):
    if update.message:
        return await update.message.reply_text(text)
    return None


# ---------------- คำสั่งหลัก ----------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎧 YTMP3 Bot (โหมดดาวน์โหลดอย่างเดียว)\n\n"
        "คำสั่งที่ใช้ได้:\n"
        "/ytmp3 - ดาวน์โหลด YouTube เป็น MP3\n\n"
        "วิธีใช้:\n"
        "1️⃣ พิมพ์ /ytmp3\n"
        "2️⃣ ส่งลิงก์ YouTube (วิดีโอเดี่ยว)\n"
        "3️⃣ ใส่ชื่อไฟล์ (ไม่ต้องใส่ .mp3) หรือพิมพ์ No เพื่อใช้ชื่อเดิมจาก YouTube\n\n"
        "📌 ถ้าใช้คำสั่งในแชทส่วนตัว: บอทจะส่งไฟล์กลับในแชทนี้\n"
        "📌 ถ้าใช้คำสั่งในกลุ่ม: บอทจะส่งไฟล์ให้คุณทางแชทส่วนตัว (DM)"
    )
    await update.message.reply_text(text)


# ---------------- Workflow ดาวน์โหลด ----------------
async def ytmp3(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📎 กรุณาส่งลิงก์ YouTube (วิดีโอเดี่ยวเท่านั้น)")
    return ASK_LINK


async def ask_filename(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    url = (update.message.text or "").strip()

    if not url.startswith("http"):
        await update.message.reply_text("❌ ลิงก์ต้องขึ้นต้นด้วย http หรือ https")
        return ConversationHandler.END

    if not is_single_video(url):
        await update.message.reply_text("❌ ลิงก์นี้ไม่ใช่วิดีโอเดี่ยว กรุณาส่งลิงก์วิดีโอเดี่ยว")
        return ConversationHandler.END

    ctx.user_data["url"] = url
    await update.message.reply_text(
        "📝 ตั้งชื่อไฟล์ (ไม่ต้องใส่ .mp3)\n"
        "พิมพ์ No ถ้าจะใช้ชื่อจาก YouTube เดิม"
    )
    return ASK_FILENAME


async def do_download(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """ถามชื่อไฟล์แล้วเริ่มโหลด และส่งไฟล์ไปยัง DM ของผู้ใช้"""
    url = ctx.user_data.get("url")
    if not url:
        await update.message.reply_text("❌ ไม่มีลิงก์ในข้อมูล กรุณาพิมพ์ /ytmp3 ใหม่อีกครั้ง")
        return ConversationHandler.END

    filename_input = (update.message.text or "").strip() or "No"
    ctx.user_data["filename"] = filename_input

    user = update.effective_user
    chat = update.effective_chat
    chat_type = chat.type  # "private", "group", "supergroup", "channel"

    # ส่งไฟล์ไป DM ของผู้ใช้เสมอ
    target_chat_id = user.id

    # ข้อความสถานะในห้องที่เรียกคำสั่ง
    if chat_type == "private":
        status_msg = await update.message.reply_text("⏳ กำลังดาวน์โหลดและแปลงเป็น MP3 ...")
    else:
        status_msg = await update.message.reply_text(
            "⏳ กำลังดาวน์โหลดและจะส่งไฟล์ให้คุณทางแชทส่วนตัว (DM)..."
        )

    url = ctx.user_data["url"]
    filename_input = ctx.user_data["filename"]

    try:
        # ใช้ asyncio.to_thread เพื่อไม่บล็อค event loop ตอนใช้ yt-dlp
        def _download():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
                "noplaylist": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    },
                ],
                "quiet": True,
                "socket_timeout": 30,
                "retries": 5,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                out_file = ydl.prepare_filename(info)

                # ให้ชื่อไฟล์ปลายทางเป็น .mp3 เสมอ
                if out_file.endswith(".webm"):
                    out_file = out_file[:-5] + ".mp3"
                elif out_file.endswith(".m4a"):
                    out_file = out_file[:-4] + ".mp3"

            return info, out_file

        info, out_file = await asyncio.to_thread(_download)

        # ตั้งชื่อไฟล์ที่แนบใน Telegram
        display_name = info.get("title", "Audio")
        if filename_input.lower() != "no":
            display_name = filename_input

        # ส่งไฟล์ไปยัง DM ของผู้ใช้
        with open(out_file, "rb") as f:
            await ctx.bot.send_document(
                chat_id=target_chat_id,
                document=f,
                filename=f"{display_name}.mp3",
            )

        if status_msg:
            await status_msg.edit_text("✅ เสร็จสิ้น! ไฟล์ถูกส่งไปยังแชทส่วนตัวของคุณแล้ว")

    except Exception as e:
        logger.exception("Download error")
        if status_msg:
            msg = str(e)
            if "Timed out" in msg or "timeout" in msg.lower():
                await status_msg.edit_text(
                    "❌ ผิดพลาด: ใช้เวลานานเกินไป (Timed out)\n"
                    "อาจเกิดจากเน็ตช้า, วิดีโอยาวมาก หรือไฟล์ใหญ่เกินไป\n"
                    "ลองใหม่ด้วยวิดีโอที่สั้นลง หรือเช็คเน็ต VPS อีกครั้ง"
                )
            else:
                await status_msg.edit_text(f"❌ ผิดพลาดขณะดาวน์โหลดหรือแปลงไฟล์: {e}")

    return ConversationHandler.END


# ---------------- timeout 3 นาที ----------------
async def on_timeout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # ถูกเรียกเมื่อเกิน 3 นาทีโดยไม่มีข้อความใหม่ใน conversation
    if update.effective_message:
        await update.effective_message.reply_text(
            "⌛ หมดเวลา 3 นาทีแล้ว ยกเลิกคำสั่งอัตโนมัติ\n"
            "หากต้องการดาวน์โหลดใหม่ ให้พิมพ์ /ytmp3 อีกครั้ง"
        )
    return ConversationHandler.END


# ---------------- main ----------------
def main():
    # เพิ่ม timeout ให้ฝั่ง Telegram bot ด้วย
    app = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30.0)
        .read_timeout(60.0)
        .write_timeout(60.0)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("ytmp3", ytmp3)],
        states={
            ASK_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_filename)],
            ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, do_download)],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, on_timeout)
            ],
        },
        fallbacks=[],
        conversation_timeout=180,  # ⏱ หมดเวลา 3 นาที
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)

    app.run_polling()


if __name__ == "__main__":
    main()
