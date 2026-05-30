import asyncio
import re
import os
import base64
from zoneinfo import ZoneInfo
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon import errors
from datetime import datetime, timezone
import jdatetime
from dotenv import load_dotenv

load_dotenv()

# تنظیمات
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")

if not SESSION_STRING:
    raise ValueError("TELEGRAM_SESSION_STRING در محیط تعریف نشده است.")

TELEGRAM_CHANNELS = [
    '@arisping', '@PrivateVPNs', '@Configir98', '@AzadLinkIran',
    '@Vpn_m2s', '@amirambitfree', '@FreakConfig', '@makvaslim',
]

NPV_CHANNELS = ['@Configir98', '@mitivpn', '@oxnet_ir']

MY_CHANNEL = '@V2ray4Free1'

CONFIG_PATTERN = re.compile(r'(?:vmess|vless|ss|shadowsocks|trojan|hysteria|hysteria2|hy2)://[^\s<>\"]+')
SUB_LINK_PATTERN = re.compile(r'https?://[^\s<>\"]+')

def fetch_sub_content(url):
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8', errors='ignore')
            try:
                padding = len(content) % 4
                if padding:
                    content += '=' * (4 - padding)
                return base64.b64decode(content).decode('utf-8', errors='ignore')
            except:
                return content
    except:
        return ""

async def fetch_configs():
    all_configs = set()

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    SPECIAL_GROUP = '@makvaslim'
    MAX_CONFIGS_FROM_GROUP = 40

    try:
        await client.start()
        print("✅ اتصال برقرار شد.\n")

        now = datetime.now(timezone.utc)
        time_threshold = now.replace(hour=0, minute=0, second=0, microsecond=0)

        for channel in TELEGRAM_CHANNELS:
            try:
                entity = await client.get_entity(channel)
                print(f"🔎 بررسی: {channel}")

                last_id = 0
                channel_count = 0
                is_special = (channel == SPECIAL_GROUP)
                group_set = set() if is_special else None

                while True:
                    messages = await client(GetHistoryRequest(
                        peer=entity, limit=100, offset_id=last_id,
                        offset_date=None, add_offset=0, max_id=0, min_id=0, hash=0
                    ))

                    if not messages.messages:
                        break

                    stop = False
                    for msg in messages.messages:
                        if msg.date < time_threshold:
                            stop = True
                            break

                        if msg.message:
                            direct = CONFIG_PATTERN.findall(msg.message)
                            if direct:
                                before = len(all_configs)
                                all_configs.update(direct)
                                channel_count += len(all_configs) - before
                                if is_special:
                                    group_set.update(direct)

                            for url in SUB_LINK_PATTERN.findall(msg.message):
                                if any(x in url.lower() for x in ['t.me','google','instagram','youtube','twitter']):
                                    continue
                                sub_content = await asyncio.to_thread(fetch_sub_content, url)
                                sub = CONFIG_PATTERN.findall(sub_content)
                                if sub:
                                    before = len(all_configs)
                                    all_configs.update(sub)
                                    channel_count += len(all_configs) - before
                                    if is_special:
                                        group_set.update(sub)

                    if stop or len(messages.messages) < 100:
                        break
                    last_id = messages.messages[-1].id

                print(f"   ✅ از {channel} حدود {channel_count} کانفیگ پردازش شد\n")

            except Exception as e:
                print(f"❌ خطا در {channel}: {e}")

    finally:
        await client.disconnect()

    return list(all_configs)

def clean_configs(configs: list) -> list:
    cleaned = []
    for cfg in configs:
        clean_cfg = re.split(r'\s*#', cfg)[0].strip()
        clean_cfg = re.sub(r'\s+$', '', clean_cfg)
        if clean_cfg:
            cleaned.append(f"{clean_cfg}#@V2ray4Free1")
    return cleaned

def save_to_files(all_configs: list) -> list:
    cleaned_all = clean_configs(all_configs)
    txt_filename = "telegram_configs.txt"
    base64_filename = "telegram_configs_base64.txt"
    today_str = datetime.now().strftime("%Y-%m-%d")

    previous_set = set()
    is_new_day = True

    if os.path.exists(txt_filename):
        try:
            with open(txt_filename, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
                if lines and lines[0].startswith("# Date: "):
                    if lines[0].split("# Date: ")[1].strip() == today_str:
                        is_new_day = False
                        previous_set = set(line.strip() for line in lines[1:] if line.strip() and not line.startswith('#'))
        except:
            pass

    new_configs = [cfg for cfg in cleaned_all if cfg not in previous_set]

    if not new_configs:
        print("هیچ کانفیگ جدیدی پیدا نشد.")
        return []

    mode = "w" if is_new_day else "a"
    with open(txt_filename, mode, encoding="utf-8") as f:
        if is_new_day:
            f.write(f"# Date: {today_str}\n")
        for cfg in new_configs:
            f.write(cfg + "\n")

    print(f"{len(new_configs)} کانفیگ {'جدید اضافه شد' if mode=='a' else 'برای روز جدید ذخیره شد'}")

    # ساخت base64
    with open(txt_filename, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if content:
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        with open(base64_filename, "w", encoding="utf-8") as f:
            f.write(encoded)

    return new_configs

async def post_to_channel(new_configs: list):
    if not new_configs:
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    try:
        await client.start()

        now_jalali = jdatetime.date.today()
        tehran_tz = ZoneInfo("Asia/Tehran")
        time_str = datetime.now(tehran_tz).strftime("%H:%M")

        first_message = (
            f"⭕️ به‌روزرسانی کانفیگ‌ها\n"
            f"{weekdays_fa[now_jalali.weekday()]} {now_jalali.day} {month_names_fa[now_jalali.month-1]} {now_jalali.year}\n"
            f"ساعت: {time_str}\n"
            f"تعداد جدید: {len(new_configs)} کانفیگ 👇"
        )
        await client.send_message(MY_CHANNEL, first_message)
        await asyncio.sleep(8)

        chunk_size = 12   # کاهش دادم برای جلوگیری از پیام طولانی
        for i in range(0, len(new_configs), chunk_size):
            chunk = new_configs[i:i+chunk_size]
            msg = "```\n" + "\n".join(chunk) + "\n```"
            await client.send_message(MY_CHANNEL, msg)
            await asyncio.sleep(8)

    finally:
        await client.disconnect()

# ====================== قابلیت جدید NPV ======================

async def fetch_and_send_npvt(client):
    today = datetime.now().date()
    for channel in NPV_CHANNELS:
        try:
            entity = await client.get_entity(channel)
            print(f"📁 بررسی فایل npvt از: {channel}")

            last_id = 0
            while True:
                messages = await client(GetHistoryRequest(
                    peer=entity, limit=30, offset_id=last_id,
                    offset_date=None, add_offset=0, max_id=0, min_id=0, hash=0
                ))
                if not messages.messages:
                    break

                for msg in messages.messages:
                    if msg.date.date() < today:
                        return

                    if msg.media and hasattr(msg.media, 'document'):
                        doc = msg.media.document
                        for attr in doc.attributes:
                            if hasattr(attr, 'file_name') and attr.file_name.endswith('.npvt'):
                                file_path = await client.download_media(msg)
                                new_name = attr.file_name.replace('.npvt', '#@V2ray4Free1.npvt')
                                await client.send_file(
                                    MY_CHANNEL, 
                                    file_path, 
                                    caption=f"📁 فایل NPV Tunnel\nاز کانال: {channel}",
                                    attributes=[{"file_name": new_name}]
                                )
                                print(f"✅ فایل npvt ارسال شد: {new_name}")
                                await asyncio.sleep(10)
                                break
                last_id = messages.messages[-1].id
        except Exception as e:
            print(f"خطا در npvt از {channel}: {e}")

# ====================== Main ======================

if __name__ == "__main__":
    try:
        results = asyncio.run(fetch_configs())
        new_ones = save_to_files(results)
        asyncio.run(post_to_channel(new_ones))

        # ارسال فایل‌های npvt
        print("\n🔍 شروع جستجوی فایل‌های NPV Tunnel...")
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        asyncio.run(client.start())
        asyncio.run(fetch_and_send_npvt(client))
        asyncio.run(client.disconnect())

    except Exception as e:
        print(f"خطای کلی: {e}")
