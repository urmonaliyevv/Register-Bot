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




# --- ADMIN PANEL ---



async def main():
    db_init()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())