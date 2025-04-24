# bot/menus/patient_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def build_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗓️ Agenda")],
            [KeyboardButton(text="💳 Pagamentos")],
            [KeyboardButton(text="🩺 Fisioterapeuta")],
        ],
        resize_keyboard=True,
    )
