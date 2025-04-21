"""
dispatch.py – Envia o *main menu* correcto consoante o role activo.
Cada menu real deve estar noutro router/fich.
"""

from __future__ import annotations

import logging
from aiogram import types

from handlers.common.keyboards import visitor_main_kb
from handlers.role_switch.role_switch_router import remember_active_role

logger = logging.getLogger(__name__)


async def dispatch_role_menu(message: types.Message, role_name: str) -> None:
    """
    Decide que menu mostrar.
    • Guarda em sessão Redis (via remember_active_role) o role activo,
      caso o utilizador queira mudar mais tarde.
    • Envia o respectivo menu (placeholder simples por agora).
    """
    await remember_active_role(message.from_user.id, role_name)

    if role_name == "patient":
        await message.answer(
            "📅 <i>Menu Paciente</i>\n"
            "Escolha uma opção:",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton("📅 Agenda", callback_data="patient_agenda")],
                    [types.InlineKeyboardButton("💳 Pagamentos", callback_data="patient_payments")],
                    [types.InlineKeyboardButton("🧑‍⚕️ Fisioterapeuta", callback_data="patient_physio")],
                    [types.InlineKeyboardButton("📞 Contactos", callback_data="patient_contacts")],
                ]
            ),
            parse_mode="HTML",
        )
        return

    if role_name == "caregiver":
        await message.answer(
            "👨‍👩‍👧 <b>Menu Cuidador</b>\n"
            "Selecione:",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton("🩺 Paciente(s)", callback_data="caregiver_patients")],
                    [types.InlineKeyboardButton("ℹ️ Serviços",   callback_data="caregiver_services")],
                    [types.InlineKeyboardButton("📞 Contactos",  callback_data="caregiver_contacts")],
                ]
            ),
            parse_mode="HTML",
        )
        return

    if role_name == "physiotherapist":
        await message.answer(
            "🧑‍⚕️ Menu Fisioterapeuta – em desenvolvimento 😉",
        )
        return

    if role_name == "administrator":
        await message.answer(
            "🛠 <b>Menu Administração</b>",
            parse_mode="HTML",
        )
        return

    # Fallback – visitante
    await message.answer(
        "Bem‑vindo! Aqui tem informações públicas:",
        reply_markup=visitor_main_kb(),
    )
