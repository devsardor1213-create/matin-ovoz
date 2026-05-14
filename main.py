# main.py
# aiogram==3.22.0
# Kutubxonalar: pip install aiogram==3.22.0 edge-tts

import asyncio
import logging
import os
import edge_tts
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

# -------------------------
# Config
# -------------------------
TOKEN = "8321889290:AAETN88DoI2fG4qMQwS3dsH9EBL1aiiWU0I"
CHANNEL_ID = "@sardorixcoder"
ADMIN_ID = 7752032178

bot = Bot(token=TOKEN)
dp = Dispatcher()

# -------------------------
# State saqlash uchun oddiy dict
# -------------------------
user_settings = {}

# -------------------------
# Kanalga a'zo ekanligini tekshirish
# -------------------------
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# -------------------------
# Start komandasi
# -------------------------
@dp.message(CommandStart())
async def start_cmd(message: Message):
    if not await check_subscription(message.from_user.id):
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Kanalga qo‘shilish", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")
        kb.button(text="♻️ Tekshirish", callback_data="check_subs")
        await message.answer(
            "❌ Botdan foydalanish uchun kanalga a’zo bo‘ling:\n👉 https://t.me/sardorixcoder",
            reply_markup=kb.as_markup()
        )
        return

    # Ovoz tanlash
    kb = InlineKeyboardBuilder()
    kb.button(text="🧑 Erkak ovoz", callback_data="voice_male")
    kb.button(text="👩 Ayol ovoz", callback_data="voice_female")
    await message.answer("👋 Salom! Avval ovoz turini tanlang:", reply_markup=kb.as_markup())

# -------------------------
# Tekshirish tugmasi
# -------------------------
@dp.callback_query(F.data == "check_subs")
async def check_subs(callback: CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.answer("❌ Hali kanalga a’zo emassiz!", show_alert=True)
    else:
        await callback.message.delete()
        kb = InlineKeyboardBuilder()
        kb.button(text="🧑 Erkak ovoz", callback_data="voice_male")
        kb.button(text="👩 Ayol ovoz", callback_data="voice_female")
        await callback.message.answer("✅ A’zo bo‘ldingiz!\nEndi ovoz turini tanlang:", reply_markup=kb.as_markup())

# -------------------------
# Ovoz tanlash
# -------------------------
@dp.callback_query(F.data.in_(["voice_male", "voice_female"]))
async def choose_voice(callback: CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.answer("❌ Botdan foydalanish uchun kanalga a’zo bo‘ling!", show_alert=True)
        return

    user_settings[callback.from_user.id] = {"voice": callback.data}

    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 Uzbek", callback_data="lang_uz")
    kb.button(text="🇷🇺 Rus", callback_data="lang_ru")
    kb.button(text="🇬🇧 Ingliz", callback_data="lang_en")

    await callback.message.edit_text("✅ Ovoz turi tanlandi.\nEndi tilni tanlang:", reply_markup=kb.as_markup())

# -------------------------
# Til tanlash
# -------------------------
@dp.callback_query(F.data.startswith("lang_"))
async def choose_lang(callback: CallbackQuery):
    if not await check_subscription(callback.from_user.id):
        await callback.answer("❌ Botdan foydalanish uchun kanalga a’zo bo‘ling!", show_alert=True)
        return

    lang = callback.data.split("_")[1]
    user_settings[callback.from_user.id]["lang"] = lang
    await callback.message.edit_text("✅ Til tanlandi.\nIltimos, endi matningizni yuboring.")

# -------------------------
# Matn qabul qilish va ovozga aylantirish
# -------------------------
@dp.message(F.text)
async def handle_text(message: Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("❌ Botdan foydalanish uchun kanalga a’zo bo‘ling:\n👉 https://t.me/Tech_communityy")
        return

    if message.from_user.id not in user_settings or "lang" not in user_settings[message.from_user.id]:
        await message.answer("⚠️ Avval /start ni bosing va ovoz + til tanlang.")
        return

    settings = user_settings[message.from_user.id]
    voice = settings["voice"]
    lang = settings["lang"]

    # edge-tts ovoz mapping
    voice_map = {
        ("voice_male", "uz"): "uz-UZ-SardorNeural",
        ("voice_female", "uz"): "uz-UZ-MadinaNeural",
        ("voice_male", "ru"): "ru-RU-DmitryNeural",
        ("voice_female", "ru"): "ru-RU-SvetlanaNeural",
        ("voice_male", "en"): "en-US-GuyNeural",
        ("voice_female", "en"): "en-US-JennyNeural",
    }

    tts_voice = voice_map.get((voice, lang), "en-US-GuyNeural")

    # Fayl yaratish
    filename = f"{message.from_user.id}.mp3"
    communicate = edge_tts.Communicate(message.text, tts_voice)
    await communicate.save(filename)

    # Foydalanuvchiga yuborish
    await message.answer_voice(
        voice=types.FSInputFile(filename),
        caption="✅ Tayyor ovoz \n\nYana qayta ishlatish uchun /start bosing!"
    )

    # Admin ga yuborish
    await bot.send_message(
        ADMIN_ID,
        f"📩 Yangi foydalanuvchi xabari:\n\n👤 ID: {message.from_user.id}\n💬 Matn: {message.text}"
    )
    await bot.send_voice(ADMIN_ID, voice=types.FSInputFile(filename))

    # Fayl o‘chirish
    os.remove(filename)

# -------------------------
# Run
# -------------------------
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
