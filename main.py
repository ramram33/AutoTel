import asyncio
import re
import os
import base64
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetHistoryRequest
from telethon import errors
from datetime import datetime, timezone
import jdatetime
from dotenv import load_dotenv

load_dotenv()

# تنظیمات از محیط (Secrets)
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION_STR = os.getenv("SESSION_STR")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MY_CHANNEL = '@V2ray4Free1'

TELEGRAM_CHANNELS = [
    '@arisping', '@PrivateVPNs', '@AzadLinkIran', 
    '@Vpn_m2s', '@amirambitfree', '@FreakConfig', '@makvaslim'
]

CONFIG_PATTERN = re.compile(r'(?:vmess|vless|ss|shadowsocks|trojan|hysteria|hysteria2|hy2)://[^\s<>\"]+')

async def fetch_configs():
    all_configs = set()
    client = TelegramClient(StringSession(SESSION_STR), API_ID, API_HASH)
    
    try:
        await client.start()
        now = datetime.now(timezone.utc)
        time_threshold = now.replace(hour=0, minute=0, second=0, microsecond=0)

        for channel in TELEGRAM_CHANNELS:
            try:
                entity = await client.get_entity(channel)
                messages = await client(GetHistoryRequest(
                    peer=entity, limit=100, offset_id=0, offset_date=None,
                    add_offset=0, max_id=0, min_id=0, hash=0
                ))

                for msg in messages.messages:
                    if msg.date < time_threshold: break
                    if msg.message:
                        found = CONFIG_PATTERN.findall(msg.message)
                        for cfg in found:
                            # تمیزکاری و افزودن تگ (اینجا شخصی‌سازی انجام می‌شود)
                            clean_cfg = re.split(r'\s*#', cfg)[0].strip()
                            all_configs.add(f"{clean_cfg}#@V2ray4Free1")
            except Exception as e:
                print(f"Error in {channel}: {e}")
    finally:
        await client.disconnect()
    return list(all_configs)

def save_and_encode(configs):
    # تغییر: همیشه فایل‌ها رو می‌سازیم تا گیت‌هاب ارور نده
    content = "\n".join(configs) if configs else "no configs found"
    
    with open("telegram_configs.txt", "w", encoding="utf-8") as f:
        f.write(content)
    
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    with open("telegram_configs_base64.txt", "w", encoding="utf-8") as f:
        f.write(encoded)
    return True

async def send_to_channel(configs):
    if not configs: return
    bot = TelegramClient('bot_session', API_ID, API_HASH)
    try:
        await bot.start(bot_token=BOT_TOKEN)
        now_j = jdatetime.datetime.now()
        text = (f"⭕️ به‌روزرسانی کانفیگ‌ها\n"
                f"📅 {now_j.strftime('%Y/%m/%d')} - {now_j.strftime('%H:%M')}\n"
                f"✅ تعداد: {len(configs)} کانفیگ جدید")
        await bot.send_message(MY_CHANNEL, text)
        
        for i in range(0, len(configs), 15):
            chunk = configs[i:i+15]
            msg = "```\n" + "\n".join(chunk) + "\n```"
            await bot.send_message(MY_CHANNEL, msg, parse_mode='markdown')
            await asyncio.sleep(5)
    finally:
        await bot.disconnect()

if __name__ == "__main__":
    configs = asyncio.run(fetch_configs())
    save_and_encode(configs) # تغییر: همیشه اجرا می‌شود
    if configs:
        asyncio.run(send_to_channel(configs))
