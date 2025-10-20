import html
from collections import deque
import asyncio
from telegram import Bot
from telegram.constants import ParseMode
import config

def truncate_text_utf8(l_text: str, max_bytes: int) -> str:
    encoded = l_text.encode('utf-8')
    if len(encoded) <= max_bytes:
        return l_text

    truncated = encoded[:max_bytes]
    while True:
        try:
            return truncated.decode('utf-8')
        except UnicodeDecodeError:
            truncated = truncated[:-1]

def tail_log_for_telegram(filename, n=10):
    l_log = ''
    with open(filename) as f:
        for line in deque(f, n):
            line = html.escape(line, quote=True)
            if len(line.split(' ')) < 3 or line.split(' ')[2] == 'ERROR':
                l_log += '<b>{}</b>'.format(line)
            else:
                l_log += line
    return l_log


async def send_async(text):
    bot = Bot(token=config.telegram_api_key)
    await bot.send_message(chat_id=config.telegram_chat_id, text=text,
                           disable_web_page_preview=True,
                           parse_mode = ParseMode.HTML)

def send_by_telegram(text):
    asyncio.run(send_async(text))