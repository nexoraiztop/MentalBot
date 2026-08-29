"""
Telegram-бот: слот-машина 🎰 → джекпот 777 → мини-игра прокачки приза (боулинг 🎳)
→ магазин с заявками на покупку → профиль игрока.

Установка:
    pip install aiogram

Запуск:
    python bowling_upgrade_bot.py

Токен бота берётся из переменной окружения BOT_TOKEN
(задаётся в настройках хостинга, например Railway → Variables).
"""

import asyncio
import logging
import os
import random
import sqlite3
import uuid

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ==== НАСТРОЙКИ ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

logging.basicConfig(level=logging.INFO)

# Username админов для выдачи приза и подтверждения заявок в магазине (без @)
ADMIN_USERNAMES = ["dol1ro"]
SUPPORT_USERNAME = ADMIN_USERNAMES[0]  # кому писать по вопросам ("@ссылка" в текстах)

# Ссылки на NFT-подарки (финальный уровень лестницы призов)
rewards_list = [
    "http://t.me/nft/ViceCream-157848",
    "http://t.me/nft/ViceCream-112371",
]

# ID премиум-эмодзи, по местам использования
EMOJI_PARTY_CLAIM = "5461151367559141950"      # 🎉 в сообщении "Вы забрали приз"
EMOJI_STAR_CLAIM = "4983748881977181112"       # ⭐️ в сообщении "Вы забрали приз" / прокачке
EMOJI_PARTY_JACKPOT = "5208541126583136130"    # 🎉 в стартовом сообщении джекпота (и в заявках)
EMOJI_SEVEN = "5443135830883313930"            # 7️⃣ комбинация 777
EMOJI_STAR_JACKPOT = "5924870095925942277"     # ⭐️ "Текущая награда: подарок 15⭐" (и в профиле)
EMOJI_BEAR = "5285201976374630866"             # 🧸 перед "Выберите: хотите забрать..."
EMOJI_CHECK = "5211112665237175703"            # ✅ в конце вопроса
EMOJI_CRY = "5393147196151438001"              # 😭 "Увы, не повезло"
EMOJI_STAR_RETRY = "4996928143743780970"       # ⭐ "Попробуйте ещё раз"
EMOJI_SMILE = "6309567129762926960"            # 😃 в конце "Попробуйте ещё раз" (и в профиле)
EMOJI_BOWLING = "5391273757186730640"          # 🎳 заголовок выбора диапазона
EMOJI_STAR_HEADER = "5006240624978953230"      # 🌟 диапазон / прокачка приза (и в заявках)
EMOJI_FIRE = "5463154755054349837"             # 🔥 в пояснении про диапазон (2 раза)
EMOJI_SIX = "5891120371762990493"              # 6️⃣ "бросит шар 6" (и на кнопках диапазона)
EMOJI_WARNING = "5447644880824181073"          # ⚠️ предупреждение про сгорание
EMOJI_MEDAL = "5170149156953523243"            # 🎖 "испытать удачу ещё, или забрать приз?"
EMOJI_SPARKLES = "4963511421280192936"         # 💫 "За выдачей пишите"

# ID премиум-эмодзи — главное меню (/start)
EMOJI_WAVE = "4918354603281482671"             # 👋 "Привет! Ты в главном меню"
EMOJI_MENU_MEDAL = "4938313951961155725"       # 🎖 "Здесь ты можешь переходить..."
EMOJI_GAMEPAD = "5012808218385058363"          # 🎮 "Основной фарм звёзд"
EMOJI_MENU_DIAMOND = "5294460341021862670"     # 💎 "Выбери нужное действие"
EMOJI_POINT_DOWN = "5231102735817918643"       # 👇 в конце меню

# ID премиум-эмодзи — магазин
EMOJI_STAR_FACE = "4938214716741781530"        # 🤩 "Добро пожаловать в Магазин"
EMOJI_SHOP_BEAR = "5294227158657427099"        # 🧸 (используется и одиночно, и рядом x3)
EMOJI_SHOP_ROCKET = "5296738580654221916"      # 🚀 (используется и одиночно, и рядом x3)
EMOJI_SHOP_DIAMOND = "5296474019258721875"     # 💎 (используется и одиночно, и рядом x3)
EMOJI_SHOP_FIRE = "5116414868357907335"        # 🔥 "Максимальная выгода!"
EMOJI_COIN = "4965663015211894662"             # 🪙 "Твой баланс" (и на кнопке "Магазин")
EMOJI_HOURGLASS = "5891211339170326418"        # ⌛️ напоминание про очередь выдачи
EMOJI_HANDS = "5008248651038852115"            # 🫴 "Фармить звёзды можешь в чате..."

# ID премиум-эмодзи — часовое рекламное напоминание (/promo_on)
EMOJI_R_SLOT = "5915833712368424979"           # 🎰 (используется несколько раз)
EMOJI_R_TROPHY = "5388773012478659078"         # 🏆 (используется дважды)
EMOJI_R_CHART = "5197503331215361533"          # 📈 "ПРАВИЛА ЛЕСЕНКИ"
EMOJI_R_GIFT = "5436006606078769970"           # 🎁 "Забрать награду"
EMOJI_R_TARGET = "5310278924616356636"         # 🎯 "Испытать удачу"
EMOJI_R_WARNING = "5275986299407344497"        # ⚠️ "Не повезёт..."
EMOJI_R_FIRE = "5190600446892326598"           # 🔥 "сгорает"
EMOJI_R_SALUTE = "6050773179557745617"         # 🫡 в конце текста

# ID премиум-эмодзи — заявка на покупку в магазине: "в обработке"
EMOJI_REQ_WAVE = "5193197184119487084"         # 👋 "Приветствуем!"
EMOJI_REQ_GLOBE = "5192830415387243122"        # 🌐 после "подарок"
EMOJI_REQ_SUNGLASSES = "5305487794108405635"   # 🕶️ "Сейчас заявка ожидает..."
EMOJI_REQ_THUMBSUP = "5391210243210353922"     # 👍 "не нужно ни о чём"
EMOJI_REQ_SEARCH = "5292014795233466480"       # 🔍 в конце блока ожидания
EMOJI_REQ_GIFT_WAIT = "5226661632259691727"    # 🎁 "подарок будет вашим!"

# ID премиум-эмодзи — заявка на покупку: "одобрена"
EMOJI_REQ_MONEY1 = "5199615755045344644"       # 🤑 "уже в пути"
EMOJI_REQ_COIN2 = "5103047194965968549"        # 🪙 после "подарка"
EMOJI_REQ_HANDSHAKE = "4976940882071651344"    # 🤝 после "одобрена"
EMOJI_REQ_MONEY2 = "5055840333242303386"       # 🤑 "Награда отправлена"
EMOJI_REQ_COWBOY = "5008457489528652800"       # 🤠 после "аккаунт"
EMOJI_REQ_CLOCK = "5893102202817352158"        # 🕞 (используется дважды)
EMOJI_REQ_STAR_THANKS = "5951762148886582569"  # ⭐️ "Спасибо, что вы с нами"

# ID премиум-эмодзи — профиль (/profile)
EMOJI_PROFILE_PERSON = "5258011929993026890"   # 👤 заголовок профиля
EMOJI_PROFILE_CARD = "5445353829304387411"     # 💳 ID
EMOJI_PROFILE_SLOT = "4938599077660068007"     # 🎰 "Прокрутов всего"
EMOJI_PROFILE_CART = "5312361253610475399"     # 🛒 "Покупок"

# ==== ПРЕМ ЭМОДЗИ НА КНОПКАХ ====
# Единая "приборная панель" для иконок на инлайн-кнопках (параметр
# icon_custom_emoji_id у InlineKeyboardButton, Bot API 9.4+ / aiogram 3.20+).
# Хочешь поменять иконку на конкретной кнопке — меняй ID здесь, ничего
# больше в коде трогать не нужно. Иконка реально отрисуется только если у
# ВЛАДЕЛЬЦА БОТА активна Telegram Premium — иначе Telegram молча покажет
# только текст кнопки без иконки.
#
# Иконки товаров магазина сюда не входят — они у каждого товара свои,
# заданы в поле "emoji_id" внутри списка SHOP_ITEMS (см. ниже по файлу).
BUTTON_ICONS = {
    "claim": "5280615440928758599",  # 🎁 "Забрать ..." (на любом уровне лесенки)
    "risk": "5280922999241859582",   # 💎 "Испытать удачу"
    "range": EMOJI_SIX,              # 6️⃣ кнопки диапазона (1-3, 4-6, 1-2 и т.д.)
    "shop_menu": EMOJI_COIN,         # 🪙 кнопка "Магазин" в главном меню
    "profile_menu": EMOJI_PROFILE_PERSON,  # 👤 кнопка "Профиль" в главном меню
}
# Хочешь новую иконку на какой-то из этих кнопок — просто впиши сюда новый
# ID строкой (или замени ссылку на константу типа EMOJI_SIX/EMOJI_COIN
# выше), больше нигде в файле трогать не нужно.

# Как часто слать напоминание, пока оно включено (в секундах)
REMINDER_INTERVAL_SECONDS = 60 * 60  # 1 час

# Значение dice.value == 64 соответствует комбинации 777 на слот-машине 🎰
SLOT_JACKPOT_VALUE = 64

# Лестница призов. Последний уровень при включённом режиме NFT — сам NFT
# (особый флаг is_nft=True). Когда режим NFT выключен командой /nft_off,
# лесенка временно заканчивается на 100⭐ — см. get_prize_ladder() ниже.
PRIZE_LADDER_BASE = [
    {"label": "15⭐", "value": 15, "is_nft": False},
    {"label": "25⭐", "value": 25, "is_nft": False},
    {"label": "40⭐", "value": 40, "is_nft": False},
    {"label": "75⭐", "value": 75, "is_nft": False},
    {"label": "100⭐", "value": 100, "is_nft": False},
]
NFT_TOP_PRIZE = {"label": "NFT 🎁", "value": None, "is_nft": True}

# Включён ли режим NFT прямо сейчас — читается/пишется через settings-таблицу
# в БД (см. init_db/get_nft_enabled/set_nft_enabled), чтобы переживать рестарт.
_nft_enabled_cache: bool | None = None


def get_prize_ladder() -> list[dict]:
    if get_nft_enabled():
        return PRIZE_LADDER_BASE + [NFT_TOP_PRIZE]
    return PRIZE_LADDER_BASE

# Диапазоны для мини-игры с боулингом (🎳 даёт число от 1 до 6).
# На простых уровнях (15→25, 25→40, 40→75) — 2 диапазона по 3 числа (50/50).
# На сложных уровнях (75→100, 100→NFT) — 3 диапазона по 2 числа (33/33/33),
# так угадать становится сложнее, хотя каждая отдельная кнопка честная.
RANGE_OPTIONS_EASY = [(1, 3), (4, 6)]
RANGE_OPTIONS_HARD = [(1, 2), (3, 4), (5, 6)]

# С какого уровня (индекс в лестнице, т.е. ТЕКУЩИЙ приз перед броском)
# начинают действовать сложные диапазоны из 3 кнопок.
HARD_RANGE_FROM_LEVEL = 3  # уровень 3 = приз 75⭐ (попытка апгрейда до 100⭐)


def get_range_options(level: int) -> list[tuple[int, int]]:
    return RANGE_OPTIONS_HARD if level >= HARD_RANGE_FROM_LEVEL else RANGE_OPTIONS_EASY

# ==== МАГАЗИН ====
# За каждое выпавшее 777 пользователю начисляется это количество звёзд на баланс магазина
SHOP_REWARD_PER_JACKPOT = 20

# Название бренда/чата, которые упоминаются в текстах магазина и меню —
# поменяй под свои реальные названия.
SHOP_BRAND_NAME = "nexoraiza"
FARM_CHAT_USERNAME = "mentalLudo"

# Сколько примерно ждать: используется в текстах заявки на покупку
REVIEW_WAIT_TEXT = "5-15 минут"     # пока заявка "в обработке" у админа
DELAY_MIN_TEXT = "10 минут"         # после одобрения — минимальный срок зачисления
DELAY_MAX_TEXT = "24 часов"         # после одобрения — максимальный срок зачисления

# Товары магазина: одиночные и "рядами" (по 3шт со скидкой).
# emoji_id используется и на кнопках покупки (icon_custom_emoji_id),
# и в тексте витрины (build_shop_text).
SHOP_ITEMS = [
    {"id": "bear", "emoji_id": EMOJI_SHOP_BEAR, "emoji": "🧸", "name": "Мишка",
     "price": 250, "qty": 1, "note": "(Самый невыгодный вариант)"},
    {"id": "rocket", "emoji_id": EMOJI_SHOP_ROCKET, "emoji": "🚀", "name": "Ракета",
     "price": 650, "qty": 1, "note": ""},
    {"id": "diamond", "emoji_id": EMOJI_SHOP_DIAMOND, "emoji": "💎", "name": "Алмаз",
     "price": 1500, "qty": 1, "note": ""},
    {"id": "bear_row", "emoji_id": EMOJI_SHOP_BEAR, "emoji": "🧸", "name": "Ряд мишек",
     "price": 600, "qty": 3, "note": "(Выгода: 3 по цене 2.4)"},
    {"id": "rocket_row", "emoji_id": EMOJI_SHOP_ROCKET, "emoji": "🚀", "name": "Ряд ракет",
     "price": 1500, "qty": 3, "note": "(Выгода: 3 по цене 2.3)"},
    {"id": "diamond_row", "emoji_id": EMOJI_SHOP_DIAMOND, "emoji": "💎", "name": "Ряд алмазов",
     "price": 3000, "qty": 3, "note": ""},
]

# Баланс, статистика и заявки на покупку хранятся в базе данных, а не в
# памяти процесса — иначе всё обнулялось бы при каждом редеплое.
#
# Если Railway даёт переменную DATABASE_URL (после того как в проект добавлен
# сервис PostgreSQL) — используем Postgres, он персистентный и переживает
# любой редеплой без дополнительной настройки.
#
# Если DATABASE_URL не задан — работаем через локальный SQLite-файл (удобно
# для теста на своём компьютере, но на Railway без Postgres это НЕ переживёт
# редеплой).
DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH = os.getenv("DB_PATH", "shop.db")

USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extensions


def _get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    conn = _get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS balances ("
            "user_id BIGINT PRIMARY KEY, "
            "balance BIGINT NOT NULL DEFAULT 0"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS reminder_chats ("
            "chat_id BIGINT PRIMARY KEY"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, "
            "value TEXT NOT NULL"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS user_stats ("
            "user_id BIGINT PRIMARY KEY, "
            "spins BIGINT NOT NULL DEFAULT 0, "
            "jackpots BIGINT NOT NULL DEFAULT 0, "
            "purchases BIGINT NOT NULL DEFAULT 0"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS purchase_requests ("
            "id SERIAL PRIMARY KEY, "
            "user_id BIGINT NOT NULL, "
            "chat_id BIGINT NOT NULL, "
            "item_id TEXT NOT NULL, "
            "item_name TEXT NOT NULL, "
            "price BIGINT NOT NULL, "
            "status TEXT NOT NULL DEFAULT 'pending'"
            ")"
        )
    else:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS balances ("
            "user_id INTEGER PRIMARY KEY, "
            "balance INTEGER NOT NULL DEFAULT 0"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS reminder_chats ("
            "chat_id INTEGER PRIMARY KEY"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, "
            "value TEXT NOT NULL"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS user_stats ("
            "user_id INTEGER PRIMARY KEY, "
            "spins INTEGER NOT NULL DEFAULT 0, "
            "jackpots INTEGER NOT NULL DEFAULT 0, "
            "purchases INTEGER NOT NULL DEFAULT 0"
            ")"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS purchase_requests ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, "
            "chat_id INTEGER NOT NULL, "
            "item_id TEXT NOT NULL, "
            "item_name TEXT NOT NULL, "
            "price INTEGER NOT NULL, "
            "status TEXT NOT NULL DEFAULT 'pending'"
            ")"
        )
    conn.commit()
    cur.close()
    conn.close()

    logging.info(
        "Хранилище данных: %s", "PostgreSQL" if USE_POSTGRES else f"SQLite ({DB_PATH})"
    )


def get_balance(user_id: int) -> int:
    conn = _get_conn()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(f"SELECT balance FROM balances WHERE user_id = {placeholder}", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else 0


def add_balance(user_id: int, amount: int) -> None:
    conn = _get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            "INSERT INTO balances (user_id, balance) VALUES (%s, %s) "
            "ON CONFLICT (user_id) DO UPDATE SET balance = balances.balance + EXCLUDED.balance",
            (user_id, amount),
        )
    else:
        cur.execute(
            "INSERT INTO balances (user_id, balance) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET balance = balance + excluded.balance",
            (user_id, amount),
        )
    conn.commit()
    cur.close()
    conn.close()


def try_spend_balance(user_id: int, amount: int) -> bool:
    """Атомарно списывает amount со счёта, если хватает средств.
    Возвращает True при успехе, False если баланса недостаточно
    (или пользователь ещё ни разу не выбивал 777 — строки в balances нет)."""
    conn = _get_conn()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(
        f"UPDATE balances SET balance = balance - {placeholder} "
        f"WHERE user_id = {placeholder} AND balance >= {placeholder}",
        (amount, user_id, amount),
    )
    success = cur.rowcount > 0
    conn.commit()
    cur.close()
    conn.close()
    return success


def enable_reminder_chat(chat_id: int) -> None:
    conn = _get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            "INSERT INTO reminder_chats (chat_id) VALUES (%s) "
            "ON CONFLICT (chat_id) DO NOTHING",
            (chat_id,),
        )
    else:
        cur.execute(
            "INSERT OR IGNORE INTO reminder_chats (chat_id) VALUES (?)", (chat_id,)
        )
    conn.commit()
    cur.close()
    conn.close()


def disable_reminder_chat(chat_id: int) -> None:
    conn = _get_conn()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(f"DELETE FROM reminder_chats WHERE chat_id = {placeholder}", (chat_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_reminder_chats() -> list[int]:
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT chat_id FROM reminder_chats")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [row[0] for row in rows]


NFT_SETTING_KEY = "nft_enabled"


def get_nft_enabled() -> bool:
    """Читает флаг из settings-таблицы (по умолчанию — включено), с кэшем
    в памяти процесса, чтобы не ходить в БД на каждый рендер клавиатуры."""
    global _nft_enabled_cache
    if _nft_enabled_cache is not None:
        return _nft_enabled_cache

    conn = _get_conn()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(f"SELECT value FROM settings WHERE key = {placeholder}", (NFT_SETTING_KEY,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    _nft_enabled_cache = (row is None) or (row[0] == "1")
    return _nft_enabled_cache


def set_nft_enabled(enabled: bool) -> None:
    global _nft_enabled_cache
    conn = _get_conn()
    cur = conn.cursor()
    value = "1" if enabled else "0"
    if USE_POSTGRES:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (%s, %s) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
            (NFT_SETTING_KEY, value),
        )
    else:
        cur.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (NFT_SETTING_KEY, value),
        )
    conn.commit()
    cur.close()
    conn.close()
    _nft_enabled_cache = enabled


def _increment_stat(user_id: int, column: str) -> None:
    # column всегда один из захардкоженных литералов ниже (spins/jackpots/
    # purchases) — никогда не берётся из пользовательского ввода.
    conn = _get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            f"INSERT INTO user_stats (user_id, {column}) VALUES (%s, 1) "
            f"ON CONFLICT (user_id) DO UPDATE SET {column} = user_stats.{column} + 1",
            (user_id,),
        )
    else:
        cur.execute(
            f"INSERT INTO user_stats (user_id, {column}) VALUES (?, 1) "
            f"ON CONFLICT(user_id) DO UPDATE SET {column} = {column} + 1",
            (user_id,),
        )
    conn.commit()
    cur.close()
    conn.close()


def increment_spins(user_id: int) -> None:
    _increment_stat(user_id, "spins")


def increment_jackpots(user_id: int) -> None:
    _increment_stat(user_id, "jackpots")


def increment_purchases(user_id: int) -> None:
    _increment_stat(user_id, "purchases")


def get_stats(user_id: int) -> dict:
    conn = _get_conn()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(
        f"SELECT spins, jackpots, purchases FROM user_stats WHERE user_id = {placeholder}",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        return {"spins": 0, "jackpots": 0, "purchases": 0}
    return {"spins": row[0], "jackpots": row[1], "purchases": row[2]}


def create_purchase_request(
    user_id: int, chat_id: int, item_id: str, item_name: str, price: int
) -> int:
    conn = _get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            "INSERT INTO purchase_requests "
            "(user_id, chat_id, item_id, item_name, price, status) "
            "VALUES (%s, %s, %s, %s, %s, 'pending') RETURNING id",
            (user_id, chat_id, item_id, item_name, price),
        )
        new_id = cur.fetchone()[0]
    else:
        cur.execute(
            "INSERT INTO purchase_requests "
            "(user_id, chat_id, item_id, item_name, price, status) "
            "VALUES (?, ?, ?, ?, ?, 'pending')",
            (user_id, chat_id, item_id, item_name, price),
        )
        new_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return new_id


def get_purchase_request(request_id: int) -> dict | None:
    conn = _get_conn()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, user_id, chat_id, item_id, item_name, price, status "
        f"FROM purchase_requests WHERE id = {placeholder}",
        (request_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        return None
    return {
        "id": row[0], "user_id": row[1], "chat_id": row[2],
        "item_id": row[3], "item_name": row[4], "price": row[5], "status": row[6],
    }


def set_request_status(request_id: int, status: str) -> None:
    conn = _get_conn()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(
        f"UPDATE purchase_requests SET status = {placeholder} WHERE id = {placeholder}",
        (status, request_id),
    )
    conn.commit()
    cur.close()
    conn.close()


router = Router()

# Активные игры: game_id -> {"user_id", "level", "chat_id"}
active_games: dict[str, dict] = {}

# Активные задачи почасового напоминания: chat_id -> asyncio.Task
reminder_tasks: dict[int, asyncio.Task] = {}


def custom_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def sevens_text() -> str:
    return custom_emoji(EMOJI_SEVEN, "7️⃣") * 3


def mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'


def admins_line() -> str:
    return " ".join(f"@{u}" for u in ADMIN_USERNAMES)


def is_admin(username: str | None) -> bool:
    return username is not None and username in ADMIN_USERNAMES


def build_reminder_text() -> str:
    star = custom_emoji(EMOJI_STAR_JACKPOT, "⭐️")
    return (
        f"{custom_emoji(EMOJI_R_SLOT, '🎰')}ИГРАЙ И ЗАБИРАЙ {star} ВСЕГО ЗА "
        f"1{custom_emoji(EMOJI_STAR_HEADER, '🌟')}\n\n"
        f"{custom_emoji(EMOJI_R_TROPHY, '🏆')} ДЖЕКПОТ ЧАТА: смотри @Mentalludo_Bot\n\n"
        f"{custom_emoji(EMOJI_R_CHART, '📈')} ПРАВИЛА ЛЕСЕНКИ:\n\n"
        f"{custom_emoji(EMOJI_R_SLOT, '🎰')} Выбил {sevens_text()}: "
        f"15 {star} ➔ 25 {star} ➔ 40 {star} ➔ 75 {star} ➔ 100{star}\n\n"
        f"{custom_emoji(EMOJI_STAR_HEADER, '🌟')} КАК ИГРАТЬ:\n\n"
        f"{custom_emoji(EMOJI_R_SLOT, '🎰')} Выбил {sevens_text()} — получаешь "
        f"шанс начать лесенку с 15 {star}\n\n"
        f"🎳 На каждом этапе решай сам:\n"
        f"{custom_emoji(EMOJI_R_GIFT, '🎁')} Забрать награду или "
        f"{custom_emoji(EMOJI_R_TARGET, '🎯')} Испытать удачу и подняться выше!\n\n"
        f"{custom_emoji(EMOJI_R_WARNING, '⚠️')} Не повезёт — текущая награда "
        f"сгорает {custom_emoji(EMOJI_R_FIRE, '🔥')}\n\n"
        f"{custom_emoji(EMOJI_R_TROPHY, '🏆')} Дойдёшь до 100{star} — забирай "
        f"главный приз!\n\n"
        f"Скоро в лудку добавится NFT{custom_emoji(EMOJI_R_SALUTE, '🫡')}"
    )


async def reminder_loop(bot: Bot, chat_id: int) -> None:
    """Раз в REMINDER_INTERVAL_SECONDS шлёт промо-текст в чат, пока не отменят."""
    try:
        while True:
            try:
                await bot.send_message(chat_id, build_reminder_text())
            except Exception as e:
                logging.error("Не удалось отправить напоминание в %s: %s", chat_id, e)
            await asyncio.sleep(REMINDER_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        pass


def start_reminder(bot: Bot, chat_id: int) -> None:
    if chat_id in reminder_tasks:
        return
    reminder_tasks[chat_id] = asyncio.create_task(reminder_loop(bot, chat_id))


def stop_reminder(chat_id: int) -> None:
    task = reminder_tasks.pop(chat_id, None)
    if task:
        task.cancel()


def build_main_menu_text() -> str:
    return (
        f"{custom_emoji(EMOJI_WAVE, '👋')}Привет! Ты в главном меню {SHOP_BRAND_NAME}\n"
        f"{custom_emoji(EMOJI_MENU_MEDAL, '🎖')}Здесь ты можешь переходить к обмену "
        f"накопленных звёзд на крутые призы, открывать маркетплейс и переходить в "
        f"игровой чат для фарма!\n\n"
        f"<blockquote>{custom_emoji(EMOJI_GAMEPAD, '🎮')} Основной фарм звезд:\n"
        f"Залетай в наш чат @{FARM_CHAT_USERNAME}, выбивай комбинацию 777 в игровых "
        f"автоматах и забирай +{SHOP_REWARD_PER_JACKPOT} звёзд моментально прямо на "
        f"свой счет!</blockquote>\n"
        f"{custom_emoji(EMOJI_MENU_DIAMOND, '💎')} Выбери нужное действие на кнопках "
        f"ниже{custom_emoji(EMOJI_POINT_DOWN, '👇')}:"
    )


def build_shop_text(balance: int) -> str:
    lines = [
        f"{custom_emoji(EMOJI_STAR_FACE, '🤩')}Добро пожаловать в Магазин {SHOP_BRAND_NAME}!",
        "<u>Здесь ты можешь обменять свои звёзды на крутые подарки "
        "(покупать оптом — гораздо дешевле!):</u>",
    ]

    item_lines = []
    for item in SHOP_ITEMS:
        icon = custom_emoji(item["emoji_id"], item["emoji"]) * item["qty"]
        star = custom_emoji(EMOJI_STAR_CLAIM, "⭐️")
        line = f"• {icon} {item['name']} — {item['price']} {star}"
        if item["note"]:
            line += f" {item['note']}"
        item_lines.append(line)
    # У самого выгодного товара (последний в списке) пометка идёт отдельной строкой
    item_lines.append(f"{custom_emoji(EMOJI_SHOP_FIRE, '🔥')} (Максимальная выгода!)")

    lines.append("<blockquote>" + "\n".join(item_lines) + "</blockquote>")
    lines.append(f"{custom_emoji(EMOJI_COIN, '🪙')} Твой баланс: {balance} звёзд")
    lines.append("")
    lines.append(
        f"{custom_emoji(EMOJI_HOURGLASS, '⌛️')} Напоминание: При выводе призов "
        f"учитывайте, что подарок может прийти не сразу. Все заявки обрабатываются "
        f"в порядке очереди, поэтому не паникуйте — ваш выигрыш обязательно дойдет!"
    )
    lines.append("")
    lines.append(
        f"{custom_emoji(EMOJI_HANDS, '🫴')} Фармить звёзды ты можешь в нашем чате "
        f"@{FARM_CHAT_USERNAME}! Выбивай комбинацию 777 и получай "
        f"+{SHOP_REWARD_PER_JACKPOT} звёзд сразу на свой баланс в магазине! "
        f"Скорее заходи, крути и забирай!"
    )
    return "\n".join(lines)


def build_pending_request_text(name: str, request_id: int, item_name: str) -> str:
    return (
        f"{custom_emoji(EMOJI_PARTY_JACKPOT, '🎉')}<b> {name}, ваша заявка уже в "
        f"обработке!</b>\n\n"
        f"{custom_emoji(EMOJI_REQ_WAVE, '👋')}Приветствуем! Мы бережно приняли ваш "
        f"запрос №{request_id} на подарок{custom_emoji(EMOJI_REQ_GLOBE, '🌐')} "
        f"«{item_name}».\n\n"
        f"<blockquote>{custom_emoji(EMOJI_REQ_SUNGLASSES, '🕶️')}Сейчас заявка "
        f"ожидает подтверждения от администратора — обычно это занимает около "
        f"{REVIEW_WAIT_TEXT}. Вам не нужно ни о чем"
        f"{custom_emoji(EMOJI_REQ_THUMBSUP, '👍')} переживать: как только статус "
        f"изменится, мы сразу же свяжемся с вами"
        f"{custom_emoji(EMOJI_REQ_SEARCH, '🔍')}</blockquote>\n\n"
        f"Еще немного терпения, и подарок будет вашим! "
        f"{custom_emoji(EMOJI_REQ_GIFT_WAIT, '🎁')}"
    )


def build_approved_request_text(request_id: int, item_name: str) -> str:
    return (
        f"{custom_emoji(EMOJI_PARTY_JACKPOT, '🎉')}<b> Отличные новости! Ваш подарок "
        f"уже в пути</b>{custom_emoji(EMOJI_REQ_MONEY1, '🤑')}\n\n"
        f"{custom_emoji(EMOJI_STAR_HEADER, '🌟')}Здравствуйте! Рады сообщить, что "
        f"ваша заявка №{request_id} на получение подарка"
        f"{custom_emoji(EMOJI_REQ_COIN2, '🪙')} «{item_name}» успешно одобрена"
        f"{custom_emoji(EMOJI_REQ_HANDSHAKE, '🤝')}\n\n"
        f"<blockquote>Куда: {custom_emoji(EMOJI_REQ_MONEY2, '🤑')}Награда отправлена "
        f"на ваш аккаунт{custom_emoji(EMOJI_REQ_COWBOY, '🤠')}\n"
        f"Сроки зачисления: Обычно это занимает от"
        f"{custom_emoji(EMOJI_REQ_CLOCK, '🕞')} {DELAY_MIN_TEXT} до "
        f"{DELAY_MAX_TEXT}</blockquote>\n\n"
        f"{custom_emoji(EMOJI_REQ_CLOCK, '🕞')}Осталось совсем чуть-чуть! Если у вас "
        f"возникнут вопросы или задержки, наша служба поддержки всегда на связи: "
        f"@{SUPPORT_USERNAME}. Спасибо, что вы с нами"
        f"{custom_emoji(EMOJI_REQ_STAR_THANKS, '⭐️')}"
    )


def build_rejected_request_text(request_id: int, item_name: str, refund: int) -> str:
    return (
        f"😔 Заявка №{request_id} на «{item_name}» отклонена администратором.\n\n"
        f"Списанные {refund}⭐ возвращены на ваш баланс. Если есть вопросы — "
        f"пишите: @{SUPPORT_USERNAME}"
    )


def build_profile_text(user_id: int, balance: int, stats: dict) -> str:
    return (
        f"{custom_emoji(EMOJI_PROFILE_PERSON, '👤')} <b>Ваш профиль</b>\n\n"
        f"{custom_emoji(EMOJI_PROFILE_CARD, '💳')} ID: {user_id}\n"
        f"{custom_emoji(EMOJI_STAR_JACKPOT, '⭐️')} Баланс: {balance}\n"
        f"{custom_emoji(EMOJI_PROFILE_SLOT, '🎰')} Прокрутов всего: {stats['spins']}\n"
        f"{custom_emoji(EMOJI_PROFILE_CART, '🛒')} Покупок: {stats['purchases']}\n"
        f"{custom_emoji(EMOJI_SMILE, '😃')} Всего Джекпотов: {stats['jackpots']}"
    )


def prize_keyboard(game_id: str, level: int) -> InlineKeyboardMarkup:
    ladder = get_prize_ladder()
    prize = ladder[level]
    buttons = [
        InlineKeyboardButton(
            text=f"Забрать {prize['label']}",
            callback_data=f"claim:{game_id}",
            icon_custom_emoji_id=BUTTON_ICONS["claim"],
            style="success",
        )
    ]
    # На последнем уровне лесенки дальше рисковать некуда
    if level < len(ladder) - 1:
        buttons.append(
            InlineKeyboardButton(
                text="Испытать удачу",
                callback_data=f"risk:{game_id}",
                icon_custom_emoji_id=BUTTON_ICONS["risk"],
                style="primary",
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def range_keyboard(game_id: str, level: int) -> InlineKeyboardMarkup:
    options = get_range_options(level)
    buttons = [
        InlineKeyboardButton(
            text=f"{lo}-{hi}",
            callback_data=f"range:{game_id}:{lo}:{hi}",
            icon_custom_emoji_id=BUTTON_ICONS["range"],
            style="primary",
        )
        for lo, hi in options
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="Магазин",
                callback_data="menu:shop",
                icon_custom_emoji_id=BUTTON_ICONS["shop_menu"],
                style="primary",
            ),
            InlineKeyboardButton(
                text="Профиль",
                callback_data="menu:profile",
                icon_custom_emoji_id=BUTTON_ICONS["profile_menu"],
                style="primary",
            ),
        ]]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="« Назад", callback_data="menu:back")]]
    )


def shop_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{item['name']}"
                + (f" x{item['qty']}" if item["qty"] > 1 else "")
                + f" — {item['price']}⭐",
                callback_data=f"buy:{item['id']}",
                icon_custom_emoji_id=item["emoji_id"],
            )
        ]
        for item in SHOP_ITEMS
    ]
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_review_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{request_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{request_id}"),
        ]]
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(build_main_menu_text(), reply_markup=main_menu_keyboard())


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    user = message.from_user
    balance = get_balance(user.id)
    stats = get_stats(user.id)
    await message.reply(build_profile_text(user.id, balance, stats))


@router.message(Command("promo_on"))
async def cmd_promo_on(message: Message) -> None:
    chat_id = message.chat.id
    if chat_id in reminder_tasks:
        await message.reply("Напоминание уже запущено в этом чате ✅")
        return

    enable_reminder_chat(chat_id)
    start_reminder(message.bot, chat_id)
    minutes = REMINDER_INTERVAL_SECONDS // 60
    await message.reply(
        f"✅ Напоминание запущено — буду присылать промо каждые {minutes} мин."
    )


@router.message(Command("promo_off"))
async def cmd_promo_off(message: Message) -> None:
    chat_id = message.chat.id
    if chat_id not in reminder_tasks:
        await message.reply("В этом чате напоминание и так не запущено.")
        return

    stop_reminder(chat_id)
    disable_reminder_chat(chat_id)
    await message.reply("🛑 Напоминание остановлено.")


@router.message(Command("nft_off"))
async def cmd_nft_off(message: Message) -> None:
    if not is_admin(message.from_user.username):
        await message.reply("Эта команда доступна только админам.")
        return
    if not get_nft_enabled():
        await message.reply("Режим NFT и так выключен.")
        return
    set_nft_enabled(False)
    await message.reply(
        "🛑 Режим NFT выключен. Пока он выключен, лесенка призов "
        "заканчивается на 100⭐ (без верхнего уровня) — до команды /nft_on."
    )


@router.message(Command("nft_on"))
async def cmd_nft_on(message: Message) -> None:
    if not is_admin(message.from_user.username):
        await message.reply("Эта команда доступна только админам.")
        return
    if get_nft_enabled():
        await message.reply("Режим NFT и так включён.")
        return
    set_nft_enabled(True)
    await message.reply("✅ Режим NFT снова включён.")


@router.callback_query(F.data == "menu:shop")
async def handle_open_shop(callback: CallbackQuery) -> None:
    balance = get_balance(callback.from_user.id)
    text = build_shop_text(balance)
    await callback.message.edit_text(text, reply_markup=shop_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def handle_open_profile(callback: CallbackQuery) -> None:
    user = callback.from_user
    balance = get_balance(user.id)
    stats = get_stats(user.id)
    text = build_profile_text(user.id, balance, stats)
    await callback.message.edit_text(text, reply_markup=back_to_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:back")
async def handle_menu_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        build_main_menu_text(), reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def handle_buy(callback: CallbackQuery) -> None:
    item_id = callback.data.split(":", 1)[1]
    item = next((i for i in SHOP_ITEMS if i["id"] == item_id), None)
    if item is None:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    user = callback.from_user
    if not try_spend_balance(user.id, item["price"]):
        await callback.answer(
            f"Недостаточно звёзд для покупки «{item['name']}» "
            f"(нужно {item['price']}⭐).",
            show_alert=True,
        )
        return

    request_id = create_purchase_request(
        user.id, callback.message.chat.id, item["id"], item["name"], item["price"]
    )
    await callback.answer("Заявка создана! Ждите подтверждения от администратора 🙂")

    pending_text = build_pending_request_text(user.full_name, request_id, item["name"])
    await callback.message.answer(
        pending_text, reply_markup=admin_review_keyboard(request_id)
    )


@router.callback_query(F.data.startswith("approve:"))
async def handle_approve_request(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.username):
        await callback.answer("Только администратор может подтверждать заявки.", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])
    req = get_purchase_request(request_id)
    if req is None or req["status"] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    set_request_status(request_id, "approved")
    increment_purchases(req["user_id"])

    approved_text = build_approved_request_text(request_id, req["item_name"])
    await callback.message.edit_text(approved_text)
    await callback.answer("Заявка одобрена ✅")


@router.callback_query(F.data.startswith("reject:"))
async def handle_reject_request(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.username):
        await callback.answer("Только администратор может отклонять заявки.", show_alert=True)
        return

    request_id = int(callback.data.split(":")[1])
    req = get_purchase_request(request_id)
    if req is None or req["status"] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    set_request_status(request_id, "rejected")
    add_balance(req["user_id"], req["price"])  # возвращаем списанные звёзды

    rejected_text = build_rejected_request_text(request_id, req["item_name"], req["price"])
    await callback.message.edit_text(rejected_text)
    await callback.answer("Заявка отклонена, звёзды возвращены")


@router.message(F.dice.emoji == "🎰")
async def handle_slot_machine(message: Message) -> None:
    dice_value = message.dice.value
    user = message.from_user

    # Считаем каждый прокрут (для профиля /profile), независимо от результата —
    # в том числе пересланные сообщения с броском.
    increment_spins(user.id)

    if dice_value != SLOT_JACKPOT_VALUE:
        return

    increment_jackpots(user.id)

    # Начисляем звёзды в магазин за каждое выпавшее 777
    add_balance(user.id, SHOP_REWARD_PER_JACKPOT)

    game_id = uuid.uuid4().hex[:12]
    active_games[game_id] = {
        "user_id": user.id,
        "level": 0,
        "chat_id": message.chat.id,
        "last_message_id": None,  # заполнится ниже, после отправки сообщения
    }

    prize = get_prize_ladder()[0]
    text = (
        f"{custom_emoji(EMOJI_PARTY_JACKPOT, '🎉')} Поздравляем "
        f"{mention(user.id, user.full_name)}, вы выиграли!\n\n"
        f"Джекпот {sevens_text()}!\n\n"
        f"Текущая награда: подарок {prize['value']}"
        f"{custom_emoji(EMOJI_STAR_JACKPOT, '⭐️')}\n\n"
        f"{custom_emoji(EMOJI_BEAR, '🧸')}Выберите: хотите забрать подарок, "
        f"или испытать удачу, чтобы получить награду получше"
        f"{custom_emoji(EMOJI_CHECK, '✅')}"
    )
    sent = await message.reply(text, reply_markup=prize_keyboard(game_id, 0))
    active_games[game_id]["last_message_id"] = sent.message_id


@router.callback_query(F.data.startswith("claim:"))
async def handle_claim(callback: CallbackQuery) -> None:
    game_id = callback.data.split(":")[1]
    game = active_games.get(game_id)

    if game is None:
        await callback.answer("Эта игра уже завершена.", show_alert=True)
        return
    if callback.from_user.id != game["user_id"]:
        await callback.answer("Это не твой приз 🙂", show_alert=True)
        return

    prize = get_prize_ladder()[game["level"]]
    user = callback.from_user

    if prize["is_nft"]:
        reward_url = random.choice(rewards_list)
        text = (
            f"🎊 Поздравляем, {mention(user.id, user.full_name)}! Ты выиграл NFT!\n\n"
            f"🎁 {reward_url}\n\n"
            f"За выдачей пишите: {admins_line()}"
        )
    else:
        text = (
            f"{custom_emoji(EMOJI_PARTY_CLAIM, '🎉')} Поздравляем, "
            f"{mention(user.id, user.full_name)}! Вы забрали {prize['value']}"
            f"{custom_emoji(EMOJI_STAR_CLAIM, '⭐️')}!"
        )

    del active_games[game_id]
    await callback.message.edit_text(text)
    await callback.answer()


@router.callback_query(F.data.startswith("risk:"))
async def handle_risk(callback: CallbackQuery) -> None:
    game_id = callback.data.split(":")[1]
    game = active_games.get(game_id)

    if game is None:
        await callback.answer("Эта игра уже завершена.", show_alert=True)
        return
    if callback.from_user.id != game["user_id"]:
        await callback.answer("Это не твоя игра 🙂", show_alert=True)
        return

    text = (
        f"{custom_emoji(EMOJI_BOWLING, '🎳')} Выберите диапазон кеглей"
        f"{custom_emoji(EMOJI_STAR_HEADER, '🌟')}\n\n"
        f"{custom_emoji(EMOJI_FIRE, '🔥')}Диапазон — это сколько кеглей "
        f"собьёт бот, когда бросит шар {custom_emoji(EMOJI_SIX, '6️⃣')} "
        f"(от 1 до 6).\n\n"
        f"{custom_emoji(EMOJI_WARNING, '⚠️')} Если результат броска попадёт "
        f"в выбранный вами диапазон — награда повышается,\n\n"
        f"если не попадёт — ваша награда сгорает"
        f"{custom_emoji(EMOJI_FIRE, '🔥')}"
    )
    await callback.message.edit_text(
        text, reply_markup=range_keyboard(game_id, game["level"])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("range:"))
async def handle_range_choice(callback: CallbackQuery) -> None:
    _, game_id, lo_str, hi_str = callback.data.split(":")
    lo, hi = int(lo_str), int(hi_str)

    game = active_games.get(game_id)
    if game is None:
        await callback.answer("Эта игра уже завершена.", show_alert=True)
        return
    if callback.from_user.id != game["user_id"]:
        await callback.answer("Это не твоя игра 🙂", show_alert=True)
        return

    await callback.answer()

    # Убираем кнопки диапазона сразу после выбора, чтобы по ним нельзя было
    # нажать повторно и чтобы было видно, какой вариант выбрал пользователь.
    await callback.message.edit_reply_markup(reply_markup=None)

    # Бот сам бросает боулинг-шар — отвечает на предыдущее сообщение цепочки,
    # чтобы в чате было видно, к какой игре относится бросок.
    dice_message = await callback.bot.send_dice(
        chat_id=game["chat_id"],
        emoji="🎳",
        reply_to_message_id=game["last_message_id"],
    )
    game["last_message_id"] = dice_message.message_id

    # Небольшая пауза, чтобы анимация броска успела доиграть у пользователя
    await asyncio.sleep(4)
    pins = dice_message.dice.value  # число от 1 до 6

    user = callback.from_user

    if lo <= pins <= hi:
        game["level"] += 1
        ladder = get_prize_ladder()
        prize = ladder[game["level"]]
        text = (
            f"🎳 Выпало: {pins}\n\n"
            f"{custom_emoji(EMOJI_STAR_HEADER, '🌟')}Поздравляем, ваша "
            f"награда прокачена!\n\n"
            f"Текущая награда: подарок {prize['value']}"
            f"{custom_emoji(EMOJI_STAR_CLAIM, '⭐️')}\n\n"
        )
        if game["level"] == len(ladder) - 1:
            text += "Это максимальный приз — заберите его прямо сейчас!"
        else:
            text += (
                f"Хотите испытать удачу ещё, или забрать приз?"
                f"{custom_emoji(EMOJI_MEDAL, '🎖')}\n"
                f"За выдачей пишите: {admins_line()}"
                f"{custom_emoji(EMOJI_SPARKLES, '💫')}"
            )

        # Отвечаем на сообщение с результатом броска (кегли), сохраняем id
        # этого сообщения, чтобы следующий раунд тоже встроился в цепочку.
        result_message = await callback.message.answer(
            text,
            reply_markup=prize_keyboard(game_id, game["level"]),
            reply_to_message_id=game["last_message_id"],
        )
        game["last_message_id"] = result_message.message_id
    else:
        result_message = await callback.message.answer(
            f"🎳 Выпало: {pins}\n\n"
            f"{custom_emoji(EMOJI_CRY, '😭')}Увы, не повезло! Ваша награда "
            f"сгорела.\n\n"
            f"{custom_emoji(EMOJI_STAR_RETRY, '⭐')}Попробуйте ещё раз"
            f"{custom_emoji(EMOJI_SMILE, '😃')}",
            reply_to_message_id=game["last_message_id"],
        )
        del active_games[game_id]


async def main() -> None:
    init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Восстанавливаем почасовые напоминания, включённые до перезапуска/редеплоя
    for chat_id in get_reminder_chats():
        start_reminder(bot, chat_id)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
