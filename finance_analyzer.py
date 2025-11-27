import pandas as pd
from dataclasses import dataclass
from typing import Dict


@dataclass
class FinanceSummary:
    total_expenses: float
    total_income: float
    net_cash_flow: float
    category_breakdown: Dict[str, float]
    essential_ratio: float
    non_essential_ratio: float
    risk_level: str
    insights: list
    actions: list


def categorize_row(description: str) -> str:
    """
    دسته بندی ساده بر اساس متن توضیحات.
    بعداً می‌توانی آن را هوشمندتر کنی.
    """
    text = (description or "").lower()

    if any(k in text for k in ["نان", "رستوران", "خوراک", "کافه", "food", "restaurant", "cafe"]):
        return "Food"
    if any(k in text for k in ["بنزین", "تاکسی", "اسنپ", "مترو", "transport", "taxi", "fuel"]):
        return "Transport"
    if any(k in text for k in ["اجاره", "رهن", "rent", "mortgage"]):
        return "Housing"
    if any(k in text for k in ["بیمه", "بیمارستان", "دارو", "health", "hospital", "medicine"]):
        return "Health"
    if any(k in text for k in ["نت", "اینترنت", "قبض", "آب", "برق", "گاز", "bill"]):
        return "Bills"
    if any(k in text for k in ["سینما", "تفریح", "game", "netflix", "entertainment"]):
        return "Entertainment"

    return "Other"


def analyze_finance_from_df(df: pd.DataFrame) -> FinanceSummary:
    """
    df باید حداقل این ستون‌ها را داشته باشد:
    - Date
    - Description
    - Amount
    - Type  (Expense / Income)
    """

    required_cols = ["Date", "Description", "Amount", "Type"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df = df.copy()
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    # اگر ستون Category نبود، خودش می‌سازد
    if "Category" not in df.columns:
        df["Category"] = df["Description"].apply(categorize_row)

    # تفکیک expense / income
    df["Type"] = df["Type"].astype(str)
    expenses = df[df["Type"].str.lower() == "expense"]
    income = df[df["Type"].str.lower() == "income"]

    total_expenses = expenses["Amount"].sum()
    total_income = income["Amount"].sum()
    net_cash_flow = total_income - total_expenses

    category_breakdown = (
        expenses.groupby("Category")["Amount"].sum().to_dict()
        if not expenses.empty
        else {}
    )

    essential_categories = {"Food", "Housing", "Bills", "Health"}
    essential_expense = sum(
        amt for cat, amt in category_breakdown.items() if cat in essential_categories
    )
    non_essential_expense = total_expenses - essential_expense

    essential_ratio = (essential_expense / total_expenses) if total_expenses else 0
    non_essential_ratio = (non_essential_expense / total_expenses) if total_expenses else 0

    # محاسبه سطح ریسک ساده
    if total_income <= 0:
        risk_level = "High"
    else:
        saving_rate = (net_cash_flow / total_income) if total_income else 0
        if saving_rate >= 0.2:
            risk_level = "Low"
        elif saving_rate >= 0.05:
            risk_level = "Medium"
        else:
            risk_level = "High"

    insights = []
    if total_expenses > total_income:
        insights.append("You are spending more than your income this period.")
    if non_essential_ratio > 0.3:
        insights.append("Non-essential spending is relatively high.")
    if not insights:
        insights.append("Your spending pattern is relatively balanced.")

    actions = []
    if non_essential_ratio > 0.3:
        actions.append("Set a monthly cap for non-essential categories (e.g., entertainment).")
    if risk_level == "High":
        actions.append("Aim to increase your saving rate to at least 10% of your income.")
    if not actions:
        actions.append("Keep tracking your expenses monthly to maintain this balance.")

    return FinanceSummary(
        total_expenses=total_expenses,
        total_income=total_income,
        net_cash_flow=net_cash_flow,
        category_breakdown=category_breakdown,
        essential_ratio=essential_ratio,
        non_essential_ratio=non_essential_ratio,
        risk_level=risk_level,
        insights=insights,
        actions=actions,
    )
