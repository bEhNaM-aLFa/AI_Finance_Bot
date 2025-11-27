import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "fa")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not set in .env")
