# bot/menus/physiotherapist_menu.py
"""
Inline-keyboard menu for the *Physiotherapist* profile.
Converted from ReplyKeyboardMarkup so the first menu can be edited
in-place (smooth transition from the role selector).
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_menu() -> InlineKeyboardMarkup:
    """
    Main physiotherapist menu as an inline keyboard.
    Callback-data uses the prefix «ph:».
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Lista de Pacientes", callback_data="ph:patients")],
            [InlineKeyboardButton(text="📊 Relatórios",         callback_data="ph:reports")],
        ]
    )
