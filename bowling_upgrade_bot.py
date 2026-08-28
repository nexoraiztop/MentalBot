import asyncio
import logging
import os
import random
import sqlite3
import uuid

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder  # Добавили строитель

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
EMOJI_COIN = "4965663015211894662"             # 🪙 "Твой баланс"
EMOJI_HOURGLASS = "5891211339170326418"        # ⌛️ напоминание про очередь выдачи
EMOJI_HANDS = "5008248651038852115"            # 🫴 "Фармить звёзды можете в чате..."

# ID премиум-эмодзи — кнопки джекпота
EMOJI_BTN_CLAIM = "5280615440928758599"        # 🎁 кнопка "Забрать приз"
EMOJI_BTN_RISK = "5280922999241859582"         # 💎 кнопка "Испытать удачу"

# ID премиум-эмодзи — часовое рекламное напоминание (/promo_on)
EMOJI_R_SLOT = "5915833712368424979"           # 🎰 (используется несколько раз)
EMOJI_R_TROPHY = "5388773012478659078"         # 🏆 (используется дважды)
EMOJI_R_CHART = "5197503331215361533"          # 📈 "ПРАВИЛА ЛЕСЕНКИ"
EMOJI_R_GIFT = "5436006606078769970"           # 🎁 "Забрать награду"
EMOJI_R_TARGET = "5310278924616356636"         # 🎯 "Испытать удачу"
EMOJI_R_WARNING = "5275986299407344497"        # ⚠️ "Не повезёт..."
EMOJI_R_FIRE = "5190600446892326598"           # 🔥 "сгорает"
EMOJI_R_SALUTE = "6050773179557745617"         # 🫡 в конце текста

# ID премиум-эмодзи для кнопок меню
EMOJI_BTN_SHOP = "5294460341021862670"         # Иконка магазина на кнопке
EMOJI_BTN_BACK = "5447644880824181073"         # Иконка Назад

REMINDER_INTERVAL_SECONDS = 60 * 60  # 1 час
SLOT_JACKPOT_VALUE = 64

PRIZE_LADDER_BASE = [
    {"label": "15⭐", "value": 15, "is_nft": False},
    {"label": "40⭐", "value": 40, "is_nft": False},
    {"label": "75⭐", "value": 75, "is_nft": False},
    {"label": "100⭐", "value": 100, "is_nft": False},
]
NFT_TOP_PRIZE = {"label": "NFT 🎁", "value": None, "is_nft": True}
FALLBACK_TOP_PRIZE = {"label": "200⭐", "value": 200, "is_nft": False}

_nft_enabled_cache: bool | None = None

def get_prize_ladder() -> list[dict]:
    top = NFT_TOP_PRIZE if get_nft_enabled() else FALLBACK_TOP_PRIZE
    return PRIZE_LADDER_BASE + [top]

RANGE_OPTIONS_EASY = [(1, 3), (4, 6)]
RANGE_OPTIONS_HARD = [(1, 2), (3, 4), (5, 6)]
HARD_RANGE_FROM_LEVEL = 2  

def get_range_options(level: int) -> list[tuple[int, int]]:
    return RANGE_OPTIONS_HARD if level >= HARD_RANGE_FROM_LEVEL else RANGE_OPTIONS_EASY

SHOP_REWARD_PER_JACKPOT = 20
SHOP_BRAND_NAME = "nexoraiza"
FARM_CHAT_USERNAME = "mentalLudo"

SHOP_ITEMS = [
    {"id": "bear", "emoji_id": EMOJI_SHOP_BEAR, "name": "Мишка", "price": 250},
    {"id": "rocket", "emoji_id": EMOJI_SHOP_ROCKET, "name": "Ракета", "price": 650},
    {"id": "diamond", "emoji_id": EMOJI_SHOP_DIAMOND, "name": "Алмаз", "price": 1500},
    {"id": "bear_row", "emoji_id": EMOJI_SHOP_BEAR, "name": "Ряд мишек", "price": 600},
    {"id": "rocket_row", "emoji_id": EMOJI_SHOP_ROCKET, "name": "Ряд ракет", "price": 1500},
    {"id": "diamond_row", "emoji_id": EMOJI_SHOP_DIAMOND, "name": "Ряд алмазов", "price": 3000},
]

DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH = os.getenv("DB_PATH", "shop.db")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2

def _get_conn():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_PATH)

def init_db() -> None:
    conn = _get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("CREATE TABLE IF NOT EXISTS balances (user_id BIGINT PRIMARY KEY, balance BIGINT NOT NULL DEFAULT 0)")
        cur.execute("CREATE TABLE IF NOT EXISTS reminder_chats (chat_id BIGINT PRIMARY KEY)")
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS balances (user_id INTEGER PRIMARY KEY, balance INTEGER NOT NULL DEFAULT 0)")
        cur.execute("CREATE TABLE IF NOT EXISTS reminder_chats (chat_id INTEGER PRIMARY KEY)")
        cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.commit()
    cur.close()
    conn.close()

def get_balance(user_id: int) -> int:
    conn = _get_conn()
    placeholder = "%s" if USE_POSTGRES else "?"
    cur = conn.cursor()
    cur.execute(f"SELECT balance FROM balances WHERE user_id = {placeholder}", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else 0

def enable_reminder_chat(chat_id: int) -> None:
    conn = _get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("INSERT INTO reminder_chats (chat_id) VALUES (%s) ON CONFLICT (chat_id) DO NOTHING", (chat_id,))
    else:
        cur.execute("INSERT OR IGNORE INTO reminder_chats (chat_id) VALUES (?)", (chat_id,))
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

def add_balance(user_id: int, amount: int) -> None:
    conn = _get_conn()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("INSERT INTO balances (user_id, balance) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET balance = balances.balance + EXCLUDED.balance", (user_id, amount))
    else:
        cur.execute("INSERT INTO balances (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + excluded.balance", (user_id, amount))
    conn.commit()
    cur.close()
    conn.close()

NFT_SETTING_KEY = "nft_enabled"

def get_nft_enabled() -> bool:
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
        cur.execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (NFT_SETTING_KEY, value))
    else:
        cur.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (NFT_SETTING_KEY, value))
    conn.commit()
    cur.close()
    conn.close()
    _nft_enabled_cache = enabled

router = Router()
active_games: dict[str, dict] = {}
reminder_tasks: dict[int, asyncio.Task] = {}

def custom_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'

def sevens_text() -> str:
    return custom_emoji(EMOJI_SEVEN, "7️⃣") * 3

def mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'

def admins_line() -> str:
    return " ".join(f"@{u}" for u in ADMIN_USERNAMES)

def build_reminder_text() -> str:
    star = custom_emoji(EMOJI_STAR_JACKPOT, "⭐️")
    return (
        f"{custom_emoji(EMOJI_R_SLOT, '🎰')}ИГРАЙ И ЗАБИРАЙ {star} ВСЕГО ЗА 1{custom_emoji(EMOJI_STAR_HEADER, '🌟')}

"
        f"{custom_emoji(EMOJI_R_TROPHY, '🏆')} ДЖЕКПОТ ЧАТА: смотри @Mentalludo_Bot

"
        f"{custom_emoji(EMOJI_R_CHART, '📈')} ПРАВИЛА ЛЕСЕНКИ:

"
        f"{custom_emoji(EMOJI_R_SLOT, '🎰')} Выбил {sevens_text()}: 15 {star} ➔ 40 {star} ➔ 75 {star} ➔ 100{star}

"
        f"{custom_emoji(EMOJI_STAR_HEADER, '🌟')} КАК ИГРАТЬ:

"
        f"{custom_emoji(EMOJI_R_SLOT, '🎰')} Выбил {sevens_text()} — получаешь шанс начать лесенку с 15 {star}

"
        f"🎳 На каждом этапе решай сам:
"
        f"{custom_emoji(EMOJI_R_GIFT, '🎁')} Забрать награду или {custom_emoji(EMOJI_R_TARGET, '🎯')} Испытать удачу!

"
        f"{custom_emoji(EMOJI_R_WARNING, '⚠️')} Не повезёт — награда сгорает {custom_emoji(EMOJI_R_FIRE, '🔥')}

"
        f"{custom_emoji(EMOJI_R_TROPHY, '🏆')} Дойдёшь до 100{star} — забирай главный приз!

"
        f"Скоро в лудку добавится NFT{custom_emoji(EMOJI_R_SALUTE, '🫡')}"
    )

async def reminder_loop(bot: Bot, chat_id: int) -> None:
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
        f"{custom_emoji(EMOJI_WAVE, '👋')}Привет! Ты в главном меню {SHOP_BRAND_NAME}
"
        f"{custom_emoji(EMOJI_MENU_MEDAL, '🎖')}Здесь ты можешь переходить к обмену звёзд на крутые призы!

"
        f"<blockquote>{custom_emoji(EMOJI_GAMEPAD, '🎮')} Основной фарм звезд:
"
        f"Залетай в чат @{FARM_CHAT_USERNAME}, выбивай 777 и получай +{SHOP_REWARD_PER_JACKPOT} звёзд!</blockquote>
"
        f"{custom_emoji(EMOJI_MENU_DIAMOND, '💎')} Выбери нужное действие ниже{custom_emoji(EMOJI_POINT_DOWN, '👇')}:"
    )

def build_shop_text(balance: int) -> str:
    lines = [
        f"{custom_emoji(EMOJI_STAR_FACE, '🤩')}Добро пожаловать в Магазин {SHOP_BRAND_NAME}!",
        "<u>Здесь ты можешь обменять свои звёзды на крутые подарки:</u>",
    ]
    item_lines = []
    for item in SHOP_ITEMS:
        star = custom_emoji(EMOJI_STAR_CLAIM, "⭐️")
        line = f"• {item['name']} — {item['price']} {star}"
        item_lines.append(line)
    lines.append("<blockquote>" + "
".join(item_lines) + "</blockquote>")
    lines.append(f"{custom_emoji(EMOJI_COIN, '🪙')} Твой баланс: {balance} звёзд")
    return "
".join(lines)


# ==== КЛАВИАТУРЫ ЧЕРЕЗ INLINEKEYBOARDBUILDER С НОВЫМИ СТИЛЯМИ И ЭМОДЗИ ====

def prize_keyboard(game_id: str, level: int) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    ladder = get_prize_ladder()
    prize = ladder[level]
    
    # Кнопка "Забрать приз" зеленая (success) с иконкой подарка
    builder.add(types.InlineKeyboardButton(
        text=f"Забрать {prize['label']}",
        callback_data=f"claim:{game_id}",
        style="success",
        icon_custom_emoji_id=EMOJI_BTN_CLAIM
    ))
    
    # Кнопка "Испытать удачу" синяя (primary) с иконкой алмаза
    if level < len(ladder) - 1:
        builder.add(types.InlineKeyboardButton(
            text="Испытать удачу",
            callback_data=f"risk:{game_id}",
            style="primary",
            icon_custom_emoji_id=EMOJI_BTN_RISK
        ))
        
    return builder.as_markup()


def range_keyboard(game_id: str, level: int) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    options = get_range_options(level)
    
    # Кнопки выбора диапазонов синие (primary) с иконкой звездочки
    for lo, hi in options:
        builder.add(types.InlineKeyboardButton(
            text=f"{lo}-{hi}",
            callback_data=f"range:{game_id}:{lo}:{hi}",
            style="primary",
            icon_custom_emoji_id=EMOJI_STAR_HEADER
        ))
        
    return builder.as_markup()


def main_menu_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Кнопка магазина фиолетово-синяя (primary) со своей иконкой
    builder.add(types.InlineKeyboardButton(
        text="Магазин",
        callback_data="menu:shop",
        style="primary",
        icon_custom_emoji_id=EMOJI_BTN_SHOP
    ))
    return builder.as_markup()


def shop_keyboard() -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # Кнопки товаров по умолчанию серые (default), иконка соответствует товару
    for item in SHOP_ITEMS:
        builder.row(types.InlineKeyboardButton(
            text=f"{item['name']} — {item['price']}⭐",
            callback_data=f"buy:{item['id']}",
            style="default",
            icon_custom_emoji_id=item["emoji_id"]
        ))
        
    # Кнопка назад красная (danger) с иконкой предупреждения/назад
    builder.row(types.InlineKeyboardButton(
        text="Назад",
        callback_data="menu:back",
        style="danger",
        icon_custom_emoji_id=EMOJI_BTN_BACK
    ))
    return builder.as_markup()


# ==== ХЭНДЛЕРЫ И ОСТАЛЬНАЯ ЛОГИКА БОТА ====

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(build_main_menu_text(), reply_markup=main_menu_keyboard())

@router.message(Command("promo_on"))
async def cmd_promo_on(message: Message) -> None:
    chat_id = message.chat.id
    if chat_id in reminder_tasks:
        await message.reply("Напоминание уже запущено в этом чате ✅")
        return
    enable_reminder_chat(chat_id)
    start_reminder(message.bot, chat_id)
    minutes = REMINDER_INTERVAL_SECONDS // 60
    await message.reply(f"✅ Напоминание запущено — каждые {minutes} мин.")

@router.message(Command("promo_off"))
async def cmd_promo_off(message: Message) -> None:
    chat_id = message.chat.id
    if chat_id not in reminder_tasks:
        await message.reply("В этом чате напоминание и так не запущено.")
        return
    stop_reminder(chat_id)
    disable_reminder_chat(chat_id)
    await message.reply("🛑 Напоминание остановлено.")

def is_admin(username: str | None) -> bool:
    return username is not None and username in ADMIN_USERNAMES

@router.message(Command("nft_off"))
async def cmd_nft_off(message: Message) -> None:
    if not is_admin(message.from_user.username):
        await message.reply("Эта команда доступна только админам.")
        return
    if not get_nft_enabled():
        await message.reply("Режим NFT и так выключен.")
        return
    set_nft_enabled(False)
    await message.reply(f"🛑 Режим NFT выключен. Теперь верхний уровень выдаёт {FALLBACK_TOP_PRIZE['label']}.")

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

@router.callback_query(F.data == "menu:back")
async def handle_menu_back(callback: CallbackQuery) -> None:
    await callback.message.edit_text(build_main_menu_text(), reply_markup=main_menu_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("buy:"))
async def handle_buy(callback: CallbackQuery) -> None:
    await callback.answer("Покупка скоро будет доступна 🙂", show_alert=True)

@router.message(F.dice.emoji == "🎰")
async def handle_slot_machine(message: Message) -> None:
    dice_value = message.dice.value
    if dice_value != SLOT_JACKPOT_VALUE:
        return
    user = message.from_user
    add_balance(user.id, SHOP_REWARD_PER_JACKPOT)
    game_id = uuid.uuid4().hex[:12]
    active_games[game_id] = {
        "user_id": user.id,
        "level": 0,
        "chat_id": message.chat.id,
        "last_message_id": None,
    }
    prize = get_prize_ladder()[0]
    text = (
        f"{custom_emoji(EMOJI_PARTY_JACKPOT, '🎉')} Поздравляем {mention(user.id, user.full_name)}, вы выиграли!

"
        f"Джекпот {sevens_text()}!

"
        f"Текущая награда: подарок {prize['value']}{custom_emoji(EMOJI_STAR_JACKPOT, '⭐️')}

"
        f"{custom_emoji(EMOJI_BEAR, '🧸')}Выберите действие{custom_emoji(EMOJI_CHECK, '✅')}"
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
        text = f"🎊 Поздравляем, {mention(user.id, user.full_name)}! Ты выиграл NFT!

🎁 {reward_url}

За выдачей пишите: {admins_line()}"
    else:
        text = f"{custom_emoji(EMOJI_PARTY_CLAIM, '🎉')} Поздравляем, {mention(user.id, user.full_name)}! Вы забрали {prize['value']}{custom_emoji(EMOJI_STAR_CLAIM, '⭐️')}!"
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
        f"{custom_emoji(EMOJI_BOWLING, '🎳')} Выберите диапазон кеглей{custom_emoji(EMOJI_STAR_HEADER, '🌟')}

"
        f"{custom_emoji(EMOJI_FIRE, '🔥')}Если результат попадет в диапазон — награда выше, иначе — сгорает{custom_emoji(EMOJI_FIRE, '🔥')}"
    )
    await callback.message.edit_text(text, reply_markup=range_keyboard(game_id, game["level"]))
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
    await callback.message.edit_reply_markup(reply_markup=None)
    dice_message = await callback.bot.send_dice(chat_id=game["chat_id"], emoji="🎳", reply_to_message_id=game["last_message_id"])
    game["last_message_id"] = dice_message.message_id
    await asyncio.sleep(4)
    pins = dice_message.dice.value
    user = callback.from_user
    if lo <= pins <= hi:
        game["level"] += 1
        prize = get_prize_ladder()[game["level"]]
        text = f"🎳 Выпало: {pins}

{custom_emoji(EMOJI_STAR_HEADER, '🌟')}Награда прокачена!

Текущая награда: подарок {prize['value']}{custom_emoji(EMOJI_STAR_CLAIM, '⭐️')}

"
        if prize["is_nft"]:
            text += "Это максимальный приз — заберите его!"
        else:
            text += f"Испытать удачу или забрать приз?{custom_emoji(EMOJI_MEDAL, '🎖')}
За выдачей пишите: {admins_line()}{custom_emoji(EMOJI_SPARKLES, '💫')}"
        result_message = await callback.message.answer(text, reply_markup=prize_keyboard(game_id, game["level"]), reply_to_message_id=game["last_message_id"])
        game["last_message_id"] = result_message.message_id
    else:
        await callback.message.answer(f"🎳 Выпало: {pins}

{custom_emoji(EMOJI_CRY, '😭')}Увы, сгорело!

{custom_emoji(EMOJI_STAR_RETRY, '⭐')}Попробуйте ещё раз{custom_emoji(EMOJI_SMILE, '😃')}", reply_to_message_id=game["last_message_id"])
        del active_games[game_id]

async def main() -> None:
    init_db()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    for chat_id in get_reminder_chats():
        start_reminder(bot, chat_id)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

