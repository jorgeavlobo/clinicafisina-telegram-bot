# bot/menus/physiotherapist_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def build_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Lista de Pacientes")],
            [KeyboardButton(text="📊 Relatórios")],
        ],
        resize_keyboard=True,
    )
