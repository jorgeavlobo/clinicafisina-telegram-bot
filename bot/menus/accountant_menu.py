# bot/menus/accountant_menu.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def build_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📂 Faturas")],
            [KeyboardButton(text="💰 Pagamentos")],
        ],
        resize_keyboard=True,
    )
