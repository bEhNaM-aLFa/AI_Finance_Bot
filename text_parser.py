import re
import pandas as pd


def normalize_digits_fa_en(text: str) -> str:
    """تبدیل ارقام فارسی به انگلیسی (برای هم‌خوانی با regex و pandas)."""
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    latin_digits = "0123456789"
    return text.translate(str.maketrans(persian_digits, latin_digits))


# الگوهای مختلف تاریخ
DATE_PATTERNS = [
    r"(\d{4}[./-]\d{1,2}[./-]\d{1,2})",  # 1402/06/15 یا 1402-06-15
    r"(\d{1,2}[./-]\d{1,2}[./-]\d{4})",  # 06/15/1402
]

# کلمات کلیدی نوع تراکنش
EXPENSE_KEYWORDS = ["برداشت", "خرید", "هزینه", "پرداخت", "withdraw", "purchase", "expense"]
INCOME_KEYWORDS = ["واریز", "دریافت", "فروش", "درآمد", "deposit", "income", "salary"]


def parse_text_transaction(text: str) -> pd.DataFrame:
    """
    متن آزاد تراکنش را تحلیل می‌کند و یک DataFrame با ستون‌های:
      Date, Description, Amount, Type
    برمی‌گرداند.

    منطق:
      - هر عددی در متن باشد → سعی می‌کنیم بزرگ‌ترین عدد را مبلغ بگیریم.
      - اگر تاریخ پیدا نشد → تاریخ = امروز.
      - اگر هیچ عددی نبود → DF خالی.
    """
    if not text or not text.strip():
        return pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])

    # 1) نرمال‌سازی ارقام
    text = normalize_digits_fa_en(text)
    text = text.replace("ريال", "ریال").replace("Rial", "ریال")

    # 2) استخراج همه اعداد (با کاما یا جداکننده‌های هزار)
    number_tokens = re.findall(r"[\d,٬]+", text)
    candidates = []

    for tok in number_tokens:
        clean = tok.replace(",", "").replace("٬", "")
        if not clean:
            continue
        try:
            val = float(clean)
        except Exception:
            continue
        if val <= 0:
            continue
        candidates.append(val)

    # اگر هیچ عددی پیدا نشد → نمی‌توانیم تراکنش بسازیم
    if not candidates:
        return pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])

    # بزرگ‌ترین عدد را مبلغ می‌گیریم
    amount_val = max(candidates)

    # 3) تاریخ: تلاش برای پیدا کردن تاریخ، اگر نشد → امروز
    date_val = None
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            raw_date = m.group(1)
            try:
                date_val = pd.to_datetime(raw_date, dayfirst=True)
                break
            except Exception:
                continue

    if date_val is None:
        # اگر تاریخ پیدا نشد، تاریخ امروز (بدون زمان)
        date_val = pd.Timestamp.today().normalize()

    # 4) نوع تراکنش (Expense / Income)
    tx_type = "Expense"
    text_lower = text.lower()

    for w in INCOME_KEYWORDS:
        if w in text_lower:
            tx_type = "Income"
            break

    for w in EXPENSE_KEYWORDS:
        if w in text_lower:
            tx_type = "Expense"
            break

    # 5) توضیح
    description = text.strip()

    # 6) ساخت DataFrame
    return pd.DataFrame(
        [
            {
                "Date": date_val,
                "Description": description,
                "Amount": amount_val,
                "Type": tx_type,
            }
        ]
    )
