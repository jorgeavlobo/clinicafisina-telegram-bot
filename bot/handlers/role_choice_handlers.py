# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra um inline-keyboard com timeout de 60 s
• Após a escolha grava «active_role» no FSM
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Iterable

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                    import show_menu
from bot.states.menu_states       import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router   = Router(name="role_choice")
_TIMEOUT = 60  # segundos

_LABELS_PT = {
    "patient":         "Paciente",
    "caregiver":       "Cuidador",
    "physiotherapist": "Fisioterapeuta",
    "accountant":      "Contabilista",
    "administrator":   "Administrador",
}


def _label(role: str) -> str:
    """Rótulo PT; capitaliza por defeito."""
    return _LABELS_PT.get(role.lower(), role.capitalize())


# ───────────────────────── API pública ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """Envia o selector de perfis e coloca o FSM em WAIT_ROLE_CHOICE."""
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(
                text=_label(r),
                callback_data=f"role:{r.lower()}",
            )
        ] for r in roles]
    )

    msg = await bot.send_message(
        chat_id,
        "🔰 *Escolha o perfil:*",
        reply_markup=kbd,
        parse_mode="Markdown",
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],       # ← guardado para validação
        role_selector_marker=msg.message_id,
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    # cria task de timeout
    asyncio.create_task(
        _expire_selector(bot, msg.chat.id, msg.message_id, state)
    )


# ───────────────────────── timeout ─────────────────────────
async def _expire_selector(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    """Apaga por completo o selector se o utilizador nada escolher em 60 s."""
    await asyncio.sleep(_TIMEOUT)

    # continua só se ainda estivermos exactamente no mesmo selector
    if await state.get_state() != MenuStates.WAIT_ROLE_CHOICE.state:
        return
    if (await state.get_data()).get("role_selector_marker") != msg_id:
        return

    # 1) tentar apagar a mensagem inteira
    deleted = False
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        deleted = True
    except exceptions.TelegramBadRequest:
        deleted = False

    # 2) se não deu, pelo menos limpa texto + teclado
    if not deleted:
        with suppress(exceptions.TelegramBadRequest):
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text="\u200b",          # zero-width space → texto invisível
                reply_markup=None,
            )

    # 3) limpar FSM (não há active_role nesta fase)
    await state.clear()

    # 4) aviso temporário
    warn = await bot.send_message(
        chat_id,
        "⏳ Tempo expirado. Envie /start para escolher de novo.",
    )
    await asyncio.sleep(_TIMEOUT)
    with suppress(exceptions.TelegramBadRequest):
        await warn.delete()


# ─────────────────── callback “role:…” ───────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role  = cb.data.split(":", 1)[1].lower()
    data  = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # remove a mensagem do selector
    with suppress(exceptions.TelegramBadRequest):
        await cb.message.delete()

    # limpa FSM temporária mas mantém lista de roles
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    # estado base (só necessário para admin)
    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
