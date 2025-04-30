# bot/handlers/role_choice_handlers.py
"""
Gestão do menu “Que perfil pretende utilizar?”

• Mostra inline-keyboard com os roles quando o utilizador tem ≥2 perfis.
• Timeout de 60 s: remove teclado e avisa; o aviso desaparece 60 s depois.
Compatível com ActiveMenuMiddleware.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any, Dict, List

from aiogram import Router, F, types, exceptions
from aiogram.fsm.context import FSMContext

from bot.states.menu_states import MenuStates
from bot.menus import show_menu            # mesma função que já apresenta menus

log = logging.getLogger(__name__)
router = Router(name="role_choice")

TIMEOUT = 60  # seg


# ───────────────────── helpers ─────────────────────
def _role_title(role: str) -> str:
    """Título mais amigável se precisares (podes ajustar livremente)."""
    mapping = {
        "patient": "🧑‍🦽 Paciente",
        "caregiver": "🧑‍🤝‍🧑 Cuidador",
        "physiotherapist": "🧑‍⚕️ Fisioterapeuta",
        "accountant": "💼 Contabilista",
        "administrator": "🛠️ Admin",
    }
    return mapping.get(role, role.capitalize())


async def _expire(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
    marker_key: str = "role_menu_marker",
) -> None:
    """Remove teclado após TIMEOUT e apaga aviso 60 s depois."""
    try:
        await asyncio.sleep(TIMEOUT)
        data = await state.get_data()
        if data.get(marker_key) != msg_id:
            return                          # já escolheu

        await state.clear()                 # limpa FSM

        with suppress(exceptions.TelegramBadRequest):
            await bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)

        warn = await bot.send_message(
            chat_id,
            "⚠️ Tempo expirado. Envie /start para voltar a escolher o perfil.",
        )
        await asyncio.sleep(TIMEOUT)
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, warn.message_id)
    except Exception:                       # não queremos quebrar a app
        log.exception("Erro no timeout do menu de roles")


# ─────────────────── API utilizada por outros módulos ───────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: List[str],
) -> None:
    """
    Envia o inline-keyboard de escolha de perfil e prepara tudo para
    o ActiveMenuMiddleware + timeout.
    """
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(_role_title(r), callback_data=f"role:{r}")]
            for r in roles
        ]
    )

    msg = await bot.send_message(
        chat_id,
        "Tem vários perfis associados.\nSelecione o perfil que deseja utilizar:",
        reply_markup=kbd,
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
        role_menu_marker=msg.message_id,
    )

    asyncio.create_task(_expire(bot, chat_id, msg.message_id, state))


# ───────────────────── handler do botão ─────────────────────
@router.callback_query(
    MenuStates.WAIT_ROLE_CHOICE,
    F.data.startswith("role:")
)
async def role_chosen(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1]

    # limpa FSM e mostra o menu correspondente
    await state.clear()
    await cb.message.edit_reply_markup(reply_markup=None)

    await show_menu(cb.bot, cb.message.chat.id, state, [role])
    await cb.answer(f"Perfil «{_role_title(role)}» seleccionado ✨")
