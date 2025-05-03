# bot/menus/administrator_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.menus.ui_helpers import back_button

__all__ = ["build_menu", "build_user_type_kbd"]

# ──────────────── menu principal ────────────────
def build_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Utilizadores", callback_data="admin:users")],
            [InlineKeyboardButton(text="📅 Agenda",       callback_data="admin:agenda")],
            [InlineKeyboardButton(text="💬 Mensagens",    callback_data="admin:messages")],
        ]
    )

# ─────────── teclado “Escolha do tipo de utilizador” ───────────
def build_user_type_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🩹 Paciente",        callback_data="role:patient")],
            [InlineKeyboardButton(text="🫱🏼‍🫲🏽 Cuidador",        callback_data="role:caregiver")],
            [InlineKeyboardButton(text="👩🏼‍⚕️ Fisioterapeuta",  callback_data="role:physiotherapist")],
            [InlineKeyboardButton(text="📊 Contabilista",    callback_data="role:accountant")],
            [InlineKeyboardButton(text="👨🏼‍💻 Administrador",   callback_data="role:administrator")],
            [back_button()],   # ← linha própria, sem parênteses a mais
        ]
    )
