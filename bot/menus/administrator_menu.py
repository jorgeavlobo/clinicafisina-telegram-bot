# bot/menus/administrator_menu.py
"""
Constrói **inline-keyboard** do menu principal de Administrador.

É mostrado logo após /start quando o papel activo é «administrator».
As callbacks começam sempre por  adm:  para serem tratadas no
administrator_handlers.py
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def build_menu() -> InlineKeyboardMarkup:
    """
    Teclado inline principal do Administrador.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗓 Agenda",      callback_data="admin:agenda")],
            [InlineKeyboardButton(text="👥 Utilizadores", callback_data="admin:users")],
        ]
    )
