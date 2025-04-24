# bot/menus/caregiver_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def build_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👶 Dependentes")],
            [KeyboardButton(text="🗓️ Agenda")],
        ],
        resize_keyboard=True,
    )
