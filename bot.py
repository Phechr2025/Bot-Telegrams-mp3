import logging
import asyncio
import os
from collections import deque

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
TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"  # แก้เป็น Token จริงของบอทคุณ
ADMIN_USER_ID = 1234567890         # แก้เป็น User ID ของแอดมินที่มีสิทธิ์ /stopall

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ytmp3-bot")

ASK_LINK, ASK_FILENAME = range(2)

# คิวดาวน์โหลด: ทำทีละ 1 งาน
DOWNLOAD_QUEUE = deque()
CURRENT_TASK = None  # asyncio.Task ปัจจุบัน หรือ None


# ---------------- ฟังก์ชันช่วยเหลือ ----------------
def is_single_video(url: str) -> bool:
    """เช็คว่าลิงก์เป็นวิดีโอเดี่ยว ไม่ใช่ playlist"""
    return not ("playlist" in url or "list=" in url)


# ---------------- คำสั่งหลัก ----------------
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎧 YTMP3 Bot (โหลดทีละ 1 งาน + คิวรอ)\n\n"
        "คำสั่งที่ใช้ได้:\n"
        "/ytmp3  - ดาวน์โหลด YouTube เป็น MP3\n"
        "/stopall - (เฉพาะแอดมินที่กำหนด) ยกเลิกงานดาวน์โหลดทั้งหมด + ล้างคิว\n\n"
        "วิธีใช้ /ytmp3:\n"
        "1️⃣ พิมพ์ /ytmp3\n"
        "2️⃣ ส่งลิงก์ YouTube (วิดีโอเดี่ยว)\n"
        "3️⃣ ใส่ชื่อไฟล์ (ไม่ต้องใส่ .mp3) หรือพิมพ์ No เพื่อใช้ชื่อเดิมจาก YouTube\n\n"
        "📌 ถ้าใช้ในแชทส่วนตัว: บอทจะส่งไฟล์ในแชทนี้\n"
        "📌 ถ้าใช้ในกลุ่ม: บอทจะส่งไฟล์ไปยังแชทส่วนตัว (DM) ของคุณ\n"
        "⌛ หากไม่มีการตอบต่อ 3 นาที คำสั่งจะถูกยกเลิกอัตโนมัติ"
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


async def enqueue_download(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """เก็บงานไว้ในคิว แล้วให้ระบบดาวน์โหลดทีละ 1 งาน"""
    url = ctx.user_data.get("url")
    if not url:
        await update.message.reply_text("❌ ไม่มีลิงก์ในข้อมูล กรุณาพิมพ์ /ytmp3 ใหม่อีกครั้ง")
        return ConversationHandler.END

    filename_input = (update.message.text or "").strip() or "No"

    user = update.effective_user
    chat = update.effective_chat
    chat_type = chat.type  # "private", "group", "supergroup", "channel"

    job = {
        "user_id": user.id,
        "origin_chat_id": chat.id,
        "chat_type": chat_type,
        "url": url,
        "filename_input": filename_input,
    }

    DOWNLOAD_QUEUE.append(job)
    position = len(DOWNLOAD_QUEUE)

    # ถ้ายังไม่มีงานกำลังทำ → เริ่มเลย
    if position == 1 and CURRENT_TASK is None:
        await update.message.reply_text("✅ งานของคุณเริ่มดาวน์โหลดทันที กำลังดำเนินการ...")
        await start_next_download(ctx.application)
    else:
        await update.message.reply_text(
            f"⏳ ตอนนี้มีงานอื่นกำลังดาวน์โหลดอยู่\n"
            f"งานของคุณถูกเพิ่มเข้า *คิวลำดับที่ {position}* แล้ว"
        )

    return ConversationHandler.END


async def start_next_download(app: Application):
    """ดึงงานจากคิวมาทำ ถ้าไม่มีงานกำลังทำอยู่"""
    global CURRENT_TASK

    if CURRENT_TASK is not None:
        return
    if not DOWNLOAD_QUEUE:
        return

    job = DOWNLOAD_QUEUE.popleft()

    async def worker():
        global CURRENT_TASK
        try:
            await process_job(app, job)
        finally:
            CURRENT_TASK = None
            await start_next_download(app)

    CURRENT_TASK = app.create_task(worker())


async def process_job(app: Application, job: dict):
    """ประมวลผลงาน 1 รายการ: ดาวน์โหลด + ส่งไฟล์"""
    user_id = job["user_id"]
    origin_chat_id = job["origin_chat_id"]
    chat_type = job["chat_type"]
    url = job["url"]
    filename_input = job["filename_input"]

    status_msg = None
    try:
        if chat_type == "private":
            status_msg = await app.bot.send_message(
                chat_id=origin_chat_id,
                text="⏳ กำลังดาวน์โหลดและแปลงเป็น MP3 ..."
            )
        else:
            status_msg = await app.bot.send_message(
                chat_id=origin_chat_id,
                text="⏳ กำลังดาวน์โหลดไฟล์ของคุณ และจะส่งไปยังแชทส่วนตัว (DM)..."
            )
    except Exception as e:
        logger.warning(f"ไม่สามารถส่งข้อความสถานะไปยัง origin_chat_id={origin_chat_id}: {e}")

    try:
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

                if out_file.endswith(".webm"):
                    out_file = out_file[:-5] + ".mp3"
                elif out_file.endswith(".m4a"):
                    out_file = out_file[:-4] + ".mp3"

            return info, out_file

        info, out_file = await asyncio.to_thread(_download)

        display_name = info.get("title", "Audio")
        if filename_input.lower() != "no":
            display_name = filename_input

        with open(out_file, "rb") as f:
            await app.bot.send_document(
                chat_id=user_id,
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


# ---------------- timeout 3 นาที ----------------
async def on_timeout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_message:
        await update.effective_message.reply_text(
            "⌛ หมดเวลา 3 นาที ยกเลิกคำสั่งอัตโนมัติ\n"
            "หากต้องการดาวน์โหลดใหม่ ให้พิมพ์ /ytmp3 อีกครั้ง"
        )
    return ConversationHandler.END


# ---------------- แอดมิน: ยกเลิกงานทั้งหมด (เฉพาะ USER ID ที่กำหนด) ----------------
async def stopall(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global CURRENT_TASK, DOWNLOAD_QUEUE

    user = update.effective_user
    chat = update.effective_chat

    # ถ้าอยู่ใน group/supergroup ให้เช็กสถานะแอดมินก่อน
    if chat.type in ("group", "supergroup"):
        try:
            member = await chat.get_member(user.id)
            if member.status not in ("administrator", "creator"):
                await update.message.reply_text("⛔ คำสั่งนี้ใช้ได้เฉพาะแอดมินเท่านั้น")
                return
        except Exception:
            await update.message.reply_text("⛔ ไม่สามารถตรวจสอบสิทธิ์แอดมินได้")
            return

    # เช็กว่า user.id ตรงกับ ADMIN_USER_ID หรือไม่
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ คำสั่งนี้ใช้ได้เฉพาะแอดมินที่ได้รับอนุญาตเท่านั้น")
        return

    # ยกเลิกงานปัจจุบัน
    if CURRENT_TASK is not None:
        CURRENT_TASK.cancel()
        CURRENT_TASK = None

    # ล้างคิว
    q_len = len(DOWNLOAD_QUEUE)
    DOWNLOAD_QUEUE.clear()

    await update.message.reply_text(
        f"🛑 ยกเลิกงานดาวน์โหลดที่กำลังทำอยู่ และล้างคิว {q_len} งานเรียบร้อยแล้ว\n"
        f"(ดำเนินการโดย User ID: {user.id})"
    )


# ---------------- main ----------------
def main():
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
            ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enqueue_download)],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, on_timeout)
            ],
        },
        fallbacks=[],
        conversation_timeout=180,  # 3 นาที
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stopall", stopall))   # แอดมินที่กำหนดเท่านั้น
    app.add_handler(conv)

    app.run_polling()


if __name__ == "__main__":
    main()
