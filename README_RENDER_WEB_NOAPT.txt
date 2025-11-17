YTMP3 Bot v6 - Render Web Service (ไม่ใช้ apt-get)

ไฟล์:
- bot.py           : โค้ดบอท (แก้ให้ใช้ BOT_TOKEN และไม่ใช้ ffmpeg แล้ว)
- web_bot.py       : ตัวห่อรันบอท + เปิดเว็บเล็ก ๆ
- requirements.txt : ไลบรารี Python (เพิ่ม Flask แล้ว)

ตั้งค่าบน Render (Web Service):
- Build Command:
    pip install -r requirements.txt
- Start Command:
    python web_bot.py
- Environment Variable:
    BOT_TOKEN = ใส่ Telegram Bot Token

ไม่ต้องใช้ ffmpeg / apt-get อีกต่อไป
