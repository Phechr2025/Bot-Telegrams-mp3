YTMP3 Bot v6 - Render.com Ready

ไฟล์ในโปรเจกต์นี้:
- bot.py              : โค้ด Telegram Bot (แก้แล้วให้ใช้ตัวแปรสภาพแวดล้อม BOT_TOKEN)
- requirements.txt    : รายการไลบรารี Python ที่ต้องติดตั้ง
- Procfile            : บอก Render ให้รันเป็น Background Worker ด้วยคำสั่ง python bot.py
- render.yaml         : สคริปต์ตั้งค่า Build บน Render (ติดตั้ง ffmpeg + pip install)

สิ่งที่ต้องแก้/ตั้งค่าเองก่อน Deploy:
1) ไปที่ Render.com → สร้าง Background Worker ใหม่
2) เชื่อมต่อ GitHub Repo ที่มีไฟล์ชุดนี้
3) ตั้งค่า Environment Variable:
   - KEY: BOT_TOKEN
   - VALUE: ใส่ Telegram Bot Token ของคุณ (จาก BotFather)
4) Render จะรันคำสั่ง:
   - apt-get update && apt-get install -y ffmpeg
   - pip install -r requirements.txt
   แล้วสตาร์ทบอทด้วย: python bot.py

หลัง Deploy เสร็จ:
- บอทจะออนไลน์อัตโนมัติ
- ทดสอบด้วยการพิมพ์ /start ใน Telegram

หมายเหตุ:
- โฟลเดอร์ downloads ที่สร้างโดยบอทจะเป็น storage ชั่วคราวบน Render (ลบเมื่อรีสตาร์ท)
