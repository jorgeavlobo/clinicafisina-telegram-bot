"""
Colecção de teclados (reply / inline) reutilizados em vários routers.
"""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# ────────── onboarding / visitante ──────────
def share_phone_kb() -> ReplyKeyboardMarkup:
    """
    Teclado de pedido de número de telemóvel.
    O botão «Cancelar» permite ao utilizador recusar sem ter
    de fechar manualmente o keyboard.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Partilhar nº de telemóvel", request_contact=True)],
            [KeyboardButton(text="❌ Cancelar")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,   # fecha‑se após 1 interacção
    )


def visitor_main_kb() -> InlineKeyboardMarkup:
    """
    Menu inline para visitantes não identificados.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("ℹ️ Serviços",  callback_data="visitor_services")],
            [InlineKeyboardButton("👥 Equipa",    callback_data="visitor_team")],
            [InlineKeyboardButton("📞 Contactos", callback_data="visitor_contacts")],
            [InlineKeyboardButton("📝 Registar‑me", callback_data="visitor_register")],
        ]
    )


def regist_menu_kb() -> InlineKeyboardMarkup:
    """
    Sub‑menu de registo: escolha de tipo de conta.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("Sou Paciente",  callback_data="regist_patient")],
            [InlineKeyboardButton("Sou Cuidador",  callback_data="regist_caregiver")],
            [InlineKeyboardButton("⬅️ Voltar",     callback_data="regist_back")],
        ]
    )


# ────────── escolha de role (vários roles) ──────────
def role_choice_kb(role_names: list[str]) -> InlineKeyboardMarkup:
    """
    Gera teclado inline listando todos os roles que o utilizador tem,
    para que possa escolher o contexto activo.
    """
    rows = [
        [InlineKeyboardButton(f"🔸 {role.title()}", callback_data=f"role_{role}")]
        for role in role_names
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
