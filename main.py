import os
import asyncio
import logging
import time
import re
from datetime import datetime, timedelta
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ChatType
from aiogram.types import Message, ChatPermissions

from config import (
    BOT_TOKEN,
    FORBIDDEN_WORDS,
    PUNISHMENT_DURATIONS,
    MAX_VIOLATIONS,
    VIOLATION_WINDOW,
    BLOCKED_MESSAGE_TEMPLATE,
    GROUP_NOTIFICATION_TEMPLATE,
    BAN_MESSAGE_TEMPLATE,
    BAN_GROUP_NOTIFICATION_TEMPLATE,
    LOG_DIR,
    LOG_LEVEL,
    LOG_FORMAT,
)

# === LOGGING ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR_PATH = os.path.join(BASE_DIR, LOG_DIR)
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
LOG_FILE = f"bot_{current_time}.log"
LOG_FILE_PATH = os.path.join(LOG_DIR_PATH, LOG_FILE)

try:
    os.makedirs(LOG_DIR_PATH, exist_ok=True)
    with open(LOG_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write("")
    print(f"Log fayl yo‘li: {LOG_FILE_PATH}")
except Exception as e:
    print(f"Log papkasini yaratishda xato: {e}")
    raise

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("Logging ishga tushdi. Log fayl: %s", LOG_FILE_PATH)

# === BOT VA DISPATCHER ===
if not BOT_TOKEN:
    logger.error("BOT_TOKEN topilmadi!")
    raise ValueError("BOT_TOKEN topilmadi! config.py faylga kiriting.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} sekund"
    elif seconds < 3600:
        return f"{seconds // 60} daqiqa"
    else:
        return f"{seconds // 3600} soat"


class ModerationBot:
    def __init__(self):
        self.forbidden_words = [w.lower() for w in FORBIDDEN_WORDS]
        self.user_violations = defaultdict(list)
        self.admin_notifications = {}

    def clean_old_violations(self, user_id: int):
        now = time.time()
        self.user_violations[user_id] = [
            t for t in self.user_violations[user_id] if now - t < VIOLATION_WINDOW
        ]

    def add_violation(self, user_id: int) -> int:
        self.user_violations[user_id].append(time.time())
        self.clean_old_violations(user_id)
        return len(self.user_violations[user_id])

    def get_punishment_duration(self, count: int) -> int:
        return PUNISHMENT_DURATIONS.get(
            count, PUNISHMENT_DURATIONS[max(PUNISHMENT_DURATIONS.keys())]
        )

    def contains_forbidden_word(self, text: str) -> tuple[bool, str | None]:
        if not text:
            return False, None
        txt = text.lower()
        for w in self.forbidden_words:
            pattern = r'\b' + re.escape(w) + r'\b'
            if re.search(pattern, txt):
                return True, w
        return False, None

    async def restrict_user(self, chat_id: int, user_id: int, duration: int) -> bool:
        try:
            until_date = datetime.now() + timedelta(seconds=duration)
            await bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            return True
        except Exception as e:
            logger.error(f"Restrict xatoligi: {e}")
            return False

    async def ban_user(self, chat_id: int, user_id: int) -> bool:
        try:
            await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            return True
        except Exception as e:
            logger.error(f"Ban xatoligi: {e}")
            return False

    async def send_private_warning(self, user_id: int, word: str, duration: int, count: int):
        try:
            msg = BLOCKED_MESSAGE_TEMPLATE.format(
                word=word, duration=format_duration(duration), count=count
            )
            await bot.send_message(user_id, msg)
        except Exception:
            pass

    async def send_private_ban_warning(self, user_id: int, word: str, count: int):
        try:
            msg = BAN_MESSAGE_TEMPLATE.format(word=word, count=count)
            await bot.send_message(user_id, msg)
        except Exception:
            pass

    async def send_group_notification(self, chat_id: int, user_id: int, user_name: str, word: str, duration: int, count: int):
        try:
            msg = GROUP_NOTIFICATION_TEMPLATE.format(
                user_name=user_name, user_id=user_id,
                word=word, duration=format_duration(duration), count=count
            )
            sent = await bot.send_message(chat_id, msg)
            self.admin_notifications[user_id] = {
                'chat_id': chat_id,
                'message_id': sent.message_id,
                'duration': duration
            }
            asyncio.create_task(self.delete_group_notification(user_id))
        except Exception:
            pass

    async def send_group_ban_notification(self, chat_id: int, user_id: int, user_name: str, word: str, count: int):
        try:
            msg = BAN_GROUP_NOTIFICATION_TEMPLATE.format(
                user_name=user_name, user_id=user_id,
                word=word, count=count
            )
            await bot.send_message(chat_id, msg)
        except Exception:
            pass

    async def delete_group_notification(self, user_id: int):
        try:
            data = self.admin_notifications.get(user_id)
            if data:
                await asyncio.sleep(data['duration'])
                await bot.delete_message(chat_id=data['chat_id'], message_id=data['message_id'])
                del self.admin_notifications[user_id]
        except Exception:
            pass


moderation = ModerationBot()


@dp.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def on_group_message(message: Message):
    if not message.text or not message.from_user:
        return

    user = message.from_user
    user_id = user.id
    user_name = f"@{user.username}" if user.username else user.full_name or str(user_id)
    chat_id = message.chat.id

    logger.info(f"[Guruh] {user_id} ({user_name}): {message.text}")

    found, word = moderation.contains_forbidden_word(message.text)
    if not found:
        return

    try:
        await message.delete()
    except Exception:
        pass

    count = moderation.add_violation(user_id)

    if count >= MAX_VIOLATIONS:
        if await moderation.ban_user(chat_id, user_id):
            await moderation.send_private_ban_warning(user_id, word, count)
            await moderation.send_group_ban_notification(chat_id, user_id, user_name, word, count)
    else:
        duration = moderation.get_punishment_duration(count)
        if await moderation.restrict_user(chat_id, user_id, duration):
            await moderation.send_private_warning(user_id, word, duration, count)
            await moderation.send_group_notification(chat_id, user_id, user_name, word, duration, count)


async def main():
    logger.info("Bot ishga tushmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Bot to‘xtatildi.")