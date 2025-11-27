import re
import pandas as pd

def normalize_digits_fa_en(text: str) -> str:
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    latin_digits = "0123456789"
    return text.translate(str.maketrans(persian_digits, latin_digits))

DATE_PATTERNS = [
    r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})",  # 1402/06/15
    r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",  # 06/15/1402
]

AMOUNT_PATTERN = r"([\d,٬]+)"

EXPENSE_KEYWORDS = ["برداشت", "خرید", "هزینه", "پرداخت"]
INCOME_KEYWORDS = ["واریز", "دریافت", "فروش", "درآمد"]

def parse_text_transaction(text: str) -> pd.DataFrame:
    text = normalize_digits_fa_en(text)
    text = text.replace("ريال", "ریال").replace("Rial", "ریال")

    # 1) تاریخ
    date_val = None
    for pat in DATE_PATTERNS:
        m = re.search(pat, text)
        if m:
            raw_date = m.group(1)
            try:
                date_val = pd.to_datetime(raw_date, dayfirst=True)
            except:
                pass
            break

    # 2) مبلغ
    m_amt = re.search(AMOUNT_PATTERN, text)
    amount_val = None
    if m_amt:
        clean = m_amt.group(1).replace(",", "").replace("٬", "")
        try:
            amount_val = float(clean)
        except:
            pass

    # 3) نوع تراکنش
    tx_type = "Expense"
    for w in INCOME_KEYWORDS:
        if w in text:
            tx_type = "Income"
            break
    for w in EXPENSE_KEYWORDS:
        if w in text:
            tx_type = "Expense"
            break

    # 4) توضیح  
    description = text.strip()

    # 5) اگر هیچ‌چیز پیدا نشد
    if not date_val or not amount_val:
        return pd.DataFrame(columns=["Date", "Description", "Amount", "Type"])

    return pd.DataFrame([{
        "Date": date_val,
        "Description": description,
        "Amount": amount_val,
        "Type": tx_type,
    }])
