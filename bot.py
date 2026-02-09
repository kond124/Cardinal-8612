"""
🧧 TrueMoney Auto-Claim Bot - Chinese New Year Edition
ไฟล์เดียวจบ ใช้งานง่าย รองรับ QR Code
Optimized for Render.com Free Tier
"""

import asyncio
import re
import os
import sys
import time
import base64
from datetime import datetime
from typing import Optional, List, Set
from io import BytesIO

# ================== CONFIGURATION ==================
API_ID = int(os.getenv("API_ID", "22644824"))
API_HASH = os.getenv("API_HASH", "7e0b2f70e207fd5ff8d531ffee84cdb8")
PHONE = os.getenv("PHONE", "0803520247")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# Webhooks (ใส่แค่อันเดียวก็ได้)
WEBHOOK = os.getenv("WEBHOOK", "https://discord.com/api/webhooks/1425169466148261951/Npqs_vMGMGzvJja87mmr0dNWUJ7nmaPxPellBMX30nNfNZ0uC4tG2sh-ADmKSFFP7H2t")  # ใช้ webhook เดียว ง่ายๆ

# Performance
MAX_CONCURRENT = 10  # รับได้ 10 ซองพร้อมกัน
CACHE_TIME = 20  # วินาที

# ================== INSTALL & IMPORT ==================
print("🔧 กำลังติดตั้ง dependencies...")

import subprocess
def install_package(package):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])
    except:
        pass

# ติดตั้งแพ็คเกจที่จำเป็น
packages = {
    "telethon": "telethon",
    "aiohttp": "aiohttp",
    "PIL": "Pillow",
    "cv2": "opencv-python-headless"  # ใช้แทน pyzbar (ไม่ต้อง apt-get)
}

for module, package in packages.items():
    try:
        __import__(module)
    except:
        print(f"  📦 Installing {package}...")
        install_package(package)

import aiohttp
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from PIL import Image
import cv2
import numpy as np

print("✅ Dependencies พร้อม!\n")

# ================== GLOBAL VARS ==================
seen_vouchers: Set[str] = set()
session: Optional[aiohttp.ClientSession] = None

# ================== QR CODE SCANNER (OpenCV) ==================
def scan_qr_opencv(image_bytes: bytes) -> Optional[str]:
    """สแกน QR Code ด้วย OpenCV (ไม่ต้อง apt-get!)"""
    try:
        # แปลง bytes เป็น numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # สร้าง QR detector
        detector = cv2.QRCodeDetector()
        
        # ลอง decode
        data, bbox, _ = detector.detectAndDecode(img)
        
        if data:
            return data
        
        # ถ้าไม่ได้ ลองแปลงเป็น grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        data, bbox, _ = detector.detectAndDecode(gray)
        
        if data:
            return data
            
        # ลองปรับ contrast
        alpha = 1.5  # Contrast
        beta = 30    # Brightness
        adjusted = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
        data, bbox, _ = detector.detectAndDecode(adjusted)
        
        return data if data else None
        
    except Exception as e:
        print(f"❌ QR scan error: {e}")
        return None

# ================== WEBHOOK ==================
async def send_webhook(title: str, description: str, color: int, fields: list = None):
    """ส่ง webhook แบบง่ายๆ"""
    if not WEBHOOK or not WEBHOOK.strip():
        return
    
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if fields:
        embed["fields"] = fields
    
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(WEBHOOK, json={"embeds": [embed]}, timeout=aiohttp.ClientTimeout(total=2))
    except:
        pass

# ================== TRUEMONEY API ==================
async def claim_voucher(voucher: str) -> dict:
    """รับซองอั่งเปา"""
    url = f"https://gift.truemoney.com/campaign/vouchers/{voucher}/redeem"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    data = {"mobile": PHONE.replace("-", "").replace(" ", "")}
    
    try:
        async with session.post(url, headers=headers, data=data, timeout=aiohttp.ClientTimeout(total=5)) as resp:
            return await resp.json()
    except:
        return {"status": {"code": "ERROR"}}

async def process_voucher(voucher: str, chat_name: str = "Unknown"):
    """ประมวลผลซอง"""
    start = time.time()
    result = await claim_voucher(voucher)
    elapsed = int((time.time() - start) * 1000)
    
    status = result.get("status", {}).get("code", "UNKNOWN")
    
    if status == "SUCCESS":
        amount = result.get("data", {}).get("voucher", {}).get("amount_baht", 0)
        print(f"🧧 [{elapsed}ms] รับได้ {amount:.2f} บาท | {voucher[:20]}... | {chat_name}")
        
        await send_webhook(
            "🧧 รับเงินสำเร็จ!",
            f"💰 **ได้รับ {amount:.2f} บาท**\n🎟️ `{voucher}`",
            0x00ff00,  # สีเขียว
            [
                {"name": "💵 จำนวน", "value": f"{amount:.2f} THB", "inline": True},
                {"name": "⚡ ความเร็ว", "value": f"{elapsed} ms", "inline": True},
                {"name": "📍 จาก", "value": chat_name, "inline": True},
                {"name": "🕐 เวลา", "value": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "inline": False}
            ]
        )
    
    elif status in ["VOUCHER_OUT_OF_STOCK", "VOUCHER_NOT_FOUND"]:
        reason = "🔴 ซองหมด/คนรับหมด" if status == "VOUCHER_OUT_OF_STOCK" else "❌ ไม่มีซองในระบบ"
        print(f"❌ [{elapsed}ms] {reason} | {voucher[:20]}... | {chat_name}")
        
        await send_webhook(
            "❌ รับไม่สำเร็จ",
            f"{reason}\n🎟️ `{voucher}`",
            0xff0000,  # สีแดง
            [
                {"name": "📍 จาก", "value": chat_name, "inline": True},
                {"name": "⚡ ใช้เวลา", "value": f"{elapsed} ms", "inline": True}
            ]
        )

# ================== VOUCHER EXTRACTION ==================
def is_valid_voucher(code: str) -> bool:
    """ตรวจสอบ voucher"""
    if not code or len(code) < 10 or len(code) > 64:
        return False
    if not code.startswith("019"):
        return False
    if not re.match(r'^[a-zA-Z0-9]+$', code):
        return False
    return True

def extract_vouchers(text: str) -> List[str]:
    """ดึง voucher จากข้อความ"""
    if not text:
        return []
    
    found = []
    
    # URL pattern
    for match in re.finditer(r'https?://gift\.truemoney\.com/campaign/?(?:voucher_detail/?)?\?v=([A-Za-z0-9]+)', text, re.IGNORECASE):
        code = match.group(1).strip()
        if is_valid_voucher(code) and code not in seen_vouchers:
            found.append(code)
            seen_vouchers.add(code)
    
    # Direct code
    words = re.split(r'[\s\n\r,;.!?()\[\]{}\'\"<>/\\]+', text)
    for word in words:
        clean = re.sub(r'[^a-zA-Z0-9]', '', word)
        if is_valid_voucher(clean) and clean not in seen_vouchers:
            found.append(clean)
            seen_vouchers.add(clean)
    
    return found

# ================== MAIN BOT ==================
async def start_bot():
    global session
    
    print("=" * 60)
    print("🧧 TrueMoney Auto-Claim Bot - Chinese New Year Edition")
    print("=" * 60)
    
    # ตรวจสอบ config
    if not all([API_ID, API_HASH, PHONE, SESSION_STRING]):
        print("❌ Error: กรุณาตั้งค่า Environment Variables:")
        print("   - API_ID")
        print("   - API_HASH")
        print("   - PHONE")
        print("   - SESSION_STRING")
        print("   - WEBHOOK (optional)")
        sys.exit(1)
    
    session = aiohttp.ClientSession()
    
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    if not await client.is_user_authorized():
        print("❌ Session String ไม่ถูกต้อง")
        sys.exit(1)
    
    me = await client.get_me()
    print(f"✅ Login: {me.first_name} ({me.phone})")
    print(f"📞 เบอร์รับเงิน: {PHONE}")
    print(f"📡 Webhook: {'✅' if WEBHOOK else '❌'}")
    print(f"⚡ Concurrent: {MAX_CONCURRENT} ซอง")
    print(f"📸 QR Scanner: ✅ OpenCV")
    print("=" * 60)
    print("🎯 กำลังรอรับซองตรุษจีน...\n")
    
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        try:
            chat = await event.get_chat()
            chat_name = getattr(chat, 'title', None) or getattr(chat, 'first_name', 'Private')
            
            # ตรวจสอบข้อความ
            if event.message.message:
                vouchers = extract_vouchers(event.message.message)
                for v in vouchers:
                    print(f"🎯 พบซอง: {v[:20]}... จาก {chat_name}")
                    async with semaphore:
                        asyncio.create_task(process_voucher(v, chat_name))
            
            # ตรวจสอบรูปภาพ (QR Code)
            if event.message.photo:
                print(f"📸 กำลังสแกน QR จาก {chat_name}...")
                try:
                    img_bytes = await event.message.download_media(bytes)
                    qr_data = await asyncio.to_thread(scan_qr_opencv, img_bytes)
                    
                    if qr_data:
                        print(f"📸 QR: {qr_data[:60]}...")
                        vouchers = extract_vouchers(qr_data)
                        for v in vouchers:
                            print(f"🎯 พบซองจาก QR: {v[:20]}...")
                            async with semaphore:
                                asyncio.create_task(process_voucher(v, chat_name))
                    else:
                        print("⚠️ ไม่พบ QR Code")
                except Exception as e:
                    print(f"❌ QR error: {e}")
        
        except Exception as e:
            print(f"❌ Handler error: {e}")
    
    # เคลียร์ cache
    async def clear_cache():
        while True:
            await asyncio.sleep(CACHE_TIME)
            seen_vouchers.clear()
    
    asyncio.create_task(clear_cache())
    
    print("✅ Bot พร้อมทำงาน!")
    await client.run_until_disconnected()

# ================== RUN ==================
if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("\n⚠️ หยุดการทำงาน...")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
