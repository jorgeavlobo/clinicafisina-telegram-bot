# bot/menus/administrator_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def build_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Utilizadores")],
            [KeyboardButton(text="⚙️ Sistema")],
        ],
        resize_keyboard=True,
    )
