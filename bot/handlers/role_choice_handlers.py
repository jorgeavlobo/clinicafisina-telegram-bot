# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem mais do que um role.

• Mostra um teclado inline com todos os perfis disponíveis.
• Aguarda a escolha durante 60 s; se não houver resposta, remove-o.
• Depois de escolhida a opção:
      – grava «active_role» no FSM
      – coloca o estado específico do menu (p/ admin)
      – abre o menu correspondente com show_menu()
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Iterable, List

from aiogram import Router, exceptions, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus import show_menu
from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

__all__: List[str] = ["ask_role", "router"]  # ← exportado para outros módulos

router = Router(name="role_choice")

# ───────────── config ─────────────
_TIMEOUT = 60  # seg.

_LABELS_PT = {
    "patient":         "Paciente",
    "caregiver":       "Cuidador",
    "physiotherapist": "Fisioterapeuta",
    "accountant":      "Contabilista",
    "administrator":   "Administrador",
}


def _label(role: str) -> str:
    return _LABELS_PT.get(role.lower(), role.capitalize())


# ─────────────────────── função pública ────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """
    Envia o selector de perfis e coloca a FSM em MenuStates.WAIT_ROLE_CHOICE.
    """
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=_label(r),
                    callback_data=f"role:{r.lower()}",
                )
            ]
            for r in roles
        ]
    )

    msg = await bot.send_message(
        chat_id,
        "🔰 Selecione o perfil que pretende utilizar:",
        reply_markup=kbd,
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        role_selector_marker=msg.message_id,
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    asyncio.create_task(
        _expire_selector(bot, msg.chat.id, msg.message_id, state)
    )


# ───────────── rotina de expiração ─────────────
async def _expire_selector(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    await asyncio.sleep(_TIMEOUT)

    # se o estado já mudou ou o marker não coincide, sai
    if await state.get_state() != MenuStates.WAIT_ROLE_CHOICE.state:
        return
    data = await state.get_data()
    if data.get("role_selector_marker") != msg_id:
        return

    await state.clear()
    with suppress(exceptions.TelegramBadRequest):
        await bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)

    warn = await bot.send_message(
        chat_id,
        "⏳ Tempo expirado. Envie /start para escolher de novo.",
    )
    await asyncio.sleep(_TIMEOUT)
    with suppress(exceptions.TelegramBadRequest):
        await warn.delete()


# ───────────── callback de escolha ─────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()      # exemplo: administrator
    data = await state.get_data()
    valid_roles = data.get("roles", [])

    if role not in valid_roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # limpar marcador / selector
    with suppress(exceptions.TelegramBadRequest):
        await cb.message.delete()

    # limpar estado temporário, mas guardar role activo
    await state.clear()
    await state.update_data(active_role=role, roles=valid_roles)

    # definir estado específico para menus que o exijam
    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    await cb.answer(f"Perfil {_label(role)} selecionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
