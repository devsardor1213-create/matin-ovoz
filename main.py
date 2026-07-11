import asyncio
import logging
import os
import sqlite3
import subprocess
import edge_tts

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# -------------------------
# Config
# -------------------------
TOKEN = "8321889290:AAETN88DoI2fG4qMQwS3dsH9EBL1aiiWU0I"
ADMIN_ID = 7752032178 # Asosiy admin
ADMIN_LOGIN = "ceo_admin"
ADMIN_PASS = "MatinOvoz!2026"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# -------------------------
# Database Setup
# -------------------------
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    # Ensure tables exist
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        voice TEXT DEFAULT 'voice_male',
        lang TEXT DEFAULT 'uz',
        speed TEXT DEFAULT '+0%',
        conversions INTEGER DEFAULT 0
    )''')
    
    # Try adding new columns if they don't exist (for migration)
    try:
        c.execute("ALTER TABLE users ADD COLUMN speed TEXT DEFAULT '+0%'")
        c.execute("ALTER TABLE users ADD COLUMN conversions INTEGER DEFAULT 0")
    except:
        pass

    c.execute('''CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT,
        url TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS active_admins (
        id INTEGER PRIMARY KEY
    )''')
    conn.commit()
    conn.close()

init_db()

# DB Helper functions
def get_channels():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT channel_id, url FROM channels")
    rows = c.fetchall()
    conn.close()
    return rows

def add_channel(channel_id, url):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO channels (channel_id, url) VALUES (?, ?)", (channel_id, url))
    conn.commit()
    conn.close()

def remove_channel(channel_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
        return True # New user
    conn.close()
    return False

def update_user_setting(user_id, key, value):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute(f"UPDATE users SET {key} = ? WHERE id = ?", (value, user_id))
    conn.commit()
    conn.close()

def get_user_settings(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT voice, lang, speed, conversions FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"voice": row[0], "lang": row[1], "speed": row[2], "conversions": row[3]}
    return {"voice": "voice_male", "lang": "uz", "speed": "+0%", "conversions": 0}

def increment_conversion(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("UPDATE users SET conversions = conversions + 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT id FROM active_admins WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return bool(row)

def add_admin_db(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO active_admins (id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# -------------------------
# States
# -------------------------
class AdminLoginStates(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_channel_id = State()
    waiting_for_channel_url = State()

class UserStates(StatesGroup):
    waiting_for_feedback = State()

# -------------------------
# Keyboards
# -------------------------
def user_main_menu():
    kb = [
        [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="👤 Kabinet")],
        [KeyboardButton(text="✉️ Adminga murojaat"), KeyboardButton(text="🚀 Ovoz tezligi")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# -------------------------
# Check Subs Logic
# -------------------------
async def check_all_subscriptions(user_id: int) -> bool:
    if is_admin(user_id):
        return True
    channels = get_channels()
    if not channels:
        return True
    
    for ch_id, url in channels:
        try:
            member = await bot.get_chat_member(ch_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

async def get_subs_keyboard():
    kb = InlineKeyboardBuilder()
    channels = get_channels()
    for idx, (ch_id, url) in enumerate(channels, 1):
        kb.button(text=f"✅ {idx}-Kanalga qo‘shilish", url=url)
    if channels:
        kb.button(text="♻️ Tekshirish", callback_data="check_subs")
        kb.adjust(1)
    return kb.as_markup()

# -------------------------
# Admin Login & Panel
# -------------------------
@dp.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    if is_admin(message.from_user.id):
        await show_admin_panel(message, state)
    else:
        await message.answer("🔐 Admin panelga kirish uchun loginingizni kiriting:")
        await state.set_state(AdminLoginStates.waiting_for_login)

@dp.message(AdminLoginStates.waiting_for_login)
async def process_admin_login(message: Message, state: FSMContext):
    if message.text == ADMIN_LOGIN:
        await message.answer("🔑 Parolni kiriting:")
        await state.set_state(AdminLoginStates.waiting_for_password)
    else:
        await message.answer("❌ Noto'g'ri login. Qaytadan /admin buyrug'ini bosing.")
        await state.clear()

@dp.message(AdminLoginStates.waiting_for_password)
async def process_admin_password(message: Message, state: FSMContext):
    if message.text == ADMIN_PASS:
        add_admin_db(message.from_user.id)
        await message.answer("✅ Muvaffaqiyatli kirdingiz!")
        await show_admin_panel(message, state)
    else:
        await message.answer("❌ Noto'g'ri parol. Qaytadan /admin buyrug'ini bosing.")
        await state.clear()

async def show_admin_panel(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Foydalanuvchilar soni", callback_data="admin_stats")
    kb.button(text="📢 Reklama tarqatish", callback_data="admin_broadcast")
    kb.button(text="➕ Kanal qo'shish", callback_data="admin_add_channel")
    kb.button(text="➖ Kanal o'chirish", callback_data="admin_del_channel")
    kb.adjust(1)
    await message.answer("🛠 <b>Maxfiy Admin panelga xush kelibsiz!</b>\nO'zingizga kerakli bo'limni tanlang:", parse_mode="HTML", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    action = callback.data.split("_", 1)[1]
    
    if action == "stats":
        users = get_all_users()
        await callback.message.answer(f"📊 Jami foydalanuvchilar: {len(users)} ta")
        await callback.answer()
        
    elif action == "broadcast":
        await callback.message.answer("📢 Yubormoqchi bo'lgan xabaringizni yuboring:")
        await state.set_state(AdminStates.waiting_for_broadcast)
        await callback.answer()
        
    elif action == "add_channel":
        await callback.message.answer("➕ Yangi kanal ID sini yoki Username ini yuboring (masalan: @sardorixcoder yoki -10012345678):")
        await state.set_state(AdminStates.waiting_for_channel_id)
        await callback.answer()
        
    elif action == "del_channel":
        channels = get_channels()
        if not channels:
            await callback.message.answer("🗑 Kanallar ro'yxati bo'sh.")
            return await callback.answer()
        
        kb = InlineKeyboardBuilder()
        for ch_id, url in channels:
            kb.button(text=f"❌ {ch_id}", callback_data=f"delch_{ch_id}")
        kb.adjust(1)
        await callback.message.answer("O'chirmoqchi bo'lgan kanalni tanlang:", reply_markup=kb.as_markup())
        await callback.answer()

@dp.callback_query(F.data.startswith("delch_"))
async def del_channel_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    ch_id = callback.data.split("_", 1)[1]
    remove_channel(ch_id)
    await callback.message.edit_text(f"✅ Kanal {ch_id} o'chirildi.")

@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    users = get_all_users()
    sent = 0
    await message.answer(f"⏳ Xabar {len(users)} ta foydalanuvchiga yuborilmoqda...")
    for user in users:
        try:
            await message.copy_to(user)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.answer(f"✅ Xabar {sent} ta foydalanuvchiga muvaffaqiyatli yuborildi.")
    await state.clear()

@dp.message(AdminStates.waiting_for_channel_id)
async def process_add_channel_id(message: Message, state: FSMContext):
    await state.update_data(ch_id=message.text)
    await message.answer("🔗 Endi ushbu kanalning taklif havolasini (URL) yuboring:")
    await state.set_state(AdminStates.waiting_for_channel_url)

@dp.message(AdminStates.waiting_for_channel_url)
async def process_add_channel_url(message: Message, state: FSMContext):
    data = await state.get_data()
    ch_id = data['ch_id']
    url = message.text
    add_channel(ch_id, url)
    await message.answer(f"✅ Kanal muvaffaqiyatli qo'shildi:\nID: {ch_id}\nURL: {url}")
    await state.clear()

# -------------------------
# User Features (Profile, Feedback, Speed)
# -------------------------
@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_menu(message: Message):
    if not await check_all_subscriptions(message.from_user.id):
        return await message.answer("❌ Kanalga a’zo bo‘ling:", reply_markup=await get_subs_keyboard())
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🧑 Erkak ovoz", callback_data="voice_male")
    kb.button(text="👩 Ayol ovoz", callback_data="voice_female")
    await message.answer("🛠 Sozlamalar:\nOvoz turini tanlang:", reply_markup=kb.as_markup())

@dp.message(F.text == "🚀 Ovoz tezligi")
async def speed_menu(message: Message):
    if not await check_all_subscriptions(message.from_user.id):
        return await message.answer("❌ Kanalga a’zo bo‘ling:", reply_markup=await get_subs_keyboard())
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🐢 Sekin", callback_data="speed_-20%")
    kb.button(text="▶️ Normal", callback_data="speed_+0%")
    kb.button(text="🐇 Tez", callback_data="speed_+20%")
    kb.button(text="⚡ Juda tez", callback_data="speed_+50%")
    kb.adjust(2)
    await message.answer("🚀 Ovoz o'qilish tezligini tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("speed_"))
async def choose_speed(callback: CallbackQuery):
    speed = callback.data.split("_")[1]
    update_user_setting(callback.from_user.id, "speed", speed)
    await callback.message.edit_text(f"✅ Ovoz tezligi saqlandi: {speed}")

@dp.message(F.text == "👤 Kabinet")
async def profile_menu(message: Message):
    if not await check_all_subscriptions(message.from_user.id):
        return await message.answer("❌ Kanalga a’zo bo‘ling:", reply_markup=await get_subs_keyboard())
    
    settings = get_user_settings(message.from_user.id)
    voice_type = "🧑 Erkak" if settings['voice'] == "voice_male" else "👩 Ayol"
    lang_type = settings['lang'].upper()
    
    text = f"👤 <b>Sizning shaxsiy kabinetingiz</b>\n\n"
    text += f"🆔 ID: <code>{message.from_user.id}</code>\n"
    text += f"🗣 Ovoz turi: {voice_type}\n"
    text += f"🌐 Til: {lang_type}\n"
    text += f"🚀 Ovoz tezligi: {settings['speed']}\n"
    text += f"📈 Jami aylantirilgan matnlar: <b>{settings['conversions']}</b> ta\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "✉️ Adminga murojaat")
async def feedback_menu(message: Message, state: FSMContext):
    if not await check_all_subscriptions(message.from_user.id):
        return await message.answer("❌ Kanalga a’zo bo‘ling:", reply_markup=await get_subs_keyboard())
    
    await message.answer("✍️ Adminga o'z taklif, shikoyat yoki savolingizni yozib yuboring.\nAdmin lichkasi: https://t.me/sardorixcoderr\n\n(Bekor qilish uchun /cancel bosing)", disable_web_page_preview=True)
    await state.set_state(UserStates.waiting_for_feedback)

@dp.message(Command("cancel"), UserStates.waiting_for_feedback)
async def cancel_feedback(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=user_main_menu())

@dp.message(UserStates.waiting_for_feedback)
async def send_feedback(message: Message, state: FSMContext):
    await bot.send_message(
        ADMIN_ID,
        f"📩 <b>Yangi Murojaat:</b>\n\n👤 ID: {message.from_user.id}\nIsm: {message.from_user.full_name}\n💬 Xabar: {message.text}",
        parse_mode="HTML"
    )
    await message.answer("✅ Xabaringiz adminga yetkazildi. Rahmat!", reply_markup=user_main_menu())
    await state.clear()


# -------------------------
# User Handlers
# -------------------------
@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    is_new = add_user(message.from_user.id)
    if is_new:
        await bot.send_message(ADMIN_ID, f"🆕 Yangi foydalanuvchi!\nID: {message.from_user.id}\nIsm: {message.from_user.full_name}")

    if not await check_all_subscriptions(message.from_user.id):
        markup = await get_subs_keyboard()
        await message.answer(
            "❌ Botdan foydalanish uchun quyidagi kanallarga a’zo bo‘ling:",
            reply_markup=markup
        )
        return

    await message.answer("👋 Salom! Matnni ovozga aylantiruvchi botga xush kelibsiz.\nMarhamat, menyudan foydalaning yoki to'g'ridan-to'g'ri matn yuboring:", reply_markup=user_main_menu())

@dp.callback_query(F.data == "check_subs")
async def check_subs(callback: CallbackQuery):
    if not await check_all_subscriptions(callback.from_user.id):
        await callback.answer("❌ Hali kanallarga a’zo emassiz!", show_alert=True)
    else:
        await callback.message.delete()
        await callback.message.answer("✅ A’zo bo‘ldingiz!\nMarhamat, menyudan foydalaning yoki matn yuboring:", reply_markup=user_main_menu())

@dp.callback_query(F.data.in_(["voice_male", "voice_female"]))
async def choose_voice(callback: CallbackQuery):
    if not await check_all_subscriptions(callback.from_user.id):
        await callback.answer("❌ Botdan foydalanish uchun kanalga a’zo bo‘ling!", show_alert=True)
        return

    update_user_setting(callback.from_user.id, "voice", callback.data)

    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 Uzbek", callback_data="lang_uz")
    kb.button(text="🇷🇺 Rus", callback_data="lang_ru")
    kb.button(text="🇬🇧 Ingliz", callback_data="lang_en")

    await callback.message.edit_text("✅ Ovoz turi tanlandi.\nEndi tilni tanlang:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("lang_"))
async def choose_lang(callback: CallbackQuery):
    if not await check_all_subscriptions(callback.from_user.id):
        await callback.answer("❌ Botdan foydalanish uchun kanalga a’zo bo‘ling!", show_alert=True)
        return

    lang = callback.data.split("_")[1]
    update_user_setting(callback.from_user.id, "lang", lang)
    await callback.message.edit_text("✅ Til tanlandi.\n\n🎙 Matn yuborsangiz, uni darhol ovozga aylantirib beraman.")

# -------------------------
# Helper: MP3 → OGG (OPUS) converter for Telegram Voice Message
# -------------------------
def convert_mp3_to_ogg(mp3_path: str, ogg_path: str) -> bool:
    """Convert MP3/WAV to OGG OPUS format required by Telegram Voice Message."""
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", mp3_path,
                "-c:a", "libopus",
                "-b:a", "64k",
                "-vbr", "on",
                "-compression_level", "10",
                "-application", "voip",
                ogg_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result.returncode == 0
    except FileNotFoundError:
        logging.error("ffmpeg topilmadi! ffmpeg o'rnatilganligini tekshiring.")
        return False
    except Exception as e:
        logging.error(f"OGG konvertatsiyada xatolik: {e}")
        return False

# -------------------------
# TTS: Text to Speech
# -------------------------
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message):
    if not await check_all_subscriptions(message.from_user.id):
        markup = await get_subs_keyboard()
        await message.answer("❌ Botdan foydalanish uchun kanalga a’zo bo‘ling:", reply_markup=markup)
        return

    add_user(message.from_user.id)
    settings = get_user_settings(message.from_user.id)
    voice = settings["voice"]
    lang = settings["lang"]
    speed = settings["speed"]

    voice_map = {
        ("voice_male", "uz"): "uz-UZ-SardorNeural",
        ("voice_female", "uz"): "uz-UZ-MadinaNeural",
        ("voice_male", "ru"): "ru-RU-DmitryNeural",
        ("voice_female", "ru"): "ru-RU-SvetlanaNeural",
        ("voice_male", "en"): "en-US-GuyNeural",
        ("voice_female", "en"): "en-US-JennyNeural",
    }
    tts_voice = voice_map.get((voice, lang), "uz-UZ-SardorNeural")

    mp3_filename = f"{message.from_user.id}_tts.mp3"
    ogg_filename = f"{message.from_user.id}_tts.ogg"
    wait_msg = await message.answer("⏳ Ovoz tayyorlanmoqda, kuting...")
    try:
        # 1. TTS orqali MP3 hosil qilamiz
        communicate = edge_tts.Communicate(message.text, tts_voice, rate=speed)
        await communicate.save(mp3_filename)

        # 2. MP3 → OGG (OPUS) konvertatsiya (Telegram Voice Message standarti)
        converted = convert_mp3_to_ogg(mp3_filename, ogg_filename)
        voice_file = ogg_filename if converted and os.path.exists(ogg_filename) else mp3_filename

        # 3. Foydalanuvchiga sendVoice orqali Telegram Voice Message yuboramiz
        await message.answer_voice(
            voice=types.FSInputFile(voice_file),
            caption="✅ Tayyor ovoz \n\n🤖 @matinovozchat_bot"
        )
        # Update user conversions stats
        increment_conversion(message.from_user.id)

        # 4. Ovozli xabarni adminga ham yuborish
        admin_text = (
            f"🔊 <b>Foydalanuvchi matnni ovozga aylantirdi!</b>\n\n"
            f"👤 <b>Foydalanuvchi:</b> <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a> (<code>{message.from_user.id}</code>)\n"
            f"🌐 <b>Til / Ovoz:</b> {lang.upper()} / {'🧑 Erkak' if voice == 'voice_male' else '👩 Ayol'}\n"
            f"💬 <b>Matn:</b>\n{message.text}"
        )
        try:
            await bot.send_voice(
                ADMIN_ID,
                voice=types.FSInputFile(voice_file),
                caption=admin_text,
                parse_mode="HTML"
            )
        except Exception as admin_err:
            logging.error(f"Adminga yuborishda xatolik: {admin_err}")

    except Exception as e:
        await message.answer("❌ Xatolik yuz berdi. Iltimos qayta urinib ko'ring yoki matnni qisqartiring.")
        logging.error(f"TTS Error: {e}")
    finally:
        await wait_msg.delete()
        if os.path.exists(mp3_filename):
            os.remove(mp3_filename)
        if os.path.exists(ogg_filename):
            os.remove(ogg_filename)

# -------------------------
# Run
# -------------------------
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
