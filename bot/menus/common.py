# bot/menus/common.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def back_inline(text: str = "🔙 Voltar", cb_data: str = "back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=cb_data)]]
    )
