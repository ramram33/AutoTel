import asyncio
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon import errors
from dotenv import load_dotenv

load_dotenv()

# تنظیمات
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")

if not SESSION_STRING:
    raise ValueError("TELEGRAM_SESSION_STRING در محیط تعریف نشده است.")

SOURCE_CHANNELS = [
    '@Configir98',
    '@mitivpn',
    '@oxnet_ir'
]

MY_CHANNEL = '@V2ray4Free1'
YOUR_TAG = "@V2ray4Free1"

TRACK_FILE = "sent_npvt_files.txt"

async def main():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    try:
        await client.start()
        print("✅ اتصال برقرار شد. در حال جمع‌آوری فایل‌های .npvt...\n")

        tehran_tz = ZoneInfo("Asia/Tehran")
        today = datetime.now(tehran_tz).date()
        today_str = today.strftime("%Y-%m-%d")

        # مدیریت فایل tracking بر اساس روز جاری
        sent_files = load_sent_files(today_str)

        for channel in SOURCE_CHANNELS:
            try:
                entity = await client.get_entity(channel)
                print(f"🔎 بررسی کانال: {channel}")

                last_id = 0

                while True:
                    messages = await client(GetHistoryRequest(
                        peer=entity,
                        limit=50,
                        offset_id=last_id,
                        offset_date=None,
                        add_offset=0,
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))

                    if not messages.messages:
                        break

                    stop = False
                    for msg in messages.messages:
                        msg_date = msg.date.astimezone(tehran_tz).date()
                        if msg_date < today:
                            stop = True
                            break

                        if msg.document and msg.document.mime_type == "application/octet-stream":
                            filename = msg.document.attributes[0].file_name if msg.document.attributes else None
                            
                            if filename and filename.endswith('.npvt'):
                                file_key = f"{channel}_{filename}"
                                if file_key in sent_files:
                                    continue

                                # دانلود
                                file_path = await client.download_media(msg, file=filename)
                                print(f"   دانلود شد: {filename}")

                                # تغییر نام
                                new_filename = f"{filename.replace('.npvt', '')}_{YOUR_TAG}.npvt"
                                new_path = os.path.join(os.getcwd(), new_filename)
                                os.rename(file_path, new_path)

                                # ارسال فقط با تگ کانال خودت
                                await client.send_file(MY_CHANNEL, new_path, caption=YOUR_TAG)
                                print(f"   ارسال شد: {new_filename}")

                                # ثبت ارسال
                                sent_files.add(file_key)
                                save_sent_files(sent_files, today_str)

                                # پاک کردن فایل محلی
                                if os.path.exists(new_path):
                                    os.remove(new_path)

                    if stop or len(messages.messages) < 50:
                        break

                    last_id = messages.messages[-1].id

            except Exception as e:
                print(f"❌ خطا در کانال {channel}: {e}")

        print("\n✅ جمع‌آوری و ارسال فایل‌های .npvt امروز به پایان رسید.")

    finally:
        await client.disconnect()


def load_sent_files(today_str):
    """فایل tracking را لود می‌کند و اگر مربوط به روز قبل بود، پاک می‌کند"""
    if not os.path.exists(TRACK_FILE):
        return set()

    try:
        with open(TRACK_FILE, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if first_line.startswith("# Date: "):
                file_date = first_line.split("# Date: ")[1].strip()
                if file_date == today_str:
                    # همان روز است → لیست را بخوان
                    return set(line.strip() for line in f if line.strip())
                else:
                    print(f"فایل tracking مربوط به روز قبل ({file_date}) بود → پاکسازی برای روز جدید")
            else:
                print("فایل tracking بدون تاریخ بود → پاکسازی")
    except:
        pass

    # پاک کردن فایل برای روز جدید
    open(TRACK_FILE, "w", encoding="utf-8").close()
    return set()


def save_sent_files(sent_files, today_str):
    """ذخیره لیست با تاریخ روز جاری در ابتدای فایل"""
    with open(TRACK_FILE, "w", encoding="utf-8") as f:
        f.write(f"# Date: {today_str}\n")
        for item in sent_files:
            f.write(item + "\n")


if __name__ == "__main__":
    asyncio.run(main())
