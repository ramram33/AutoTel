import asyncio
import re
import os
import base64
import hashlib
from zoneinfo import ZoneInfo
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon import errors
from datetime import datetime, timezone
import jdatetime
from dotenv import load_dotenv

load_dotenv()

# ==================== تنظیمات ====================
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

# الگوها
CONFIG_PATTERN = re.compile(r'(?:vmess|vless|ss|shadowsocks|trojan|hysteria|hysteria2|hy2)://[^\s<>\"]+')
SUB_LINK_PATTERN = re.compile(r'https?://[^\s<>\"]+')
NPV_EXTENSION = '.npvt'

# =================================================

def get_file_hash(file_bytes: bytes) -> str:
    return hashlib.md5(file_bytes).hexdigest()

def load_sent_npv_hashes():
    hashes = set()
    if os.path.exists("npv_sent_hashes.txt"):
        try:
            with open("npv_sent_hashes.txt", "r", encoding="utf-8") as f:
                hashes = set(line.strip() for line in f if line.strip())
        except:
            pass
    return hashes

def save_sent_npv_hashes(npv_files):
    try:
        with open("npv_sent_hashes.txt", "a", encoding="utf-8") as f:
            for _, _, file_hash in npv_files:
                f.write(file_hash + "\n")
    except:
        pass

async def fetch_configs():
    all_configs = set()
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    SPECIAL_GROUP = '@makvaslim'
    MAX_CONFIGS_FROM_GROUP = 40

    try:
        await client.start()
        print("✅ اتصال برقرار شد...\n")

        now = datetime.now(timezone.utc)
        time_threshold = now.replace(hour=0, minute=0, second=0, microsecond=0)

        print(f"اسکن پیام‌ها از: {time_threshold.strftime('%Y-%m-%d %H:%M:%S UTC')} به بعد\n")

        # ==================== استخراج لینک‌های متنی ====================
        for channel in TELEGRAM_CHANNELS:
            try:
                entity = await client.get_entity(channel)
                print(f"🔎 بررسی کانال: {channel}")

                last_id = 0
                channel_count = 0
                is_special_group = (channel == SPECIAL_GROUP)
                group_added_configs = set() if is_special_group else None

                while True:
                    messages = await client(GetHistoryRequest(
                        peer=entity, limit=100, offset_id=last_id,
                        offset_date=None, add_offset=0, max_id=0, min_id=0, hash=0
                    ))

                    if not messages.messages:
                        break

                    stop_scanning = False

                    for msg in messages.messages:
                        if msg.date < time_threshold:
                            print(f"   ∟ رسید به پیام قبل از امروز → توقف اسکن {channel}")
                            stop_scanning = True
                            break

                        if msg.message:
                            direct = CONFIG_PATTERN.findall(msg.message)
                            if direct:
                                before = len(all_configs)
                                all_configs.update(direct)
                                newly_added = len(all_configs) - before
                                channel_count += newly_added
                                if is_special_group:
                                    group_added_configs.update(direct)

                            urls = SUB_LINK_PATTERN.findall(msg.message)
                            for url in urls:
                                if any(x in url.lower() for x in ['t.me', 'google', 'instagram', 'youtube', 'twitter']):
                                    continue
                                sub_content = await asyncio.to_thread(fetch_sub_content, url)
                                sub_configs = CONFIG_PATTERN.findall(sub_content)
                                if sub_configs:
                                    before = len(all_configs)
                                    all_configs.update(sub_configs)
                                    newly_added = len(all_configs) - before
                                    channel_count += newly_added
                                    if is_special_group:
                                        group_added_configs.update(sub_configs)

                        if is_special_group and len(group_added_configs) >= MAX_CONFIGS_FROM_GROUP:
                            print(f"   ∟ به حداکثر {MAX_CONFIGS_FROM_GROUP} کانفیگ از {channel} رسیدیم → توقف")
                            stop_scanning = True
                            break

                    if is_special_group and len(group_added_configs) >= MAX_CONFIGS_FROM_GROUP:
                        break

                    if stop_scanning or len(messages.messages) < 100:
                        break

                    last_id = messages.messages[-1].id

                special_count = len(group_added_configs) if is_special_group else "نامحدود"
                print(f"   ✅ از {channel} تعداد تقریبی {channel_count} کانفیگ پردازش شد (منحصربه‌فرد: {special_count})\n")

            except Exception as e:
                print(f"❌ خطا در بررسی {channel}: {e}")

        # ==================== استخراج فایل‌های NPV ====================
        npv_files = await fetch_npv_files(client)

    finally:
        await client.disconnect()

    return list(all_configs), npv_files


async def fetch_npv_files(client):
    npv_files = []  # (bytes, new_filename, hash)
    sent_hashes = load_sent_npv_hashes()

    for channel in NPV_CHANNELS:
        try:
            entity = await client.get_entity(channel)
            print(f"🔎 بررسی فایل‌های NPV از: {channel}")

            last_id = 0
            while True:
                messages = await client(GetHistoryRequest(
                    peer=entity, limit=50, offset_id=last_id,
                    offset_date=None, add_offset=0, max_id=0, min_id=0, hash=0
                ))

                if not messages.messages:
                    break

                for msg in messages.messages:
                    if msg.date < datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0):
                        break

                    if msg.document and msg.file and msg.file.name and msg.file.name.lower().endswith(NPV_EXTENSION):
                        file_bytes = await msg.download_media(bytes)
                        file_hash = get_file_hash(file_bytes)

                        if file_hash in sent_hashes:
                            print(f"   ⏭ فایل تکراری: {msg.file.name}")
                            continue

                        base_name = os.path.splitext(msg.file.name)[0]
                        new_filename = f"{base_name}_@V2ray4Free1{NPV_EXTENSION}"

                        npv_files.append((file_bytes, new_filename, file_hash))
                        print(f"   📄 فایل NPV جدید پیدا شد: {new_filename}")

                if len(messages.messages) < 50:
                    break
                last_id = messages.messages[-1].id

        except Exception as e:
            print(f"خطا در بررسی NPV از {channel}: {e}")

    return npv_files


def clean_configs(configs: list) -> list:
    cleaned = []
    for cfg in configs:
        clean_cfg = re.split(r'\s*#', cfg)[0].strip()
        clean_cfg = re.sub(r'\s+$', '', clean_cfg)
        if clean_cfg:
            tagged = f"{clean_cfg}#@V2ray4Free1"
            cleaned.append(tagged)
    return cleaned


def save_to_files(configs: list):
    cleaned_all = clean_configs(configs)
    txt_filename = "telegram_configs.txt"
    base64_filename = "telegram_configs_base64.txt"
    today_str = datetime.now().strftime("%Y-%m-%d")

    with open(txt_filename, "w", encoding="utf-8") as f:
        f.write(f"# Date: {today_str}\n")
        for cfg in cleaned_all:
            f.write(cfg + "\n")

    with open(txt_filename, "r", encoding="utf-8") as f:
        full_content = f.read().strip()
    encoded = base64.b64encode(full_content.encode("utf-8")).decode("utf-8")
    with open(base64_filename, "w", encoding="utf-8") as f:
        f.write(encoded)

    return cleaned_all


async def post_to_channel(configs: list, npv_files: list):
    if not configs and not npv_files:
        print("هیچ محتوای جدیدی برای ارسال وجود ندارد.")
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    try:
        await client.start()

        now_jalali = jdatetime.date.today()
        tehran_tz = ZoneInfo("Asia/Tehran")
        time_str = datetime.now(tehran_tz).strftime("%H:%M")

        first_message = (
            f"⭕️ به‌روزرسانی کانفیگ‌ها\n"
            f"{weekday_name} {now_jalali.day} {month_name} {now_jalali.year}\n"
            f"ساعت: {time_str}\n"
            f"تعداد جدید: {len(configs)} کانفیگ + {len(npv_files)} فایل NPV 👇"
        )
        await client.send_message(MY_CHANNEL, first_message)
        await asyncio.sleep(10)

        # ارسال لینک‌های متنی
        chunk_size = 15
        i = 0
        block_number = 1
        while i < len(configs):
            chunk = configs[i:i + chunk_size]
            message = "```\n" + "\n".join(chunk) + "\n```"

            if len(message) <= 3800:
                await client.send_message(MY_CHANNEL, message)
                print(f"بخش {block_number} ارسال شد")
                await asyncio.sleep(10)
                i += chunk_size
                block_number += 1
            else:
                print(f"بخش {block_number} طولانی → تقسیم شد")
                half = len(chunk) // 2
                await client.send_message(MY_CHANNEL, "```\n" + "\n".join(chunk[:half]) + "\n```")
                await asyncio.sleep(5)
                await client.send_message(MY_CHANNEL, "```\n" + "\n".join(chunk[half:]) + "\n```")
                await asyncio.sleep(10)
                i += chunk_size
                block_number += 1

        # ارسال فایل‌های NPV
        for file_bytes, filename, _ in npv_files:
            await client.send_file(MY_CHANNEL, file_bytes, caption=filename)
            print(f"📤 فایل NPV ارسال شد: {filename}")
            await asyncio.sleep(8)

        # ذخیره هش برای جلوگیری از تکرار
        save_sent_npv_hashes(npv_files)

    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        configs, npv_files = asyncio.run(fetch_configs())
        new_configs = save_to_files(configs)
        asyncio.run(post_to_channel(new_configs, npv_files))
    except Exception as e:
        print(f"خطای کلی: {e}")
