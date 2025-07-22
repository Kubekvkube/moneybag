import logging
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

load_dotenv(dotenv_path='pet1.env')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Типы трат и курсы валют к USD
EXPENSE_TYPES = {'fd', 'drnk', 'els', 'med', 'dope', 'trns', 'hom'}
RATES = {'myr': 0.21, 'thb': 0.027, 'vnd': 0.000043}

# Простейшее хранилище в памяти: user_id -> list of expenses
user_expenses = defaultdict(list)

# Структура одной траты
def create_expense(amount, currency, category):
    return {
        "amount": float(amount),
        "currency": currency.lower(),
        "category": category.lower(),
        "timestamp": datetime.utcnow()
    }

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я помогу вести учёт трат. Введите /payment, чтобы записать трату.")

# Команда /payment <category> <amount> <currency>
async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        args = context.args

        if len(args) != 3:
            await update.message.reply_text("Формат: /payment <тип> <сумма> <валюта>")
            return

        category, amount, currency = args
        if category.lower() not in EXPENSE_TYPES:
            await update.message.reply_text("Неизвестный тип траты.")
            return
        if currency.lower() not in RATES:
            await update.message.reply_text("Неизвестная валюта. Допустимы: myr, thb, vnd.")
            return

        expense = create_expense(amount, currency, category)
        user_expenses[user_id].append(expense)

        await update.message.reply_text("Трата записана!")
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("Ошибка при записи траты.")

# Фильтрация трат по периоду
def get_expenses_by_period(user_id, days_back):
    now = datetime.utcnow()
    since = now - timedelta(days=days_back)
    return [e for e in user_expenses[user_id] if e['timestamp'] >= since]

def summarize_expenses(expenses):
    summary = defaultdict(float)
    total_usd = 0
    for e in expenses:
        usd = e['amount'] * RATES[e['currency']]
        summary[e['category']] += usd
        total_usd += usd
    return summary, total_usd

# Команды /payout_day /payout_week /payout_month /payout_all
async def payout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    command = update.message.text.split()[0]
    user_id = update.message.from_user.id

    if command == '/payout_day':
        days = 1
    elif command == '/payout_week':
        days = 7
    elif command == '/payout_month':
        days = 30
    elif command == '/payout_all':
        days = 365
    else:
        await update.message.reply_text("Неизвестная команда.")
        return

    expenses = get_expenses_by_period(user_id, days)
    if not expenses:
        await update.message.reply_text("Нет трат за указанный период.")
        return

    summary, total = summarize_expenses(expenses)
    response = f"💰 Траты за период ({command[8:]}):\n"
    for cat, amt in summary.items():
        response += f"- {cat}: {amt:.2f} USD\n"
    response += f"\nИтого: {total:.2f} USD"

    await update.message.reply_text(response)

# Основной запуск
if __name__ == '__main__':
    import os
    TOKEN = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("payment", payment))
    app.add_handler(CommandHandler("payout_day", payout))
    app.add_handler(CommandHandler("payout_week", payout))
    app.add_handler(CommandHandler("payout_month", payout))
    app.add_handler(CommandHandler("payout_all", payout))

    app.run_polling()

