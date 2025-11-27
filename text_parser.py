import re
import pandas as pd


def normalize_digits_fa_en(text: str) -> str:
    """تبدیل ارقام فارسی به انگلیسی."""
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    latin_digits = "0123456789"
    return text.translate(str.maketrans(persian_digits, latin_digits))


# الگوهای مختلف تاریخ
DATE_PATTERNS = [
    r"(\d{4}[./-]\d{1,2}[./-]\d{1,2})",  # 1402/06/15 یا 1402-06-15
    r"(\d{1,2}[./-]\d{1,2}[./-]\d{4})",  # 06/15/1402
]

# هر عدد با کاما/٬‌
AMOUNT_PATTERN = r"([\d,٬]+)"

EXPENSE_KEYWORDS = ["برداشت", "خرید", "هزینه", "پرداخت", "withdraw", "purchase", "expense"]
INCOME_KEYWORDS = ["واریز", "دریافت", "فروش", "درآمد", "deposit", "income", "salary"]


def parse_text_transaction(text: str) -> pd.DataFrame:
    """
    متن آزاد تراکنش را تحلیل می‌کند و یک DataFrame با ستون‌های
    Date, Description, Amount, Type
    برمی‌گرداند.

    استراتژی:
      - ارقام فارسی → انگلیسی
      - پیدا کردن تاریخ، اگر نشد: تاریخ = امروز
      - پیدا کردن همه اعداد، حذف شماره‌حساب‌های خیلی بلند، انتخاب بزرگ‌ترین عدد به‌عنوان مبلغ
      - نوع تراکنش از روی کلمات کلیدی
    """
    text = normalize_digits_fa_en(text)
    text = text.replace("ريال", "ریال").replace("Rial", "ریال")

    # ---------------- 1) تاریخ ----------------
    date_val = None
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            raw_date = m.group(1)
            try:
                # dayfirst=True تا 15/06/1402 هم درست بخواند
                date_val = pd.to_datetime(raw_date, dayfirst=True)
            except Exception:
                pass
            if date_val is not None:
                break

    # اگر تاریخ پیدا نشد، فرض = امروز
    if date_val is None:
        date_val = pd.Timestamp.today().normalize()

    # ---------------- 2) مبلغ ----------------
    numbers = re.findall(AMOUNT_PATTERN, text)
    amount_val = None

    candidates = []
    for tok in numbers:
        clean = tok.replace(",", "").replace("٬", "")
        if not clean:
            continue

        # حذف شماره حساب/کارت/شباهای خیلی بلند
        if len(clean) >= 14:
            continue

        try:
            val = float(clean)
        except Exception:
            continue

        if val <= 0:
            continue

        candidates.append(val)

    if candidates:
        # بزرگ‌ترین عدد را به‌عنوان مبلغ می‌گیریم
        amount_val = max(candidates)

    # اگر هیچ عدد معقولی پیدا نشد → DF خالی
    if amount_val is None:
        return pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])

    # ---------------- 3) نوع تراکنش ----------------
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

    # ---------------- 4) توضیح ----------------
    description = text.strip()

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
