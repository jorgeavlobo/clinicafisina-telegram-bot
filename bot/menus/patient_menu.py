# bot/menus/patient_menu.py
"""
Inline-keyboard menu for the *Patient* profile.

Changed from ReplyKeyboardMarkup to InlineKeyboardMarkup so the first
menu can be edited in-place (no visual “jump” when switching from the
profile selector).
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_menu() -> InlineKeyboardMarkup:
    """
    Returns the main patient menu as an **inline** keyboard.
    Callback-data prefixes use the same convention as the other roles:
    «pt:<action>».
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗓️ Agenda",       callback_data="pt:agenda")],
            [InlineKeyboardButton(text="💳 Pagamentos",   callback_data="pt:payments")],
            [InlineKeyboardButton(text="🩺 Fisioterapeuta", callback_data="pt:physio")],
        ]
    )
