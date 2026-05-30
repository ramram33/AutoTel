import asyncio
import re
import os
import base64
from zoneinfo import ZoneInfo
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon import errors
from typing import List
from datetime import datetime, timezone, timedelta
import jdatetime
from dotenv import load_dotenv

load_dotenv()

# تنظیمات از محیط
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")

if not SESSION_STRING:
    raise ValueError("TELEGRAM_SESSION_STRING در محیط تعریف نشده است. لطفاً در GitHub Secrets اضافه کنید.")

TELEGRAM_CHANNELS = [
    '@arisping',
    '@PrivateVPNs',
    '@Configir98',
    '@AzadLinkIran',
    '@Vpn_m2s',
    '@amirambitfree',
    '@FreakConfig',
    '@makvaslim',
]

NPV_CHANNELS = ['@Configir98', '@mitivpn', '@oxnet_ir']   # کانال‌های جدید برای فایل npvt

MY_CHANNEL = '@V2ray4Free1'

# الگوهای شناسایی
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
                decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                return decoded
            except:
                return content
    except:
        return ""

async def fetch_configs():
    all_configs = set()

    client = TelegramClient(
        StringSession(SESSION_STRING),
        API_ID,
        API_HASH
    )

    SPECIAL_GROUP = '@makvaslim'
    MAX_CONFIGS_FROM_GROUP = 40

    try:
        await client.start()
        print("✅ اتصال برقرار شد. در حال اسکن پیام‌های روز جاری...\n")

        now = datetime.now(timezone.utc)
        time_threshold = now.replace(hour=0, minute=0, second=0, microsecond=0)

        print(f"اسکن پیام‌ها از: {time_threshold.strftime('%Y-%m-%d %H:%M:%S UTC')} به بعد\n")

        for channel in TELEGRAM_CHANNELS:
            try:
                entity = await client.get_entity(channel)
                print(f"🔎 بررسی کانال/گروه: {channel}")

                last_id = 0
                channel_count = 0

                is_special_group = (channel == SPECIAL_GROUP)
                group_added_configs = set() if is_special_group else None

                while True:
                    messages = await client(GetHistoryRequest(
                        peer=entity,
                        limit=100,
                        offset_id=last_id,
                        offset_date=None,
                        add_offset=0,
                        max_id=0,
                        min_id=0,
                        hash=0
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
                            print(f"   ∟ به حداکثر {MAX_CONFIGS_FROM_GROUP} کانفیگ منحصربه‌فرد از {channel} رسیدیم → توقف اسکن")
                            stop_scanning = True
                            break

                    if is_special_group and len(group_added_configs) >= MAX_CONFIGS_FROM_GROUP:
                        print(f"   ∟ به حداکثر {MAX_CONFIGS_FROM_GROUP} کانفیگ منحصربه‌فرد از {channel} رسیدیم → توقف اسکن")
                        break

                    if stop_scanning or len(messages.messages) < 100:
                        break

                    last_id = messages.messages[-1].id

                special_count = len(group_added_configs) if is_special_group else "نامحدود"
                print(f"   ✅ از {channel} تعداد تقریبی {channel_count} کانفیگ پردازش شد (منحصربه‌فرد اضافه‌شده: {special_count})\n")

            except Exception as e:
                print(f"❌ خطا در بررسی {channel}: {e}")

    finally:
        await client.disconnect()

    return list(all_configs)

def clean_configs(configs: list) -> list:
    cleaned = []
    for cfg in configs:
        clean_cfg = re.split(r'\s*#', cfg)[0].strip()
        clean_cfg = re.sub(r'\s+$', '', clean_cfg)
        if clean_cfg:
            tagged = f"{clean_cfg}#@V2ray4Free1"
            cleaned.append(tagged)
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
                    file_date = lines[0].split("# Date: ")[1].strip()
                    if file_date == today_str:
                        is_new_day = False
                        previous_set = set(line.strip() for line in lines[1:] if line.strip() and not line.startswith('#'))
        except:
            pass

    new_configs = [cfg for cfg in cleaned_all if cfg not in previous_set]

    if not new_configs:
        print("هیچ کانفیگ جدیدی پیدا نشد.")
        return []

    mode = "w" if is_new_day else "a"
    try:
        with open(txt_filename, mode, encoding="utf-8") as f:
            if is_new_day:
                f.write(f"# Date: {today_str}\n")
            for cfg in new_configs:
                f.write(cfg + "\n")
        print(f"{len(new_configs)} کانفیگ {'جدید اضافه شد' if mode == 'a' else 'برای روز جدید ذخیره شد (overwrite)'}")
    except Exception as e:
        print(f"خطا در نوشتن فایل txt: {e}")

    try:
        with open(txt_filename, "r", encoding="utf-8") as f:
            full_content = f.read().strip()
        if full_content:
            encoded = base64.b64encode(full_content.encode("utf-8")).decode("utf-8")
            with open(base64_filename, "w", encoding="utf-8") as f:
                f.write(encoded)
            print("فایل base64 بروز شد.")
    except Exception as e:
        print(f"خطا در ساخت base64: {e}")

    return new_configs

# ====================== قابلیت جدید: استخراج فایل‌های .npvt ======================

async def fetch_npvt_files(client):
    npvt_files = []
    today = datetime.now().date()

    for channel in NPV_CHANNELS:
        try:
            entity = await client.get_entity(channel)
            print(f"🔎 بررسی فایل npvt از کانال: {channel}")

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

                for msg in messages.messages:
                    if msg.date.date() < today:
                        break

                    if msg.media and hasattr(msg.media, 'document'):
                        doc = msg.media.document
                        if doc and doc.mime_type and 'octet-stream' in doc.mime_type.lower():
                            for attr in doc.attributes:
                                if hasattr(attr, 'file_name') and attr.file_name and attr.file_name.endswith('.npvt'):
                                    file_name = attr.file_name
                                    # دانلود فایل
                                    file_path = await client.download_media(msg, file=file_name)
                                    npvt_files.append((file_path, file_name))
                                    print(f"   فایل npvt پیدا شد: {file_name}")
                                    break

                if len(messages.messages) < 50 or msg.date.date() < today:
                    break
                last_id = messages.messages[-1].id

        except Exception as e:
            print(f"❌ خطا در بررسی npvt از {channel}: {e}")

    return npvt_files

async def send_npvt_files(client, npvt_files):
    if not npvt_files:
        return

    for file_path, original_name in npvt_files:
        try:
            # اضافه کردن نام کانال به نام فایل
            new_name = f"{original_name.rsplit('.', 1)[0]}#@V2ray4Free1.npvt"
            
            await client.send_file(
                MY_CHANNEL,
                file_path,
                caption=f"📁 فایل NPV Tunnel\nنام اصلی: {original_name}",
                attributes=[{"file_name": new_name}]
            )
            print(f"فایل {original_name} با موفقیت ارسال شد")
            await asyncio.sleep(8)  # فاصله برای جلوگیری از flood
        except Exception as e:
            print(f"خطا در ارسال فایل {original_name}: {e}")

# ====================== Main ======================

if __name__ == "__main__":
    try:
        results = asyncio.run(fetch_configs())
        new_ones = save_to_files(results)
        asyncio.run(post_to_channel(new_ones))

        # قابلیت جدید: استخراج و ارسال فایل‌های npvt
        print("\n🔄 شروع بررسی فایل‌های NPV Tunnel...")
        client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
        asyncio.run(client.start())
        npvt_files = asyncio.run(fetch_npvt_files(client))
        asyncio.run(send_npvt_files(client, npvt_files))
        asyncio.run(client.disconnect())

    except KeyboardInterrupt:
        print("\nتوسط کاربر متوقف شد.")
    except Exception as e:
        print(f"خطای کلی: {e}")
