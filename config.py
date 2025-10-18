# config.py

BOT_TOKEN = ""

FORBIDDEN_WORDS = [
    "so'kinish1",
    "so'kinish2",
    "sokinish3",
    "bla"
]

PUNISHMENT_DURATIONS = {
    1: 600,    # 10 daqiqa
    2: 1800,   # 30 daqiqa
    3: 3600,   # 1 soat
}

MAX_VIOLATIONS = 3

VIOLATION_WINDOW = 3600  # 1 soat ichida buzilishlar hisoblanadi

BLOCKED_MESSAGE_TEMPLATE = (
    "🚫 Siz '{word}' so‘zini ishlatdingiz va {duration} davomida yozish huquqidan mahrum qilingansiz.\n"
    "Bu sizning {count}-chi ogohlantirishingiz."
)

GROUP_NOTIFICATION_TEMPLATE = (
    "⚠️ {user_name} (ID: {user_id}) taqiqlangan so‘z '{word}' ishlatgani uchun "
    "{duration} davomida bloklandi. Bu {count}-chi ogohlantirish."
)

BAN_MESSAGE_TEMPLATE = (
    "🚫 Siz '{word}' so‘zini ishlatdingiz va guruhdan chiqarib yuborildingiz.\n"
    "Bu sizning {count}-chi ogohlantirishingiz edi."
)

BAN_GROUP_NOTIFICATION_TEMPLATE = (
    "🚫 {user_name} (ID: {user_id}) taqiqlangan so‘z '{word}' ishlatgani uchun "
    "guruhdan chiqarib yuborildi. Bu {count}-chi ogohlantirish edi."
)

LOG_DIR = "logs"
LOG_LEVEL = "INFO"
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(message)s"
