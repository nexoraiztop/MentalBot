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
import uuid

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
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

# ID премиум-эмодзи (семёрка)
SEVEN_EMOJI_ID = "5364243419164064459"

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

# Утешительный приз при проигрыше в мини-игре
CONSOLATION_LABEL = "5⭐"

# Диапазоны для мини-игры с боулингом (🎳 даёт число от 1 до 6)
RANGE_OPTIONS = [(1, 3), (4, 6)]

router = Router()

# Активные игры: game_id -> {"user_id", "level", "chat_id"}
active_games: dict[str, dict] = {}


def custom_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def sevens_text() -> str:
    return custom_emoji(SEVEN_EMOJI_ID, "7️⃣") * 3


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


def range_keyboard(game_id: str) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=f"{lo}-{hi}", callback_data=f"range:{game_id}:{lo}:{hi}"
        )
        for lo, hi in RANGE_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


@router.message(F.dice.emoji == "🎰")
async def handle_slot_machine(message: Message) -> None:
    # Пересланные сообщения (в том числе с чужим настоящим броском) игнорируем —
    # реагируем только на бросок, сделанный прямо в этом чате.
    if message.forward_origin is not None:
        return

    dice_value = message.dice.value
    if dice_value != SLOT_JACKPOT_VALUE:
        return

    user = message.from_user
    game_id = uuid.uuid4().hex[:12]
    active_games[game_id] = {
        "user_id": user.id,
        "level": 0,
        "chat_id": message.chat.id,
    }

    prize = PRIZE_LADDER[0]
    text = (
        f"🎉 Поздравляем {mention(user.id, user.full_name)}, вы выиграли!\n\n"
        f"Джекпот {sevens_text()}!\n\n"
        f"Текущая награда: подарок {prize['label']}\n\n"
        f"Выберите: хотите забрать подарок, или испытать удачу, "
        f"чтобы получить награду получше?"
    )
    await message.reply(text, reply_markup=prize_keyboard(game_id, 0))


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
            f"🎉 Поздравляем, {mention(user.id, user.full_name)}! "
            f"Вы забрали {prize['label']}!\n\n"
            f"За выдачей пишите: {admins_line()}"
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
        "🎳 Выберите диапазон кеглей\n\n"
        "⚠️ Если выпадет число из выбранного вами диапазона — награда "
        "повышается, если не выпадет — ваша награда сгорает."
    )
    await callback.message.edit_text(text, reply_markup=range_keyboard(game_id))
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

    # Бот сам бросает боулинг-шар и получает результат прямо из ответа Telegram
    dice_message = await callback.bot.send_dice(
        chat_id=game["chat_id"], emoji="🎳"
    )
    # Небольшая пауза, чтобы анимация броска успела доиграть у пользователя
    await asyncio.sleep(4)
    pins = dice_message.dice.value  # число от 1 до 6

    user = callback.from_user

    if lo <= pins <= hi:
        game["level"] += 1
        prize = PRIZE_LADDER[game["level"]]
        text = (
            f"🎳 Выпало: {pins}\n\n"
            f"✨ Поздравляем, ваша награда прокачена!\n\n"
            f"Текущая награда: подарок {prize['label']}\n\n"
        )
        if prize["is_nft"]:
            text += "Это максимальный приз — заберите его прямо сейчас!"
        else:
            text += "Хотите испытать удачу ещё, или забрать приз?"

        await callback.message.answer(
            text, reply_markup=prize_keyboard(game_id, game["level"])
        )
    else:
        del active_games[game_id]
        text = (
            f"🎳 Выпало: {pins}\n\n"
            f"😔 Увы, не повезло! Ваша награда сгорела.\n\n"
            f"Но вы получаете утешительный приз: {CONSOLATION_LABEL}\n\n"
            f"За выдачей пишите: {admins_line()}"
        )
        await callback.message.answer(text)


async def main() -> None:
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
