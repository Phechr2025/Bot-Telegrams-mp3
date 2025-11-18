YTMP3 Bot (Only download mode)

คำสั่งที่ใช้ได้:
/start  - แสดงวิธีใช้งาน
/ytmp3  - ดาวน์โหลดวิดีโอ YouTube เป็นไฟล์ MP3

ฟังก์ชัน:
- ขอ URL YouTube (เฉพาะวิดีโอเดี่ยว)
- ถามชื่อไฟล์ (พิมพ์ No เพื่อใช้ชื่อเดิมจาก YouTube)
- ดาวน์โหลดและแปลงเสียงเป็น MP3 ด้วย yt-dlp + ffmpeg
- ถ้าใช้ในแชทส่วนตัว: ส่งไฟล์กลับในแชทนั้นเลย
- ถ้าใช้ในกลุ่ม: บอทจะส่งไฟล์ไปทางแชทส่วนตัว (DM) ของผู้ใช้คนนั้น
- ถ้าไม่มีการตอบภายใน 3 นาที (180 วินาที) จะยกเลิกคำสั่งอัตโนมัติ

วิธีใช้งานบน VPS (ตัวอย่าง):

1) แตกไฟล์ ZIP แล้วเข้าโฟลเดอร์:
   cd YTMP3_ONLY_BOT_FULL

2) สร้างและเปิดใช้งาน virtualenv:
   python3 -m venv venv
   source venv/bin/activate

3) ติดตั้ง dependencies:
   pip install -r requirements.txt

4) ติดตั้ง ffmpeg (ถ้ายังไม่มี):
   sudo apt update
   sudo apt install -y ffmpeg

5) แก้โค้ดใส่ TOKEN จริง:
   nano bot.py
   # แก้บรรทัด TOKEN = "PUT_YOUR_BOT_TOKEN_HERE"

6) รันบอท:
   python3 bot.py
