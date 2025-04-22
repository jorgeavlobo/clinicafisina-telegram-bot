"""
Coleção de teclados (reply / inline) usados em vários routers.
Mantemos todos aqui para evitar duplicação.
"""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)


# ────────── onboarding ──────────
def share_phone_kb() -> ReplyKeyboardMarkup:
    """Pede ao utilizador para partilhar o contacto Telegram."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton("📲 Partilhar nº de telemóvel", request_contact=True)],
            [KeyboardButton("❌ Cancelar")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def visitor_main_kb() -> InlineKeyboardMarkup:
    """Menu para utilizadores não identificados."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("ℹ️ Serviços",  callback_data="visitor_services")],
            [InlineKeyboardButton("👥 Equipa",    callback_data="visitor_team")],
            [InlineKeyboardButton("📞 Contactos", callback_data="visitor_contacts")],
            [InlineKeyboardButton("📝 Registar‑me", callback_data="visitor_register")],
        ]
    )


def regist_menu_kb() -> InlineKeyboardMarkup:
    """Escolha de tipo de registo (paciente vs. cuidador)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("Sou Paciente", callback_data="regist_patient")],
            [InlineKeyboardButton("Sou Cuidador", callback_data="regist_caregiver")],
            [InlineKeyboardButton("⬅️ Voltar",    callback_data="regist_back")],
        ]
    )


# ────────── escolha de role ──────────
def role_choice_kb(role_names: list[str]) -> InlineKeyboardMarkup:
    """Mostra buttons para alternar entre múltiplos roles que um user possa ter."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(f"🔸 {role.title()}", callback_data=f"role_{role}")]
            for role in role_names
        ]
    )
