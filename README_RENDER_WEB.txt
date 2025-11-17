YTMP3 Bot v6 - Render.com (Web Service mode)

ไฟล์ในโปรเจกต์นี้:
- bot.py           : โค้ด Telegram Bot (ใช้ตัวแปรสภาพแวดล้อม BOT_TOKEN)
- web_bot.py       : ตัวห่อสำหรับรันบอท + เว็บเล็ก ๆ ไว้ให้ Render เช็ค
- requirements.txt : รายการไลบรารี Python (เพิ่ม Flask ให้แล้ว)

วิธีใช้กับ Render แบบ Web Service (ฟรี):

1) อัปโหลดไฟล์ทั้งหมดขึ้น GitHub
2) ไปที่ Render.com → New → Web Service
3) เลือก repo นี้

ในหน้าตั้งค่า Web Service ให้ตั้งค่าแบบนี้:

- Environment: Python 3
- Build Command:

    apt-get update && apt-get install -y ffmpeg && pip install -r requirements.txt

- Start Command:

    python web_bot.py

4) เลื่อนลงไปส่วน Environment Variables แล้วเพิ่มตัวแปร:

   NAME: BOT_TOKEN
   VALUE: ใส่ Telegram Bot Token ที่ได้จาก BotFather

5) กด Deploy Web Service

เมื่อ Deploy สำเร็จ:
- Render จะรัน web_bot.py
- web_bot.py จะเปิดเว็บเล็ก ๆ บนพอร์ตที่ Render กำหนด และรัน Telegram bot ในเธรดแยก
- ทดสอบบอทได้โดยส่ง /start ใน Telegram

หมายเหตุ:
- โฟลเดอร์ downloads ที่บอทสร้างจะเป็น storage ชั่วคราวบน Render (ล้างออกเมื่อรีสตาร์ท)
