import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "fa")
