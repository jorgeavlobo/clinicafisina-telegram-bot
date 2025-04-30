# bot/menus/administrator_menu.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.menus.common import back_button

__all__ = ["build_menu", "build_user_type_kbd"]


def build_menu() -> InlineKeyboardMarkup:
    """Menu principal de administrador (NÃO tem botão Voltar)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("🗂 Utilizadores", callback_data="admin:users")],
            [InlineKeyboardButton("📅 Agenda",       callback_data="admin:agenda")],
            [InlineKeyboardButton("💬 Mensagens",    callback_data="admin:messages")],
        ]
    )


# ───────────── teclado “Escolha do tipo de utilizador” ─────────────
def build_user_type_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("Paciente",        callback_data="role:patient")],
            [InlineKeyboardButton("Cuidador",        callback_data="role:caregiver")],
            [InlineKeyboardButton("Fisioterapeuta",  callback_data="role:physiotherapist")],
            [InlineKeyboardButton("Contabilista",    callback_data="role:accountant")],
            [InlineKeyboardButton("Administrador",   callback_data="role:administrator")],
            [back_button()],          # ← tem de estar dentro de lista
        ]
    )
