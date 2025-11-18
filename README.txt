YTMP3 Queue Bot (Admin Stop)

ฟีเจอร์:
- คำสั่ง /ytmp3 สำหรับดาวน์โหลดเสียงจาก YouTube เป็น .mp3
- จำกัดให้ดาวน์โหลดทีละ 1 งานเท่านั้น งานที่เหลือจะเข้าคิวรอ
- ถ้าใช้คำสั่งในแชทส่วนตัว (DM) บอทจะส่งไฟล์กลับใน DM นั้น
- ถ้าใช้คำสั่งในกลุ่ม บอทจะส่งไฟล์ไปยัง DM ของผู้ใช้คนนั้น
- มีระบบ timeout 3 นาที หากผู้ใช้ไม่ตอบต่อจะยกเลิกคำสั่งอัตโนมัติ
- คำสั่ง /stopall ใช้ยกเลิกงานดาวน์โหลดทั้งหมด + ล้างคิว
  * ใช้ได้เฉพาะ User ID ที่กำหนดในตัวแปร ADMIN_USER_ID เท่านั้น
  * ถ้าใช้ในกลุ่ม ต้องเป็นแอดมินของกลุ่มด้วย

ไฟล์ที่มี:
- bot.py
- requirements.txt
- README.txt

วิธีใช้งานบน VPS (ตัวอย่าง Ubuntu):

1) แตกไฟล์ ZIP แล้วเข้าโฟลเดอร์:
   cd ~/ytmp3_admin_stop_bot

2) สร้าง virtualenv และเปิดใช้งาน:
   python3 -m venv venv
   source venv/bin/activate

3) ติดตั้ง dependencies:
   pip install -r requirements.txt

4) ติดตั้ง ffmpeg (ถ้ายังไม่ได้ติดตั้ง):
   sudo apt update
   sudo apt install -y ffmpeg

5) แก้ TOKEN และ ADMIN_USER_ID ใน bot.py:
   nano bot.py
   # TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"
   # ADMIN_USER_ID = 1234567890

6) รันบอท:
   python3 bot.py

ใช้งาน:
- แชทกับบอท: /start, /ytmp3
- กลุ่ม: /ytmp3 เพื่อให้บอทโหลดแล้วส่งไฟล์ไป DM
- แอดมินที่กำหนด: /stopall เพื่อยกเลิกงานทั้งหมด
