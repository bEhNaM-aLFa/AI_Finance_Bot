import logging
import os
import tempfile

import pandas as pd
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_TOKEN, DEFAULT_LANG
from finance_analyzer import analyze_finance_from_df
from ocr_reader import df_from_image
from text_parser import parse_text_transaction

# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SUPPORTED_LANGS = ["fa", "en"]

MESSAGES = {
    "start_intro": {
        "fa": "سلام 👋\nلطفاً زبان مورد نظر را انتخاب کن:",
        "en": "Hi 👋\nPlease choose your language:",
    },
    "help_main": {
        "fa": (
            "✅ زبان: فارسی\n\n"
            "۱) فایل Excel خرج و دخل را بفرست.\n"
            "۲) یا عکس رسید بانکی را بفرست.\n"
            "۳) یا متن تراکنش را به صورت تکست ارسال کن.\n\n"
            "مثال متن تراکنش:\n"
            "1402/06/15 - 3,260,000 - خرید مواد اولیه"
        ),
        "en": (
            "✅ Language: English\n\n"
            "1) Send an Excel file with your transactions.\n"
            "2) Or send a receipt image.\n"
            "3) Or send a transaction as plain text.\n\n"
            "Example text transaction:\n"
            "2023-09-06 - 3,260,000 - Groceries"
        ),
    },
    "file_received": {
        "fa": "فایل دریافت شد ✅ در حال پردازش...",
        "en": "File received ✅ Processing...",
    },
    "photo_received": {
        "fa": "عکس دریافت شد ✅ در حال انجام OCR و تحلیل...",
        "en": "Photo received ✅ Running OCR and analysis...",
    },
    "no_transactions_from_image": {
        "fa": "هیچ تراکنشی از روی تصویر پیدا نشد (یا مبلغ خیلی کوچک تشخیص داده شد).",
        "en": "No transactions could be extracted from the image (or amount too small).",
    },
    "text_parse_failed": {
        "fa": "متوجه نشدم. لطفاً متن تراکنش را واضح‌تر و با تاریخ و مبلغ بفرست.\n"
              "مثال: 1402/06/15 - 3,260,000 - خرید مواد اولیه",
        "en": "Could not understand. Please send a clearer text with date and amount.\n"
              "Example: 2023-09-06 - 3,260,000 - Groceries",
    },
    "error_file": {
        "fa": "در پردازش فایل خطایی رخ داد.",
        "en": "An error occurred while processing the file.",
    },
    "error_photo": {
        "fa": "در پردازش تصویر خطایی رخ داد (OCR).",
        "en": "An error occurred while processing the image (OCR).",
    },
    "unknown": {
        "fa": "برای شروع /start را بفرست و زبان را انتخاب کن.",
        "en": "Send /start and choose your language first.",
    },
}


def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = context.user_data.get("lang")
    if lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def t(key: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    lang = get_lang(context)
    return MESSAGES.get(key, {}).get(lang, "")


# -------------------------------
# Formatting helper
# -------------------------------
def format_summary(summary, lang: str, source: str) -> str:
    """
    source: 'Excel', 'Image', 'Text'
    """
    if lang == "fa":
        title_map = {
            "Excel": "📊 خلاصه مالی شما (Excel):",
            "Image": "📊 خلاصه مالی از روی تصویر:",
            "Text": "📊 خلاصه مالی از روی متن:",
        }
        lines = [
            title_map.get(source, "📊 خلاصه مالی:"),
            f"• مجموع هزینه‌ها: {summary.total_expenses:,.0f}",
            f"• مجموع درآمدها: {summary.total_income:,.0f}",
            f"• جریان نقدی خالص: {summary.net_cash_flow:,.0f}",
            f"• سطح ریسک: {summary.risk_level}",
            "",
            "📂 تقسیم هزینه‌ها:",
        ]
        for cat, amt in summary.category_breakdown.items():
            lines.append(f"- {cat}: {amt:,.0f}")

        lines.append("\n🔎 نکات کلیدی:")
        for ins in summary.insights:
            lines.append(f"- {ins}")

        lines.append("\n✅ پیشنهادها:")
        for act in summary.actions:
            lines.append(f"- {act}")

        return "\n".join(lines)

    else:
        title_map = {
            "Excel": "📊 Your finance summary (Excel):",
            "Image": "📊 Finance summary from image:",
            "Text": "📊 Finance summary from text:",
        }
        lines = [
            title_map.get(source, "📊 Finance summary:"),
            f"• Total expenses: {summary.total_expenses:,.0f}",
            f"• Total income: {summary.total_income:,.0f}",
            f"• Net cash flow: {summary.net_cash_flow:,.0f}",
            f"• Risk level: {summary.risk_level}",
            "",
            "📂 Expense breakdown:",
        ]
        for cat, amt in summary.category_breakdown.items():
            lines.append(f"- {cat}: {amt:,.0f}")

        lines.append("\n🔎 Insights:")
        for ins in summary.insights:
            lines.append(f"- {ins}")

        lines.append("\n✅ Actions:")
        for act in summary.actions:
            lines.append(f"- {act}")

        return "\n".join(lines)


# -------------------------------
# /start command handler
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Received /start")
    keyboard = [
        [
            InlineKeyboardButton("فارسی 🇮🇷", callback_data="lang_fa"),
            InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        MESSAGES["start_intro"]["fa"],
        reply_markup=reply_markup,
    )


# -------------------------------
# Language selection callback
# -------------------------------
async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Language callback: {data}")

    if data == "lang_fa":
        context.user_data["lang"] = "fa"
    elif data == "lang_en":
        context.user_data["lang"] = "en"

    lang = get_lang(context)
    await query.edit_message_text(MESSAGES["help_main"][lang])


# -------------------------------
# Handler for receiving Excel file
# -------------------------------
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.document:
        return

    logger.info("handle_document triggered")

    doc = message.document
    file_name = doc.file_name or ""
    lang = get_lang(context)

    if not (file_name.endswith(".xlsx") or file_name.endswith(".xls")):
        if lang == "fa":
            await message.reply_text("لطفاً فایل Excel ارسال کن (پسوند .xlsx یا .xls).")
        else:
            await message.reply_text("Please send an Excel file (.xlsx or .xls).")
        return

    await message.reply_text(t("file_received", context))

    try:
        file = await doc.get_file()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, file_name)
            await file.download_to_drive(file_path)

            df = pd.read_excel(file_path)

        summary = analyze_finance_from_df(df)
        text = format_summary(summary, lang, source="Excel")
        await message.reply_text(text)

    except Exception:
        logger.exception("Error processing file")
        await message.reply_text(t("error_file", context))


# -------------------------------
# Handler for receiving photo (receipt / screenshot)
# -------------------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.photo:
        return

    logger.info("handle_photo triggered")

    await message.reply_text(t("photo_received", context))

    lang = get_lang(context)

    try:
        photo = message.photo[-1]
        file = await photo.get_file()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "receipt.jpg")
            await file.download_to_drive(file_path)

            logger.info(f"Saved photo to {file_path}, calling df_from_image...")
            df = df_from_image(file_path)
            logger.info(f"OCR DataFrame:\n{df}")

        if df.empty:
            await message.reply_text(t("no_transactions_from_image", context))
            return

        summary = analyze_finance_from_df(df)
        text = format_summary(summary, lang, source="Image")
        await message.reply_text(text)

    except Exception:
        logger.exception("Error processing OCR")
        await message.reply_text(t("error_photo", context))


# -------------------------------
# Handler for text-based transactions
# -------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    logger.info("handle_text triggered")

    lang = get_lang(context)
    text_input = message.text.strip()
    logger.info(f"Text input: {text_input}")

    df = parse_text_transaction(text_input)
    logger.info(f"Parsed text DF:\n{df}")

    if df.empty:
        await message.reply_text(t("text_parse_failed", context))
        return

    summary = analyze_finance_from_df(df)
    out = format_summary(summary, lang, source="Text")
    await message.reply_text(out)


# -------------------------------
# Unknown message handler
# -------------------------------
async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("handle_unknown triggered")
    await update.message.reply_text(t("unknown", context))


# -------------------------------
# Main function
# -------------------------------
def main():
    if not TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN is not configured.")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Command + language selection
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))

    # Documents (Excel)
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Photos (receipts)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Text (manual transaction)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )

    # Fallback
    application.add_handler(MessageHandler(filters.ALL, handle_unknown))

    application.run_polling()


if __name__ == "__main__":
    main()
