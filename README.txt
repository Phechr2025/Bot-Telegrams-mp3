YTMP3 Telegram Bot - Render Web Service Version (Fixed v2)

การเปลี่ยนแปลงหลักจากเวอร์ชันก่อน:
- ย้าย Telegram bot ไปรันใน main thread เพื่อแก้ปัญหา
  RuntimeError: set_wakeup_fd only works in main thread of the main interpreter
- Flask จะรันใน thread เบื้องหลังแทน

ไฟล์ในโปรเจกต์:
- bot.py          ← ใช้ BOT_TOKEN จาก Environment + มี event loop fix
- web_bot.py      ← รัน Flask ใน thread, บอทใน main thread
- requirements.txt← python-telegram-bot, yt-dlp, Flask

วิธี Deploy บน Render (Web Service ฟรี):

1. อัปโหลดไฟล์ทั้งหมดใน zip นี้ขึ้น GitHub repo (เช่น Bot-Telegrams-mp3)
2. บน Render สร้าง Web Service ใหม่ หรือ Redeploy ตัวเดิม โดยตั้งค่า:

   Build Command:
       pip install -r requirements.txt

   Start Command:
       python web_bot.py

3. ใน Environment Variables ใส่ค่า:
       BOT_TOKEN = <Token บอท Telegram ของคุณ>

4. Deploy เสร็จแล้ว:
   - เปิด URL ของ Render จะเห็นข้อความ "Telegram YTMP3 Bot is running..."
   - ใน Telegram ทดสอบพิมพ์ /start บอทควรตอบกลับทันที
