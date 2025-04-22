from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ────────── onboarding / visitor flow ──────────
def share_phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Partilhar nº de telemóvel", request_contact=True)],
            [KeyboardButton(text="❌ Cancelar")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

def visitor_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("ℹ️ Serviços",  url="https://fisina.pt/servicos")],
            [InlineKeyboardButton("👥 Equipa",    url="https://fisina.pt/equipa")],
            [InlineKeyboardButton("📞 Contactos", url="https://fisina.pt/contactos")],
            [InlineKeyboardButton("📝 Registar‑me", callback_data="visitor_register")],
        ]
    )

def regist_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton("Sou Paciente", callback_data="regist_patient")],
            [InlineKeyboardButton("Sou Cuidador", callback_data="regist_caregiver")],
            [InlineKeyboardButton("⬅️ Voltar",    callback_data="regist_back")],
        ]
    )

def role_choice_kb(role_names: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(f"🔸 {r.title()}", callback_data=f"role_{r}")]
            for r in role_names
        ]
    )
