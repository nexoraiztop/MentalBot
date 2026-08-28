"""
Telegram-бот: слот-машина 🎰 → джекпот 777 → мини-игра прокачки приза (боулинг 🎳).

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
from aiogram.filters import CommandStart
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

# Username админов для выдачи приза (без @)
ADMIN_USERNAMES = ["dol1ro"]

# Ссылки на NFT-подарки (финальный уровень лестницы призов)
rewards_list = [
    "http://t.me/nft/ViceCream-157848",
    "http://t.me/nft/ViceCream-112371",
]

# ID премиум-эмодзи, по местам использования
EMOJI_PARTY_CLAIM = "5461151367559141950"      # 🎉 в сообщении "Вы забрали приз"
EMOJI_STAR_CLAIM = "4983748881977181112"       # ⭐️ в сообщении "Вы забрали приз" / прокачке
EMOJI_PARTY_JACKPOT = "5208541126583136130"    # 🎉 в стартовом сообщении джекпота
EMOJI_SEVEN = "5443135830883313930"            # 7️⃣ комбинация 777
EMOJI_STAR_JACKPOT = "5924870095925942277"     # ⭐️ "Текущая награда: подарок 15⭐"
EMOJI_BEAR = "5285201976374630866"             # 🧸 перед "Выберите: хотите забрать..."
EMOJI_CHECK = "5211112665237175703"            # ✅ в конце вопроса
EMOJI_CRY = "5393147196151438001"              # 😭 "Увы, не повезло"
EMOJI_STAR_RETRY = "4996928143743780970"       # ⭐ "Попробуйте ещё раз"
EMOJI_SMILE = "6309567129762926960"            # 😃 в конце "Попробуйте ещё раз"
EMOJI_BOWLING = "5391273757186730640"          # 🎳 заголовок выбора диапазона
EMOJI_STAR_HEADER = "5006240624978953230"      # 🌟 в заголовке диапазона / прокачке приза
EMOJI_FIRE = "5463154755054349837"             # 🔥 в пояснении про диапазон (2 раза)
EMOJI_SIX = "5891120371762990493"              # 6️⃣ "бросит шар 6"
EMOJI_WARNING = "5447644880824181073"          # ⚠️ предупреждение про сгорание
EMOJI_MEDAL = "5170149156953523243"            # 🎖 "испытать удачу ещё, или забрать приз?"
EMOJI_SPARKLES = "4963511421280192936"         # 💫 "За выдачей пишите"

# Значение dice.value == 64 соответствует комбинации 777 на слот-машине 🎰
SLOT_JACKPOT_VALUE = 64

# Лестница призов. Последний уровень — NFT (особый флаг is_nft=True)
PRIZE_LADDER = [
    {"label": "15⭐", "value": 15, "is_nft": False},
    {"label": "40⭐", "value": 40, "is_nft": False},
    {"label": "75⭐", "value": 75, "is_nft": False},
    {"label": "100⭐", "value": 100, "is_nft": False},
    {"label": "NFT 🎁", "value": None, "is_nft": True},
]

# Диапазоны для мини-игры с боулингом (🎳 даёт число от 1 до 6).
# На простых уровнях (15→40, 40→75) — 2 диапазона по 3 числа (шанс 50/50 на каждый).
# На сложных уровнях (75→100, 100→NFT) — 3 диапазона по 2 числа (шанс 33/33/33 на каждый),
# так угадать becomes сложнее, хотя каждая отдельная кнопка честная.
RANGE_OPTIONS_EASY = [(1, 3), (4, 6)]
RANGE_OPTIONS_HARD = [(1, 2), (3, 4), (5, 6)]

# С какого уровня (индекс в PRIZE_LADDER, т.е. ТЕКУЩИЙ приз перед броском)
# начинают действовать сложные диапазоны из 3 кнопок.
HARD_RANGE_FROM_LEVEL = 2  # уровень 2 = приз 75⭐ (попытка апгрейда до 100⭐)


def get_range_options(level: int) -> list[tuple[int, int]]:
    return RANGE_OPTIONS_HARD if level >= HARD_RANGE_FROM_LEVEL else RANGE_OPTIONS_EASY

# ==== МАГАЗИН ====
# За каждое выпавшее 777 пользователю начисляется это количество звёзд на баланс магазина
SHOP_REWARD_PER_JACKPOT = 5

# Товары магазина. NFT сюда сознательно не добавляем — только звёздные призы.
SHOP_ITEMS = [
    {"id": "bear_nexo", "label": "🧸 Мишка от Nexo", "price": 100},
    {"id": "rose_nexo", "label": "🌹❤️ Роза от Nexo", "price": 150},
    {"id": "gift_nexo", "label": "🎁 Подарок от Nexo", "price": 50},
]

# Баланс магазина хранится в базе данных, а не в памяти процесса — иначе
# он обнулялся бы при каждом редеплое.
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
    if USE_POSTGRES:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS balances ("
            "user_id BIGINT PRIMARY KEY, "
            "balance BIGINT NOT NULL DEFAULT 0"
            ")"
        )
        conn.commit()
        cur.close()
    else:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS balances ("
            "user_id INTEGER PRIMARY KEY, "
            "balance INTEGER NOT NULL DEFAULT 0"
            ")"
        )
        conn.commit()
    conn.close()

    logging.info(
        "Хранилище баланса: %s", "PostgreSQL" if USE_POSTGRES else f"SQLite ({DB_PATH})"
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

router = Router()

# Активные игры: game_id -> {"user_id", "level", "chat_id"}
active_games: dict[str, dict] = {}


def custom_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def sevens_text() -> str:
    return custom_emoji(EMOJI_SEVEN, "7️⃣") * 3


def mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'


def admins_line() -> str:
    return " ".join(f"@{u}" for u in ADMIN_USERNAMES)


def prize_keyboard(game_id: str, level: int) -> InlineKeyboardMarkup:
    prize = PRIZE_LADDER[level]
    buttons = [
        InlineKeyboardButton(
            text=f"🎁 Забрать {prize['label']}",
            callback_data=f"claim:{game_id}",
        )
    ]
    # На последнем уровне (NFT) дальше рисковать некуда
    if level < len(PRIZE_LADDER) - 1:
        buttons.append(
            InlineKeyboardButton(
                text="🎳 Испытать удачу", callback_data=f"risk:{game_id}"
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def range_keyboard(game_id: str, level: int) -> InlineKeyboardMarkup:
    options = get_range_options(level)
    buttons = [
        InlineKeyboardButton(
            text=f"{lo}-{hi}", callback_data=f"range:{game_id}:{lo}:{hi}"
        )
        for lo, hi in options
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏪 Магазин", callback_data="menu:shop")]]
    )


def shop_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{item['label']} — {item['price']}⭐",
                callback_data=f"buy:{item['id']}",
            )
        ]
        for item in SHOP_ITEMS
    ]
    buttons.append([InlineKeyboardButton(text="« Назад", callback_data="menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Привет! Крути слот-машину 🎰 в чате — при выпадении 777 "
        "стартует игра на прокачку приза, а на баланс магазина "
        f"падает +{SHOP_REWARD_PER_JACKPOT}⭐.",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "menu:shop")
async def handle_open_shop(callback: CallbackQuery) -> None:
    balance = get_balance(callback.from_user.id)
    text = (
        "🛍 Магазин\n\n"
        f"⭐ Твой баланс: {balance}\n\n"
        "Выбери подарок ниже:"
    )
    await callback.message.edit_text(text, reply_markup=shop_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:back")
async def handle_menu_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "👋 Главное меню", reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def handle_buy(callback: CallbackQuery) -> None:
    # Пока подключаем только витрину магазина и баланс — сама покупка
    # (списание звёзд и выдача приза) будет добавлена следующим шагом.
    await callback.answer("Покупка скоро будет доступна 🙂", show_alert=True)


@router.message(F.dice.emoji == "🎰")
async def handle_slot_machine(message: Message) -> None:
    dice_value = message.dice.value
    if dice_value != SLOT_JACKPOT_VALUE:
        return

    user = message.from_user

    # Начисляем звёзды в магазин за каждое выпавшее 777 —
    # реагируем в том числе и на пересланные сообщения с броском.
    add_balance(user.id, SHOP_REWARD_PER_JACKPOT)

    game_id = uuid.uuid4().hex[:12]
    active_games[game_id] = {
        "user_id": user.id,
        "level": 0,
        "chat_id": message.chat.id,
        "last_message_id": None,  # заполнится ниже, после отправки сообщения
    }

    prize = PRIZE_LADDER[0]
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

    prize = PRIZE_LADDER[game["level"]]
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
        prize = PRIZE_LADDER[game["level"]]
        text = (
            f"🎳 Выпало: {pins}\n\n"
            f"{custom_emoji(EMOJI_STAR_HEADER, '🌟')}Поздравляем, ваша "
            f"награда прокачена!\n\n"
            f"Текущая награда: подарок {prize['value']}"
            f"{custom_emoji(EMOJI_STAR_CLAIM, '⭐️')}\n\n"
        )
        if prize["is_nft"]:
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

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
