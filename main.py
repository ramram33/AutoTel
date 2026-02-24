import asyncio
import re
import os
import base64
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon import errors
from typing import List
from datetime import datetime, timezone, timedelta
import jdatetime
from dotenv import load_dotenv

load_dotenv()

# تنظیمات از محیط (در GitHub Actions از Secrets خوانده می‌شود)
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("TELEGRAM_SESSION_STRING")  # رشته StringSession

if not SESSION_STRING:
    raise ValueError("TELEGRAM_SESSION_STRING در محیط تعریف نشده است. لطفاً در GitHub Secrets اضافه کنید.")

TELEGRAM_CHANNELS = [
    '@arisping',
    '@PrivateVPNs',
    '@AzadLinkIran',
    '@Vpn_m2s',
    '@amirambitfree',
    '@FreakConfig',
    '@makvaslim',
]

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

    # استفاده از StringSession بدون فایل روی دیسک
    client = TelegramClient(
        StringSession(SESSION_STRING),
        API_ID,
        API_HASH
        # بدون پروکسی در محیط Actions
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

    filename = "telegram_configs.txt"
    previous_set = set()

    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                previous_lines = f.read().splitlines()
                previous_set = set(line.strip() for line in previous_lines if line.strip())
        except Exception as e:
            print(f"خطا در خواندن فایل قبلی: {e}")

    new_configs = [cfg for cfg in cleaned_all if cfg not in previous_set]

    if not new_configs:
        print("هیچ کانفیگ جدیدی پیدا نشد.")
        return []

    try:
        with open(filename, "a", encoding="utf-8") as f:
            for cfg in new_configs:
                f.write(cfg + "\n")
        print(f"{len(new_configs)} کانفیگ جدید به فایل اضافه شد.")
    except Exception as e:
        print(f"خطا در نوشتن در فایل: {e}")

    try:
        with open(filename, "r", encoding="utf-8") as f:
            full_content = f.read().strip()
        if full_content:
            encoded = base64.b64encode(full_content.encode("utf-8")).decode("utf-8")
            with open("telegram_configs_base64.txt", "w", encoding="utf-8") as f:
                f.write(encoded)
            print("فایل base64 بروز شد.")
    except Exception as e:
        print(f"خطا در ساخت base64: {e}")

    return new_configs

async def post_to_channel(new_configs: list):
    if not new_configs:
        print("کانفیگی برای ارسال وجود ندارد.")
        return

    client = TelegramClient(
        StringSession(SESSION_STRING),
        API_ID,
        API_HASH
        # بدون پروکسی
    )
    
    try:
        await client.start()
        print("کلاینت برای ارسال پست‌ها آماده شد")

        now_jalali = jdatetime.date.today()
        weekdays_fa = ["شنبه", "یک‌شنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه"]
        weekday_name = weekdays_fa[now_jalali.weekday()]
        month_names_fa = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
                          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
        month_name = month_names_fa[now_jalali.month - 1]
        time_str = datetime.now().strftime("%H:%M")

        first_message = (
            f"⭕️ به‌روزرسانی کانفیگ‌ها\n"
            f"{weekday_name} {now_jalali.day} {month_name} {now_jalali.year}\n"
            f"ساعت: {time_str}\n"
            f"تعداد جدید: {len(new_configs)} کانفیگ 👇"
        )
        await client.send_message(MY_CHANNEL, first_message)
        print("پیام اول (تعداد جدید) ارسال شد")
        await asyncio.sleep(10)

        chunk_size = 15
        i = 0
        block_number = 1

        while i < len(new_configs):
            chunk = new_configs[i:i + chunk_size]
            message = "```\n" + "\n".join(chunk) + "\n```"

            if len(message) <= 3800:
                await client.send_message(MY_CHANNEL, message)
                print(f"بخش {block_number} ارسال شد (اندازه: {len(chunk)} کانفیگ)")
                await asyncio.sleep(10)
                i += chunk_size
                block_number += 1
            else:
                print(f"بخش {block_number} طولانی است (طول: {len(message)}) → تقسیم به دو قسمت")
                
                half = len(chunk) // 2
                chunk1 = chunk[:half]
                chunk2 = chunk[half:]

                msg1 = "```\n" + "\n".join(chunk1) + "\n```"
                await client.send_message(MY_CHANNEL, msg1)
                print(f"   نیمه اول (اندازه: {len(chunk1)}) ارسال شد")
                await asyncio.sleep(5)

                msg2 = "```\n" + "\n".join(chunk2) + "\n```"
                await client.send_message(MY_CHANNEL, msg2)
                print(f"   نیمه دوم (اندازه: {len(chunk2)}) ارسال شد")
                await asyncio.sleep(10)

                i += chunk_size
                block_number += 1

        print(f"ارسال تمام {len(new_configs)} کانفیگ جدید به {MY_CHANNEL} به پایان رسید")

    except errors.FloodWaitError as e:
        print(f"فلود: باید {e.seconds} ثانیه صبر کنی")
    except Exception as e:
        print(f"خطا در ارسال به کانال: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    try:
        results = asyncio.run(fetch_configs())
        new_ones = save_to_files(results)
        asyncio.run(post_to_channel(new_ones))
    except KeyboardInterrupt:
        print("\nتوسط کاربر متوقف شد.")
    except Exception as e:
        print(f"خطای کلی در اجرای اسکریپت: {e}")
