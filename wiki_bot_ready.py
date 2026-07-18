import asyncio
import logging
import os

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ============ SOZLAMALAR ============
BOT_TOKEN = "8813619450:AAGj5mZUMEJDCNcA_bkjMtqePQe2TMioAlI"
# =====================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_lang = {}

LANGUAGES = {
    "uz": {"name": "O'zbekcha", "wiki_code": "uz"},
    "ru": {"name": "Русский", "wiki_code": "ru"},
    "en": {"name": "English", "wiki_code": "en"},
}

DEFAULT_LANG = "uz"


def lang_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=info["name"], callback_data=f"setlang_{code}")]
        for code, info in LANGUAGES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Salom! Men Wikipedia qidiruv botiman\n\n"
        "Menga istalgan so'z yoki ibora yuboring, men Wikipedia'dan qisqacha "
        "ma'lumot va havola topib beraman.\n\n"
        "Tilni o'zgartirish uchun /til buyrug'ini bosing."
    )


@dp.message(Command("til"))
async def cmd_lang(message: Message):
    await message.answer("Qidiruv tilini tanlang:", reply_markup=lang_keyboard())


@dp.callback_query(F.data.startswith("setlang_"))
async def set_lang(callback):
    code = callback.data.split("_")[1]
    user_lang[callback.from_user.id] = code
    await callback.message.edit_text(
        f"Til o'rnatildi: {LANGUAGES[code]['name']}\n\nEndi qidirmoqchi bo'lgan so'zni yuboring."
    )
    await callback.answer()


HEADERS = {
    "User-Agent": "WikiBot/1.0"
}


async def search_wikipedia(query: str, lang_code: str) -> dict | None:
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        search_url = f"https://{lang_code}.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        }
        async with session.get(search_url, params=params) as resp:
            data = await resp.json()
            results = data.get("query", {}).get("search", [])
            if not results:
                return None
            title = results[0]["title"]

        summary_url = f"https://{lang_code}.wikipedia.org/api/rest_v1/page/summary/{title}"
        async with session.get(summary_url) as resp:
            if resp.status != 200:
                return None
            summary_data = await resp.json()
            return {
                "title": summary_data.get("title", title),
                "extract": summary_data.get("extract", ""),
                "url": summary_data.get("content_urls", {})
                .get("desktop", {})
                .get("page", f"https://{lang_code}.wikipedia.org/wiki/{title}"),
            }


@dp.message(F.text)
async def handle_query(message: Message):
    query = message.text.strip()
    if not query:
        return

    lang_code = user_lang.get(message.from_user.id, DEFAULT_LANG)

    await bot.send_chat_action(message.chat.id, "typing")
    result = await search_wikipedia(query, lang_code)

    if result is None:
        await message.answer(
            f"'{query}' bo'yicha hech narsa topilmadi"
        )
        return

    text = f"<b>{result['title']}</b>\n\n{result['extract']}\n\nHavola: {result['url']}"
    await message.answer(text, parse_mode="HTML")


async def main():
    print("Bot ishga tushmoqda...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
