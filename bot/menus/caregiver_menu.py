# bot/menus/caregiver_menu.py
"""
Inline-keyboard menu for the *Caregiver* profile.
Converted from ReplyKeyboardMarkup to InlineKeyboardMarkup so the first
menu can be edited seamlessly from the role selector.
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_menu() -> InlineKeyboardMarkup:
    """
    Main caregiver menu as an inline keyboard.
    Callback-data prefix: «cg:».
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👶 Dependentes", callback_data="cg:dependents")],
            [InlineKeyboardButton(text="🗓️ Agenda",      callback_data="cg:agenda")],
        ]
    )
