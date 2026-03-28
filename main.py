import asyncio
import logging
import sqlite3
import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# =========================
# KONFIGURATSIYA
# =========================
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# =========================
# TILLAR MATNLARI
# =========================
TEXTS = {
    'uz': {
        'welcome': "Xush kelibsiz! Tilni tanlang / Қош келдіңіз! Тілді таңдаңыз:",
        'main_menu': "Asosiy menyu:",
        'courses': "📚 Kurslar",
        'reg': "📝 Ro'yxatdan o'tish",
        'contact': "☎️ Bog'lanish",
        'faq': "❓ Savol-javob",
        'enter_name': "Ism-sharifingizni kiriting:",
        'send_phone': "Telefon raqamingizni yuboring:",
        'phone_btn': "📱 Raqamni yuborish",
        'select_course': "Kursni tanlang:",
        'success_reg': "✅ Siz muvaffaqiyatli ro'yxatdan o'tdingiz! Operator tez orada bog'lanadi.",
        'back': "⬅️ Orqaga",
        'no_courses': "Kurslar hali qo'shilmagan.",
        'contact_us': "Biz bilan bog'lanish: +998935860291 ",
        'faq_ans': "1. Kurslar qachon boshlanadi? - Har oy boshida.\n2. Sertifikat beriladimi? - Ha.",
        'admin_msg': "🔔 YANGI ARIZA:\n👤 Ism: {name}\n📞 Tel: {phone}\n📚 Kurs: {course}"
    },
    'kz': {
        'welcome': "Қош келдіңіз!",
        'main_menu': "Бас мәзір:",
        'courses': "📚 Курстар",
        'reg': "📝 Тіркелу",
        'contact': "☎️ Байланыс",
        'faq': "❓ Сұрақ-жауап",
        'enter_name': "Аты-жөніңізді енгізіңіз:",
        'send_phone': "Телефон нөміріңізді жіберіңіз:",
        'phone_btn': "📱 Нөмірді жіберу",
        'select_course': "Курсты таңдаңыз:",
        'success_reg': "✅ Сіз сәтті тіркелдіңіз! Оператор жақын арада хабарласады.",
        'back': "⬅️ Артқа",
        'no_courses': "Курстар әлі қосылмаған.",
        'contact_us': "Бізбен байланыс: +998935860291",
        'faq_ans': "1. Курстар қашан басталады? - Әр айдың басында.\n2. Сертификат беріле ме? - Иә.",
        'admin_msg': "🔔 ЖАҢА ӨТІНІШ:\n👤 Аты: {name}\n📞 Тел: {phone}\n📚 Курс: {course}"
    }
}


# =========================
# DATABASE
# =========================
def db_init():
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS users(
            telegram_id INTEGER PRIMARY KEY, name TEXT, phone TEXT, 
            course TEXT, date TEXT, lang TEXT DEFAULT 'uz')""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS courses(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, description TEXT)""")
        conn.commit()


def execute_query(query, params=(), fetchall=False, fetchone=False):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetchall: return cursor.fetchall()
        if fetchone: return cursor.fetchone()
        conn.commit()


# =========================
# STATES
# =========================
class Register(StatesGroup):
    name = State()
    phone = State()
    course = State()


class AdminStates(StatesGroup):
    waiting_course_name = State()
    waiting_course_desc = State()
    waiting_broadcast_msg = State()


# =========================
# KEYBOARDS
# =========================
def get_lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
         InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz")]
    ])


def get_main_menu(user_id, lang):
    t = TEXTS[lang]
    kb = [
        [KeyboardButton(text=t['courses']), KeyboardButton(text=t['reg'])],
        [KeyboardButton(text=t['contact']), KeyboardButton(text=t['faq'])]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton(text="🛠 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def get_admin_menu():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="➕ Kurs qo'shish"), KeyboardButton(text="📚 Kurslarni boshqarish")],
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="📢 Xabar yuborish")],
        [KeyboardButton(text="⬅️ Tilni o'zgartirish")]
    ], resize_keyboard=True)


# =========================
# HANDLERS
# =========================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    execute_query("INSERT OR IGNORE INTO users (telegram_id) VALUES (?)", (message.from_user.id,))
    await message.answer(TEXTS['uz']['welcome'], reply_markup=get_lang_keyboard())


@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    execute_query("UPDATE users SET lang=? WHERE telegram_id=?", (lang, callback.from_user.id))
    await callback.message.delete()
    await callback.message.answer(TEXTS[lang]['main_menu'], reply_markup=get_main_menu(callback.from_user.id, lang))


# --- REGISTRATION ---
@dp.message(F.text.in_([TEXTS['uz']['reg'], TEXTS['kz']['reg']]))
async def start_reg(message: types.Message, state: FSMContext):
    user = execute_query("SELECT lang FROM users WHERE telegram_id=?", (message.from_user.id,), fetchone=True)
    lang = user[0] if user else 'uz'
    await message.answer(TEXTS[lang]['enter_name'], reply_markup=ReplyKeyboardRemove())
    await state.update_data(lang=lang)
    await state.set_state(Register.name)


@dp.message(Register.name)
async def reg_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data['lang']
    await state.update_data(name=message.text)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=TEXTS[lang]['phone_btn'], request_contact=True)]],
                             resize_keyboard=True)
    await message.answer(TEXTS[lang]['send_phone'], reply_markup=kb)
    await state.set_state(Register.phone)


@dp.message(Register.phone, F.contact | F.text)
async def reg_phone(message: types.Message, state: FSMContext):
    num = message.contact.phone_number if message.contact else message.text
    data = await state.get_data()
    lang = data['lang']
    await state.update_data(phone=num)

    courses = execute_query("SELECT name FROM courses", fetchall=True)
    if not courses:
        return await message.answer(TEXTS[lang]['no_courses'], reply_markup=get_main_menu(message.from_user.id, lang))

    builder = InlineKeyboardBuilder()
    for c in courses: builder.row(InlineKeyboardButton(text=c[0], callback_data=f"c_{c[0]}"))
    await message.answer(TEXTS[lang]['select_course'], reply_markup=builder.as_markup())
    await state.set_state(Register.course)


@dp.callback_query(Register.course, F.data.startswith("c_"))
async def reg_done(callback: types.CallbackQuery, state: FSMContext):
    c_name = callback.data.split("_")[1]
    data = await state.get_data()
    lang = data['lang']
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    execute_query("UPDATE users SET name=?, phone=?, course=?, date=? WHERE telegram_id=?",
                  (data['name'], data['phone'], c_name, now, callback.from_user.id))

    await callback.message.delete()
    await callback.message.answer(TEXTS[lang]['success_reg'], reply_markup=get_main_menu(callback.from_user.id, lang))

    admin_txt = TEXTS[lang]['admin_msg'].format(name=data['name'], phone=data['phone'], course=c_name)
    await bot.send_message(ADMIN_ID, admin_txt)
    await state.clear()


# --- COURSES ---
@dp.message(F.text.in_([TEXTS['uz']['courses'], TEXTS['kz']['courses']]))
async def show_courses(message: types.Message):
    user = execute_query("SELECT lang FROM users WHERE telegram_id=?", (message.from_user.id,), fetchone=True)
    lang = user[0] if user else 'uz'
    courses = execute_query("SELECT id, name FROM courses", fetchall=True)
    if not courses: return await message.answer(TEXTS[lang]['no_courses'])

    builder = InlineKeyboardBuilder()
    for c in courses: builder.row(InlineKeyboardButton(text=f"📖 {c[1]}", callback_data=f"inf_{c[0]}"))
    await message.answer(TEXTS[lang]['courses'], reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("inf_"))
async def course_info(callback: types.CallbackQuery):
    user = execute_query("SELECT lang FROM users WHERE telegram_id=?", (callback.from_user.id,), fetchone=True)
    lang = user[0] if user else 'uz'
    c_id = callback.data.split("_")[1]
    res = execute_query("SELECT name, description FROM courses WHERE id=?", (c_id,), fetchone=True)

    builder = InlineKeyboardBuilder()
    if callback.from_user.id == ADMIN_ID:
        builder.row(InlineKeyboardButton(text="🗑 O'chirish / Өшіру", callback_data=f"del_{c_id}"))
    builder.row(InlineKeyboardButton(text=TEXTS[lang]['back'], callback_data="go_back"))

    if res:
        await callback.message.edit_text(f"📚 *{res[0]}*\n\n{res[1]}", parse_mode="Markdown",
                                         reply_markup=builder.as_markup())


@dp.callback_query(F.data == "go_back")
async def go_back(callback: types.CallbackQuery):
    await callback.message.delete()
    await show_courses(callback.message)


@dp.callback_query(F.data.startswith("del_"), F.from_user.id == ADMIN_ID)
async def delete_course(callback: types.CallbackQuery):
    c_id = callback.data.split("_")[1]
    execute_query("DELETE FROM courses WHERE id=?", (c_id,))
    await callback.answer("✅ Kurs o'chirildi!", show_alert=True)
    await callback.message.delete()
    await show_courses(callback.message)

# --- ADMIN PANEL ---



async def main():
    db_init()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())