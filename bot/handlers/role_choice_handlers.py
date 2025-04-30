# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem **mais do que um** role.

• mostra um inline-keyboard com os perfis disponíveis  
• espera 60 s – se não houver resposta, remove o teclado e avisa  
• grava o «active_role» no FSM para que os middlewares saibam qual
  o menu que deve ficar activo
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Iterable

from aiogram import Router, F, types, exceptions
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.menus import show_menu
from bot.states.menu_states import MenuStates   # ← estado guardado só p/ este selector

router = Router(name="role_choice")

_TIMEOUT = 60  # segundos -----------------------------------------------------------------

# ───────────────────────────── labels ─────────────────────────────
_LABELS_PT = {
    "patient":         "Paciente",
    "caregiver":       "Cuidador",
    "physiotherapist": "Fisioterapeuta",
    "accountant":      "Contabilista",
    "administrator":   "Administrador",
}


def role_label(role: str) -> str:
    """Traduz o *internal name* (‘patient’, …) para PT-BR/PT-PT amigável."""
    return _LABELS_PT.get(role, role.capitalize())


# ───────────────────── API chamada por outros handlers ─────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """
    Envia o inline-keyboard com os papéis disponíveis e
    regista-o como menu activo (para ActiveMenuMiddleware).
    """
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[                       # todos na mesma linha
            types.InlineKeyboardButton(
                text=role_label(r),
                callback_data=f"role:{r}",
            )
            for r in roles
        ]]
    )

    msg = await bot.send_message(
        chat_id,
        "🔰 Escolha o perfil que pretende utilizar:",
        reply_markup=keyboard,
    )

    # gravar como “menu activo” para poder ser limpo depois
    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
        role_selector_marker=msg.message_id,   # usado pelo timeout
    )

    # iniciar tarefa de expiração
    asyncio.create_task(
        _expire_selector(bot, msg.chat.id, msg.message_id, state)
    )


# ───────────────────── timeout de 60 s ─────────────────────
async def _expire_selector(
    bot: types.Bot,
    chat_id: int,
    msg_id: int,
    state: FSMContext,
) -> None:
    await asyncio.sleep(_TIMEOUT)

    data = await state.get_data()
    if data.get("role_selector_marker") != msg_id:
        return  # já houve resposta entretanto

    await state.clear()  # limpa FSM

    # remove inline-keyboard caso ainda exista
    with suppress(exceptions.TelegramBadRequest):
        await bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=None)

    # avisa o utilizador (e limpa o aviso 60 s depois)
    warn = await bot.send_message(
        chat_id,
        "⏳ O tempo esgotou-se. Envie /start para escolher de novo.",
    )
    await asyncio.sleep(_TIMEOUT)
    with suppress(exceptions.TelegramBadRequest):
        await bot.delete_message(chat_id, warn.message_id)


# ───────────────────── callback de escolha ─────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    """
    Handler que corre quando o utilizador toca num dos perfis.
    """
    role = cb.data.split(":", 1)[1]           # ex.: “administrator”

    # marca papel activo para os middlewares
    await state.update_data(active_role=role)
    await state.clear()                       # já não precisamos do estado intermédio

    # remove o keyboard do selector
    with suppress(exceptions.TelegramBadRequest):
        await cb.message.edit_reply_markup(reply_markup=None)

    await cb.answer(f"Perfil {role_label(role)} seleccionado!")

    # mostra o menu correspondente somente a esse papel
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
