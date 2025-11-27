import re
from typing import List, Optional

import pandas as pd
from PIL import Image, ImageOps
import pytesseract

# -------------------------------------------------------------------
# تنظیم مسیر نصب Tesseract در ویندوز (در صورت نیاز مسیر را اصلاح کن)
# -------------------------------------------------------------------
# مثال رایج:
# C:\Program Files\Tesseract-OCR\tesseract.exe
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------------------------------------------------------------
# ابزارهای کمکی ارقام فارسی → انگلیسی
# -------------------------------------------------------------------
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
LATIN_DIGITS = "0123456789"
TRANS_TABLE = str.maketrans(PERSIAN_DIGITS, LATIN_DIGITS)


def normalize_digits(text: str) -> str:
    """تبدیل ارقام فارسی به انگلیسی."""
    if not text:
        return ""
    return text.translate(TRANS_TABLE)


# -------------------------------------------------------------------
# OCR روی تصویر
# -------------------------------------------------------------------
def image_to_text(image_path: str) -> str:
    """
    خواندن تصویر و انجام OCR:
      - تبدیل به grayscale
      - بزرگ‌نمایی
      - autocontrast
      - استفاده از زبان فارسی + انگلیسی
    """
    img = Image.open(image_path)

    # 1) تبدیل به سطح خاکستری
    img = img.convert("L")

    # 2) بزرگ‌تر کردن تصویر برای بهبود OCR
    scale = 2
    img = img.resize((img.width * scale, img.height * scale))

    # 3) افزایش کنتراست خودکار
    img = ImageOps.autocontrast(img)

    # 4) OCR
    text = pytesseract.image_to_string(
        img,
        lang="fas+eng",
        config="--psm 6",  # مناسب برای بلاک متن
    )

    text = normalize_digits(text)
    return text


# -------------------------------------------------------------------
# مپ ماه‌های فارسی
# -------------------------------------------------------------------
MONTH_MAP = {
    "فروردین": 1,
    "اردیبهشت": 2,
    "خرداد": 3,
    "تیر": 4,
    "مرداد": 5,
    "شهریور": 6,
    "مهر": 7,
    "آبان": 8,
    "آذر": 9,
    "دی": 10,
    "بهمن": 11,
    "اسفند": 12,
}


# -------------------------------------------------------------------
# توابع کمکی برای استخراج مبلغ
# -------------------------------------------------------------------
def extract_best_amount(full: str) -> Optional[float]:
    """
    از کل متن، عددهای ممکن را پیدا می‌کند،
    شماره حساب/شباهای خیلی بلند را حذف می‌کند،
    و بزرگ‌ترین عدد منطقی را برمی‌گرداند.
    """
    tokens = re.findall(r"([\d٬,]+)", full)
    candidates = []

    for tok in tokens:
        clean = tok.replace(",", "").replace("٬", "")
        if not clean:
            continue

        # حذف شماره حساب / شباهای خیلی بلند (مثلاً 14 رقم به بالا)
        if len(clean) >= 14:
            continue

        try:
            val = float(clean)
        except ValueError:
            continue

        if val <= 0:
            continue

        candidates.append(val)

    if not candidates:
        return None

    return max(candidates)


def extract_amount_from_labels(full: str) -> Optional[float]:
    """
    تلاش می‌کند مبلغ را مشخصاً از کنار لیبل‌هایی مثل:
      - مبلغ انتقال
      - مبلغ تراکنش
      - مبلغ پایا
      - مبلغ
    استخراج کند.
    اگر پیدا نشد، به extract_best_amount برمی‌گردد.
    """
    full_norm = full

    labels = [
        "مبلغ انتقال",
        "مبلغ تراکنش",
        "مبلغ پايا",
        "مبلغ پایا",
        "مبلغ",
    ]
for label in labels:
    m = re.search(fr"{label}[^\d]*([\d\s٬,]+)", full_norm)
    if not m:
        continue

    raw = m.group(1)

    # نسخه بدون فاصله برای تشخیص الگوی خراب‌شده
    raw_no_space = raw.replace(" ", "")

    # هک: اگر مثل "76,0" باشد، یعنی احتمال زیاد "76,000" بوده
    if "," in raw_no_space and raw_no_space.endswith(",0"):
        base = raw_no_space[:-2]  # حذف ",0"
        base_clean = base.replace(",", "").replace("٬", "")
        if base_clean.isdigit():
            try:
                return float(base_clean) * 1000
            except ValueError:
                pass  # اگر نشد، می‌رویم سراغ منطق عادی

    # منطق عادی
    clean = raw.replace(" ", "").replace(",", "").replace("٬", "")
    if not clean:
        continue

    # حذف رشته‌های خیلی بلند (شبیه شبا)
    if len(clean) >= 14:
        continue

    try:
        return float(clean)
    except ValueError:
        continue

# -------------------------------------------------------------------
# تبدیل متن OCR شده به ردیف‌های تراکنش
# -------------------------------------------------------------------
def parse_ocr_text_to_rows(text: str) -> List[dict]:
    """
    1) پاس اول: خطوطی که تاریخ عددی (مثلاً 1400/06/08) و مبلغ دارند → ردیف تراکنش.
    2) پاس دوم: رسید بانکی فارسی:
       - تاریخ به فرم «7 شهریور ماه سال 1400»
       - مبلغ از کنار لیبل «مبلغ انتقال» و مشابه، یا بزرگ‌ترین عدد منطقی متن.
    """
    rows: List[dict] = []

    # ---------- پاس ۱: الگوی عمومی (تاریخ عددی در خطوط) ----------
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    date_pattern = re.compile(r"(\d{2,4}[-/\.]\d{1,2}[-/\.]\d{1,2})")
    amount_pattern = re.compile(r"([\d٬,]+(?:\.\d+)?)")

    for line in lines:
        line_norm = normalize_digits(line)

        date_match = date_pattern.search(line_norm)
        amounts = amount_pattern.findall(line_norm)

        if not date_match or not amounts:
            continue

        date_str = date_match.group(1)
        amount_str = amounts[-1]

        try:
            date_val = pd.to_datetime(date_str, dayfirst=True, errors="raise")
        except Exception:
            continue

        amount_clean = amount_str.replace(",", "").replace("٬", "")
        try:
            amount_val = float(amount_clean)
        except ValueError:
            continue

        desc = (
            line_norm.replace(date_str, "")
            .replace(amount_str, "")
            .strip(" -:/")
        )

        if not desc:
            desc = "Transaction"

        rows.append(
            {
                "Date": date_val,
                "Description": desc,
                "Amount": amount_val,
                "Type": "Expense",
            }
        )

    if rows:
        return rows

    # ---------- پاس ۲: رسید بانکی فارسی روی متن کامل ----------
    full = normalize_digits(text)

    # تاریخ: «7 شهریور ماه سال 1400»
    m_date = re.search(r"(\d{1,2})\s+(\S+)\s+ماه\s+سال\s+(\d{4})", full)
    date_str = None
    if m_date:
        day = int(m_date.group(1))
        month_name = m_date.group(2).replace("‌", "")  # حذف نیم‌فاصله احتمالی
        year = int(m_date.group(3))
        month = MONTH_MAP.get(month_name, 1)
        date_str = f"{year:04d}-{month:02d}-{day:02d}"

    # مبلغ: ابتدا از کنار لیبل‌ها، اگر نشد، بزرگ‌ترین عدد منطقی
    amount_val = extract_amount_from_labels(full)

    if date_str and amount_val is not None:
        rows.append(
            {
                "Date": date_str,              # تاریخ شمسی به‌صورت رشته
                "Description": "رسید بانکی",
                "Amount": amount_val,
                "Type": "Expense",
            }
        )

    return rows


# -------------------------------------------------------------------
# رابط اصلی برای بات: از تصویر → DataFrame
# -------------------------------------------------------------------
def df_from_image(image_path: str) -> pd.DataFrame:
    """
    تصویر را OCR می‌کند و DataFrame استاندارد با ستون‌های:
    Date, Description, Amount, Type
    برمی‌گرداند.
    """
    text = image_to_text(image_path)
    rows = parse_ocr_text_to_rows(text)

    if not rows:
        return pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])

    df = pd.DataFrame(rows)
    return df
