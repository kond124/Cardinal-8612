"""
สร้าง Session String สำหรับ Telegram Bot
รันไฟล์นี้ 1 ครั้งเพื่อเอา SESSION_STRING
"""

import sys
import subprocess

# ติดตั้ง telethon ถ้ายังไม่มี
try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except:
    print("📦 กำลังติดตั้ง telethon...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "telethon"])
    from telethon import TelegramClient
    from telethon.sessions import StringSession

import asyncio

async def main():
    print("=" * 60)
    print("🔐 สร้าง Telegram Session String")
    print("=" * 60)
    
    # ใส่ข้อมูล
    api_id = input("📱 API_ID: ")
    api_hash = input("🔑 API_HASH: ")
    phone = input("📞 เบอร์โทร (เช่น +66812345678): ")
    
    client = TelegramClient(StringSession(), int(api_id), api_hash)
    
    await client.connect()
    
    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        otp = input("📟 OTP: ")
        
        try:
            await client.sign_in(phone, otp)
        except Exception as e:
            if "password" in str(e).lower():
                password = input("🔐 2FA Password: ")
                await client.sign_in(password=password)
            else:
                raise e
    
    session_string = client.session.save()
    
    print("\n" + "=" * 60)
    print("✅ สำเร็จ! คัดลอก SESSION_STRING นี้:")
    print("=" * 60)
    print(f"\n{session_string}\n")
    print("=" * 60)
    print("💡 นำไปใส่ใน Environment Variable: SESSION_STRING")
    print("=" * 60)
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
