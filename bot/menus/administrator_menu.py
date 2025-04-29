# bot/menus/administrator_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗓 Agenda",       callback_data="admin:agenda")],
            [InlineKeyboardButton(text="👥 Utilizadores", callback_data="admin:users")],
        ]
    )

def build_user_type_kbd() -> InlineKeyboardMarkup:
    """
    Build an inline keyboard for selecting the type of user to add.
    """
    keyboard = [
        [InlineKeyboardButton(text="👤 Paciente",       callback_data="role:patient")],
        [InlineKeyboardButton(text="🤝 Cuidador",       callback_data="role:caregiver")],
        [InlineKeyboardButton(text="🩺 Fisioterapeuta", callback_data="role:physiotherapist")],
        [InlineKeyboardButton(text="💼 Contabilista",   callback_data="role:accountant")],
        [InlineKeyboardButton(text="💻 Administrador",  callback_data="role:administrator")],
        [InlineKeyboardButton(text="🔙 Voltar",         callback_data="users:add_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
