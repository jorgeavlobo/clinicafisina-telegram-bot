# bot/menus/administrator_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def build_menu() -> InlineKeyboardMarkup:
    """
    Menu principal do Administrador (“Agenda” / “Utilizadores”).
    As callback-data começam sempre por `admin:` para podermos
    filtrar facilmente no handler.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗓 Agenda",
                    callback_data="admin:agenda",
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Utilizadores",
                    callback_data="admin:users",
                )
            ],
        ]
    )
