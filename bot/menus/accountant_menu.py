# bot/menus/accountant_menu.py
"""
Inline-keyboard menu for the *Accountant* profile.
Converted from ReplyKeyboardMarkup to InlineKeyboardMarkup so the first
menu can be edited in-place (smooth transition from the role selector).
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_menu() -> InlineKeyboardMarkup:
    """
    Main accountant menu as an inline keyboard.
    Callback-data prefix: «ac:».
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📂 Faturas",     callback_data="ac:invoices")],
            [InlineKeyboardButton(text="💰 Pagamentos",  callback_data="ac:payments")],
        ]
    )
