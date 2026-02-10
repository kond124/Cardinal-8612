"""
🧧 TrueMoney Auto-Claim Bot - Ultimate Edition
รับซองอั่งเปาอัตโนมัติ รองรับทุกรูปแบบ
ไฟล์เดียวจบ ใช้งานง่าย เร็วที่สุด
"""

import asyncio
import re
import os
import sys
import time
from datetime import datetime
from typing import Optional, List, Set

print("=" * 70)
print("🧧 TrueMoney Auto-Claim Bot - Ultimate Edition")
print("=" * 70)

# ================== CONFIGURATION ==================
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
PHONE = os.getenv("PHONE", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")
WEBHOOK = os.getenv("WEBHOOK", "")

MAX_CONCURRENT = 10
CACHE_TIME = 20

# ================== AUTO INSTALL DEPENDENCIES ==================
print("\n🔧 กำลังตรวจสอบและติดตั้ง dependencies...")

import subprocess
def install(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        pass

packages = ["telethon", "aiohttp", "Pillow", "opencv-python-headless"]
for pkg in packages:
    module = "cv2" if pkg == "opencv-python-headless" else pkg.split("-")[0].lower()
    if module == "pillow":
        module = "PIL"
    try:
        __import__(module)
    except:
        print(f"  📦 Installing {pkg}...")
        install(pkg)

import aiohttp
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from PIL import Image
import cv2
import numpy as np

print("✅ Dependencies พร้อม!\n")

# ================== GLOBAL VARIABLES ==================
seen_vouchers: Set[str] = set()
session: Optional[aiohttp.ClientSession] = None
stats = {"success": 0, "failed": 0, "total": 0}

# ================== QR CODE SCANNER ==================
def scan_qr(image_bytes: bytes) -> Optional[str]:
    """สแกน QR Code ด้วย OpenCV - เร็วและแม่นยำ"""
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        
        detector = cv2.QRCodeDetector()
        
        # ลอง 4 วิธี
        attempts = [
            img,  # Original
            cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),  # Grayscale
            cv2.convertScaleAbs(img, alpha=1.5, beta=30),  # Bright
            cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 127, 255, cv2.THRESH_BINARY)[1]  # Binary
        ]
        
        for attempt in attempts:
            data, _, _ = detector.detectAndDecode(attempt)
            if data:
                return data
        
        return None
    except:
        return None

# ================== WEBHOOK ==================
async def send_webhook(title: str, desc: str, color: int, fields: list = None):
    """ส่ง Discord Webhook"""
    if not WEBHOOK:
        return
    
    embed = {
        "title": title,
        "description": desc,
        "color": color,
        "timestamp": datetime.utcnow().isoformat(),
        "footer": {"text": f"✅ {stats['success']} | ❌ {stats['failed']} | 📊 {stats['total']}"}
    }
    
    if fields:
        embed["fields"] = fields
    
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(WEBHOOK, json={"embeds": [embed]}, 
                        timeout=aiohttp.ClientTimeout(total=2))
    except:
        pass

# ================== TRUEMONEY API ==================
async def claim(voucher: str) -> dict:
    """รับซองอั่งเปา"""
    url = f"https://gift.truemoney.com/campaign/vouchers/{voucher}/redeem"
    
    # แปลงเบอร์ให้ถูกต้อง
    phone = PHONE.replace("-", "").replace(" ", "")
    if phone.startswith("+66"):
        phone = "0" + phone[3:]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    try:
        async with session.post(url, headers=headers, data={"mobile": phone}, 
                               timeout=aiohttp.ClientTimeout(total=5)) as resp:
            return await resp.json()
    except:
        return {"status": {"code": "ERROR"}}

async def process(voucher: str, chat: str):
    """ประมวลผลการรับซอง"""
    start = time.time()
    result = await claim(voucher)
    ms = int((time.time() - start) * 1000)
    
    stats["total"] += 1
    status = result.get("status", {}).get("code", "UNKNOWN")
    
    if status == "SUCCESS":
        stats["success"] += 1
        amount = result.get("data", {}).get("voucher", {}).get("amount_baht", 0)
        
        print(f"✅ [{ms}ms] 💰 {amount:.2f} บาท | {voucher[:16]}... | {chat}")
        
        await send_webhook(
            "🎉 รับเงินสำเร็จ!",
            f"💰 **ได้รับ {amount:.2f} บาท**",
            0x00ff00,
            [
                {"name": "💵 จำนวนเงิน", "value": f"{amount:.2f} THB", "inline": True},
                {"name": "⚡ ความเร็ว", "value": f"{ms} ms", "inline": True},
                {"name": "📍 แหล่งที่มา", "value": chat, "inline": True},
                {"name": "🎟️ Voucher", "value": f"`{voucher}`", "inline": False},
                {"name": "🕐 เวลา", "value": datetime.now().strftime("%H:%M:%S"), "inline": True}
            ]
        )
    
    elif status in ["VOUCHER_OUT_OF_STOCK", "VOUCHER_NOT_FOUND", "VOUCHER_EXPIRED"]:
        stats["failed"] += 1
        reasons = {
            "VOUCHER_OUT_OF_STOCK": "🔴 ซองหมด/คนรับหมดแล้ว",
            "VOUCHER_NOT_FOUND": "❌ ไม่มีซองในระบบ",
            "VOUCHER_EXPIRED": "⏰ ซองหมดอายุแล้ว"
        }
        reason = reasons.get(status, status)
        
        print(f"❌ [{ms}ms] {reason} | {voucher[:16]}... | {chat}")
        
        await send_webhook(
            "❌ รับไม่สำเร็จ",
            f"**{reason}**",
            0xff0000,
            [
                {"name": "🎟️ Voucher", "value": f"`{voucher}`", "inline": False},
                {"name": "📍 จาก", "value": chat, "inline": True},
                {"name": "⚡ ใช้เวลา", "value": f"{ms} ms", "inline": True}
            ]
        )
    
    else:
        stats["failed"] += 1
        print(f"⚠️ [{ms}ms] {status} | {voucher[:16]}...")

# ================== VOUCHER EXTRACTION ==================
def valid(code: str) -> bool:
    """ตรวจสอบความถูกต้อง"""
    if not code or len(code) < 10 or len(code) > 64:
        return False
    if not code.startswith("019"):
        return False
    if not re.match(r'^[a-zA-Z0-9]+$', code):
        return False
    return True

def extract(text: str) -> List[str]:
    """ดึง voucher จากข้อความ - รองรับทุกรูปแบบ"""
    if not text:
        return []
    
    found = []
    
    # รูปแบบ URL ทั้งหมด
    patterns = [
        r'https?://gift\.truemoney\.com/campaign/?(?:voucher_detail/?)?\?v=([A-Za-z0-9]+)',
        r'gift\.truemoney\.com/campaign/?(?:voucher_detail/?)?\?v=([A-Za-z0-9]+)',
        r'truemoney\.com/campaign/?(?:voucher_detail/?)?\?v=([A-Za-z0-9]+)',
        r'\?v=([A-Za-z0-9]{16,})',
        r'v=([A-Za-z0-9]{16,})',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            code = match.group(1).strip()
            if valid(code) and code not in seen_vouchers:
                found.append(code)
                seen_vouchers.add(code)
    
    # รูปแบบ Code เปล่า
    words = re.split(r'[\s\n\r,;.!?()\[\]{}\'\"<>/\\|`~@#$%^&*+=]+', text)
    for word in words:
        clean = re.sub(r'[^a-zA-Z0-9]', '', word)
        if valid(clean) and clean not in seen_vouchers:
            found.append(clean)
            seen_vouchers.add(clean)
    
    return found

# ================== TELEGRAM BOT ==================
async def main():
    global session
    
    # ตรวจสอบ config
    if not all([API_ID, API_HASH, PHONE, SESSION_STRING]):
        print("\n❌ กรุณาตั้งค่า Environment Variables:")
        print("   • API_ID")
        print("   • API_HASH")
        print("   • PHONE")
        print("   • SESSION_STRING")
        print("   • WEBHOOK (optional)")
        print("\n💡 วิธีสร้าง SESSION_STRING:")
        print("   python generate_session_simple.py")
        sys.exit(1)
    
    session = aiohttp.ClientSession()
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("\n❌ SESSION_STRING ไม่ถูกต้องหรือหมดอายุ")
            print("💡 รัน: python generate_session_simple.py")
            sys.exit(1)
        
        me = await client.get_me()
        
        print("=" * 70)
        print(f"✅ Login สำเร็จ: {me.first_name} ({me.phone})")
        print(f"📞 เบอร์รับเงิน: {PHONE}")
        print(f"📡 Webhook: {'✅ เปิด' if WEBHOOK else '❌ ปิด'}")
        print(f"⚡ รับพร้อมกัน: {MAX_CONCURRENT} ซอง")
        print(f"📸 QR Scanner: ✅ OpenCV")
        print("=" * 70)
        print("\n🎯 พร้อมรับซองอั่งเปา!\n")
        
        sem = asyncio.Semaphore(MAX_CONCURRENT)
        
        @client.on(events.NewMessage(incoming=True))
        async def handler(event):
            try:
                chat = await event.get_chat()
                chat_name = getattr(chat, 'title', None) or \
                           getattr(chat, 'username', None) or \
                           getattr(chat, 'first_name', 'Private')
                
                # ข้อความ
                if event.message.message:
                    text = event.message.message
                    vouchers = extract(text)
                    
                    if vouchers:
                        print(f"\n📨 {chat_name}")
                        for v in vouchers:
                            print(f"   🎯 พบ: {v[:20]}...")
                            async with sem:
                                asyncio.create_task(process(v, chat_name))
                
                # รูปภาพ (QR Code)
                if event.message.photo:
                    print(f"\n📸 สแกน QR จาก {chat_name}...")
                    try:
                        img = await event.message.download_media(bytes)
                        qr_data = await asyncio.to_thread(scan_qr, img)
                        
                        if qr_data:
                            vouchers = extract(qr_data)
                            if vouchers:
                                for v in vouchers:
                                    print(f"   🎯 QR: {v[:20]}...")
                                    async with sem:
                                        asyncio.create_task(process(v, chat_name))
                    except:
                        pass
            
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # เคลียร์ cache
        async def clear():
            while True:
                await asyncio.sleep(CACHE_TIME)
                seen_vouchers.clear()
        
        asyncio.create_task(clear())
        
        # แสดงสถิติทุก 5 นาที
        async def show_stats():
            while True:
                await asyncio.sleep(300)
                if stats["total"] > 0:
                    rate = (stats["success"] / stats["total"]) * 100
                    print(f"\n📊 สถิติ: ✅ {stats['success']} | ❌ {stats['failed']} | 📈 {rate:.1f}%\n")
        
        asyncio.create_task(show_stats())
        
        print("✅ Bot เริ่มทำงาน!\n")
        await client.run_until_disconnected()
    
    except KeyboardInterrupt:
        print("\n\n⚠️ หยุดการทำงาน...")
    except Exception as e:
        print(f"\n❌ Critical Error: {e}")
    finally:
        if session:
            await session.close()
        sys.exit(0)

# ================== RUN ==================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ ปิดโปรแกรม")
    except Exception as e:
        print(f"❌ Error: {e}")
        
