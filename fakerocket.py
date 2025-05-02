import asyncio
import sqlite3
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# === Настройки ===
BOT_TOKEN = '7510261387:AAHv8dULHPU4gu-5Utmm2cFOqbheNtD2W3E'
ADMIN_ID = 1799193124
CHANNEL_USERNAME = 'xrocketnewsru'

# Фиксированные курсы валют (рубли)
CURRENCY_RATES = {
    'USDT': 82.0,
    'TON': 273.0,
    'XROCK': 1.0,  # Примерный курс, можно изменить
    'USDC': 82.0,
    'ETH': 180000.0,  # Примерный курс
    'TRX': 8.5,      # Примерный курс
    'BNB': 30000.0,  # Примерный курс
    'SOL': 15000.0,  # Примерный курс
    'BTC': 4000000.0 # Примерный курс
}

CURRENCIES = list(CURRENCY_RATES.keys())

# Инициализация БД
def init_db():
    conn = sqlite3.connect('xrocket.db')
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if not columns:
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            usdt REAL DEFAULT 0,
            ton REAL DEFAULT 0,
            xrock REAL DEFAULT 0,
            usdc REAL DEFAULT 0,
            eth REAL DEFAULT 0,
            trx REAL DEFAULT 0,
            bnb REAL DEFAULT 0,
            sol REAL DEFAULT 0,
            btc REAL DEFAULT 0,
            subscribed BOOLEAN DEFAULT FALSE
        )
        ''')
    else:
        if 'subscribed' not in columns:
            cursor.execute('ALTER TABLE users ADD COLUMN subscribed BOOLEAN DEFAULT FALSE')
    
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# --- Вспомогательные функции ---

def create_main_menu():
    buttons = [
        [InlineKeyboardButton(text="📱 Открыть приложение", url="https://t.me/xrocket/app?startapp=wallet")],
        [
            InlineKeyboardButton(text="💵 Мой кошелёк", callback_data="my_wallet"),
            InlineKeyboardButton(text="📤 Пополнить", callback_data="deposit")
        ],
        [
            InlineKeyboardButton(text="📤 Отправить", callback_data="withdraw"),
            InlineKeyboardButton(text="🏷️ Чеки", callback_data="checks")
        ],
        [
            InlineKeyboardButton(text="💱 Биржа", url="https://t.me/xrocket/app?startapp=exchange"),
            InlineKeyboardButton(text="🤖 API", callback_data="api_info")
        ],
        [InlineKeyboardButton(text="🛒 P2P Маркет", callback_data="p2p_market")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_currency_menu(action, back_to="back_to_menu"):
    buttons = []
    for i in range(0, len(CURRENCIES), 2):
        row = CURRENCIES[i:i+2]
        buttons.append([
            InlineKeyboardButton(text=currency, callback_data=f"{action}_{currency}")
            for currency in row
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=back_to)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- Хендлеры ---

@dp.message(Command("start"))
async def start(message: types.Message):
    cursor.execute("SELECT id, subscribed FROM users WHERE id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT INTO users (id, subscribed) VALUES (?, ?)", (message.from_user.id, False))
        conn.commit()
        subscribed = False
    else:
        subscribed = user[1]
    
    if not subscribed:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscribe")]
        ])
        await message.answer("Чтобы пользоваться ботом, подпишитесь на канал:", reply_markup=kb)
    else:
        await show_main_menu(message)

async def show_main_menu(message_or_call):
    text = "🚀 xRocket — это бот-кошелёк для получения, отправки, покупки и хранения криптовалюты в Telegram. Обо всех возможностях читай в официальном канале @xrocketnewsru"
    if isinstance(message_or_call, types.Message):
        await message_or_call.answer(text, reply_markup=create_main_menu())
    else:
        await message_or_call.message.edit_text(text, reply_markup=create_main_menu())

@dp.callback_query(lambda c: c.data == "check_subscribe")
async def check_sub(callback: types.CallbackQuery):
    cursor.execute("UPDATE users SET subscribed = TRUE WHERE id = ?", (callback.from_user.id,))
    conn.commit()
    await callback.message.delete()
    await show_main_menu(callback)

@dp.callback_query(lambda c: c.data == "my_wallet")
async def my_wallet(callback: types.CallbackQuery):
    cursor.execute("SELECT * FROM users WHERE id = ?", (callback.from_user.id,))
    user = cursor.fetchone()
    
    text = "<b>💵 Ваш кошелёк:</b>\n\n"
    total_rub = 0
    
    for idx, currency in enumerate(CURRENCIES, start=1):
        amount = user[idx]
        rub_value = amount * CURRENCY_RATES[currency]
        total_rub += rub_value
        text += f"<b>{currency}:</b> {amount:.6f} (~{rub_value:.2f}₽)\n"
    
    text += f"\n<b>Итого:</b> ~{total_rub:.2f}₽"
    await callback.message.edit_text(text, reply_markup=create_main_menu())

# --- Пополнение ---

@dp.callback_query(lambda c: c.data == "deposit")
async def deposit_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите валюту для пополнения:",
        reply_markup=create_currency_menu("deposit_currency", "back_to_menu")
    )

@dp.callback_query(lambda c: c.data.startswith("deposit_currency_"))
async def deposit_currency(callback: types.CallbackQuery):
    currency = callback.data.split("_")[2]
    address = ''.join(random.choices(string.ascii_letters + string.digits + '_-', k=44))
    
    await callback.message.edit_text(
        f"🔹 Ваш адрес для пополнения {currency}:\n<code>{address}</code>\n\n"
        "После пополнения баланс обновится автоматически.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="deposit")]
        ])
    )

# --- Вывод средств ---

user_withdraw_data = {}

@dp.callback_query(lambda c: c.data == "withdraw")
async def withdraw_start(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Выберите валюту для вывода:",
        reply_markup=create_currency_menu("withdraw_currency", "back_to_menu")
    )

@dp.callback_query(lambda c: c.data.startswith("withdraw_currency_"))
async def withdraw_enter_amount(callback: types.CallbackQuery):
    currency = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    cursor.execute(f"SELECT {currency.lower()} FROM users WHERE id = ?", (user_id,))
    balance = cursor.fetchone()[0]
    
    user_withdraw_data[user_id] = {"currency": currency, "step": "amount"}
    
    await callback.message.edit_text(
        f"💵 Ваш баланс {currency}: {balance:.6f} (~{balance * CURRENCY_RATES[currency]:.2f}₽)\n\n"
        "Введите сумму для вывода:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="withdraw")]
        ])
    )

@dp.message(lambda m: m.from_user.id in user_withdraw_data and user_withdraw_data[m.from_user.id]["step"] == "amount")
async def withdraw_enter_address(message: types.Message):
    user_id = message.from_user.id
    currency = user_withdraw_data[user_id]["currency"]
    
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
        
        cursor.execute(f"SELECT {currency.lower()} FROM users WHERE id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        
        if amount > balance:
            await message.answer("Недостаточно средств на балансе.")
            return
        
        user_withdraw_data[user_id]["amount"] = amount
        user_withdraw_data[user_id]["step"] = "address"
        
        await message.answer(
            "Введите адрес кошелька для вывода:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="withdraw")]
            ])
        )
    except ValueError:
        await message.answer("Введите корректную сумму.")

@dp.message(lambda m: m.from_user.id in user_withdraw_data and user_withdraw_data[m.from_user.id]["step"] == "address")
async def withdraw_confirm(message: types.Message):
    user_id = message.from_user.id
    data = user_withdraw_data[user_id]
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подтвердить", callback_data="confirm_withdraw")],
        [InlineKeyboardButton(text="Отменить", callback_data="withdraw")]
    ])
    
    await message.answer(
        f"<b>Подтвердите вывод:</b>\n\n"
        f"<b>Сумма:</b> {data['amount']:.6f} {data['currency']} (~{data['amount'] * CURRENCY_RATES[data['currency']]:.2f}₽)\n"
        f"<b>На адрес:</b> <code>{message.text}</code>\n\n"
        f"После подтверждения средства будут отправлены.",
        reply_markup=kb
    )

@dp.callback_query(lambda c: c.data == "confirm_withdraw" and c.from_user.id in user_withdraw_data)
async def withdraw_execute(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = user_withdraw_data[user_id]
    
    cursor.execute(f"UPDATE users SET {data['currency'].lower()} = {data['currency'].lower()} - ? WHERE id = ?", 
                  (data['amount'], user_id))
    conn.commit()
    
    del user_withdraw_data[user_id]
    
    await callback.message.edit_text(
        f"✅ Вывод {data['amount']:.6f} {data['currency']} успешно выполнен!",
        reply_markup=create_main_menu()
    )

# --- Дополнительные функции ---

@dp.callback_query(lambda c: c.data == "checks")
async def checks_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚙️ Тех. Работы 30 мин.",
        reply_markup=create_main_menu()
    )

@dp.callback_query(lambda c: c.data == "api_info")
async def api_info(callback: types.CallbackQuery):
    text = (
        "🤖 <b>xRocket Pay</b>\n\n"
        "Интегрируйте платежное <b>API xRocket Pay</b> 🚀 в свой сервис.\n\n"
        "Вы можете создать чеки, счета и делать переводы, используя наше API.\n\n"
        "Комиссия на входящие транзакции составит 1.5% (для счетов или пополнений приложений), "
        "все остальные операции без комиссии.\n\n"
        "Вся документация - https://pay.xrocket.tg/api/"
    )
    await callback.message.edit_text(
        text,
        reply_markup=create_main_menu()
    )

# --- Админ-панель ---

admin_data = {}

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Выдать крипту", callback_data="admin_give")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    await message.answer("🔐 Админ-панель", reply_markup=kb)

@dp.callback_query(lambda c: c.data == "admin_give" and c.from_user.id == ADMIN_ID)
async def admin_give_currency(callback: types.CallbackQuery):
    admin_data[callback.from_user.id] = {"step": "user_id"}
    await callback.message.edit_text("Введите ID пользователя:")

@dp.message(lambda m: m.from_user.id in admin_data and admin_data[m.from_user.id]["step"] == "user_id")
async def admin_enter_user_id(message: types.Message):
    if not message.text.isdigit():
        await message.answer(" Введите корректный ID пользователя.")
        return
    
    admin_data[message.from_user.id]["user_id"] = int(message.text)
    admin_data[message.from_user.id]["step"] = "currency"
    
    await message.answer(
        "Выберите валюту для выдачи:",
        reply_markup=create_currency_menu("admin_currency", "admin_give")
    )

@dp.callback_query(lambda c: c.data.startswith("admin_currency_") and c.from_user.id in admin_data)
async def admin_choose_currency(callback: types.CallbackQuery):
    admin_data[callback.from_user.id]["currency"] = callback.data.split("_")[2]
    admin_data[callback.from_user.id]["step"] = "amount"
    await callback.message.edit_text("Введите количество монет для выдачи:")

@dp.message(lambda m: m.from_user.id in admin_data and admin_data[m.from_user.id]["step"] == "amount")
async def admin_enter_amount(message: types.Message):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer(" Введите корректное число.")
        return
    
    user_id = admin_data[message.from_user.id]["user_id"]
    currency = admin_data[message.from_user.id]["currency"]
    
    cursor.execute(f"UPDATE users SET {currency.lower()} = {currency.lower()} + ? WHERE id = ?", (amount, user_id))
    conn.commit()
    
    try:
        await bot.send_message(user_id, f"✅ Вы получили {amount} {currency} (~{amount * CURRENCY_RATES[currency]:.2f}₽) на свой кошелек.")
    except:
        pass
    
    await message.answer(f"Успешно выдано {amount} {currency} пользователю {user_id}.")
    del admin_data[message.from_user.id]

# --- Общие хендлеры ---

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await show_main_menu(callback)

@dp.callback_query(lambda c: c.data == "p2p_market")
async def p2p_market(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "⚙️ P2P маркет находится на технических работах.",
        reply_markup=create_main_menu()
    )

# --- Запуск ---

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())