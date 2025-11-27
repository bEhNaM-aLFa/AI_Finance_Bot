import os
import logging
import tempfile

import pandas as pd
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,

from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

)

from finance_analyzer import analyze_finance_from_df
from ocr_reader import df_from_image

# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------
# توکن ربات را اینجا بگذار
# ---------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
# ---------------------------------------------------


# -------------------------------
# /start command handler
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام 👋\n"
        "من یک ربات تحلیل مالی هستم.\n\n"
        "۱) برای تحلیل کامل، فایل Excel خرج‌و‌دخلت را بفرست.\n"
        "   ستون‌های لازم: Date, Description, Amount, Type (Expense / Income)\n\n"
        "۲) یا می‌توانی عکس رسید بانکی/اسکرین‌شات تراکنش را بفرستی تا OCR و تحلیل انجام شود."
    )
    await update.message.reply_text(text)


# -------------------------------
# Handler for receiving Excel file
# -------------------------------
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message or not message.document:
        return

    doc = message.document
    file_name = doc.file_name or ""

    # فقط فایل اکسل را می‌پذیریم
    if not (file_name.endswith(".xlsx") or file_name.endswith(".xls")):
        await message.reply_text("لطفاً فایل Excel ارسال کن (پسوند .xlsx یا .xls).")
        return

    await message.reply_text("فایل دریافت شد ✅ در حال پردازش...")

    try:
        # دانلود فایل در حافظه موقت
        file = await doc.get_file()
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, file_name)
            await file.download_to_drive(file_path)

            # خواندن اکسل
            df = pd.read_excel(file_path)

        # تحلیل داده‌ها
        summary = analyze_finance_from_df(df)

        # ساخت پیام خلاصه برای کاربر
        text_lines = []
        text_lines.append("📊 خلاصه مالی شما (Excel):")
        text_lines.append(f"• مجموع هزینه‌ها: {summary.total_expenses:,.0f}")
        text_lines.append(f"• مجموع درآمدها: {summary.total_income:,.0f}")
        text_lines.append(f"• جریان نقدی خالص: {summary.net_cash_flow:,.0f}")
        text_lines.append(f"• سطح ریسک: {summary.risk_level}")

        text_lines.append("\n📂 تقسیم هزینه‌ها:")
        for cat, amt in summary.category_breakdown.items():
            text_lines.append(f"- {cat}: {amt:,.0f}")

        text_lines.append("\n🔎 نکات کلیدی:")
        for ins in summary.insights:
            text_lines.append(f"- {ins}")

        text_lines.append("\n✅ پیشنهادهای اولیه:")
        for act in summary.actions:
            text_lines.append(f"- {act}")

        await message.reply_text("\n".join(text_lines))

    except Exception:
        logger.exception("Error processing file")
        await message.reply_text(
            "در پردازش فایل خطایی رخ داد. لطفاً مطمئن شو ستون‌ها درست باشند و دوباره امتحان کن."
        )


# -------------------------------
# Handler for receiving photo (receipt / screenshot)
# -------------------------------
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.photo:
        return

    await message.reply_text("عکس دریافت شد ✅ در حال انجام OCR و تحلیل...")

    try:
        # دریافت فایل
        photo = message.photo[-1]
        file = await photo.get_file()

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "receipt.jpg")
            await file.download_to_drive(file_path)

            # پردازش و OCR
            df = df_from_image(file_path)

        if df.empty:
            await message.reply_text(
                "هیچ تراکنشی از روی تصویر پیدا نشد.\n"
                "لطفاً رسید واضح‌تری بفرست یا از فرمت دیگری استفاده کن."
            )

            amt = float(df.iloc[0]["Amount"])
date = df.iloc[0]["Date"]

if amt < 1_000_000:
    await message.reply_text(
        f"📸 رسید شناسایی شد.\n"
        f"- تاریخ: {date}\n"
        f"- مبلغ تشخیص‌داده‌شده: {amt:,.0f} ریال\n\n"
        "لطفاً مبلغ صحیح را به ریال وارد کن (فقط عدد)."
    )
    # این‌جا می‌تونی state نگه داری (مثلاً در context.user_data)
    # تا پیام بعدی کاربر را به عنوان مبلغ صحیح ذخیره کنی و بعدش تحلیل را انجام بدهی.
    return

            return

        # تحلیل مالی
        summary = analyze_finance_from_df(df)

        text = []
        text.append("📊 خلاصه مالی از روی تصویر:")
        text.append(f"- تعداد تراکنش‌ها: {len(df)}")
        text.append(f"- مجموع هزینه‌ها: {summary.total_expenses:,.0f}")
        text.append(f"- سطح ریسک: {summary.risk_level}")

        text.append("\n🔍 تقسیم هزینه‌ها:")
        for cat, amt in summary.category_breakdown.items():
            text.append(f"• {cat}: {amt:,.0f}")

        text.append("\n💡 نکات:")
        for ins in summary.insights:
            text.append(f"• {ins}")

        text.append("\n🛠 پیشنهاد:")
        for act in summary.actions:
            text.append(f"• {act}")

        await message.reply_text("\n".join(text))

    except Exception as e:
        logger.exception("Error processing OCR")
        await message.reply_text(f"خطای OCR: {e}")

# -------------------------------
#Handler for text
# -------------------------------

async def handle_text_transaction(update: Update, context: CallbackContext):
    text = update.message.text

    df = parse_text_transaction(text)

    if df.empty:
        await update.message.reply_text("متوجه نشدم. لطفاً متن تراکنش را واضح‌تر بفرست.")
        return

    summary = analyze_finance_from_df(df)
    await update.message.reply_text(summary.format_for_user())


# -------------------------------
# Unknown message handler
# -------------------------------
async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "برای شروع /start را بفرست.\n"
        "سپس یکی از این کارها را انجام بده:\n"
        "• ارسال فایل Excel خرج‌و‌دخل\n"
        "• یا ارسال عکس رسید بانکی / اسکرین‌شات تراکنش"
    )


# -------------------------------
# Main function
# -------------------------------
def main():
    # بررسی وجود توکن
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("لطفاً توکن ربات را در TELEGRAM_TOKEN قرار بده.")

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.ALL, handle_unknown))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_transaction))

    # اجرا
    application.run_polling()


if __name__ == "__main__":
    main()
