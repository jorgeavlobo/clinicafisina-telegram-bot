# bot/handlers/auth_handlers.py
"""
/start  – autenticação, selecção de perfil e apresentação do menu.

Fluxo:
1.  Se o utilizador ainda NÃO estiver ligado → delega no onboarding
    (auth_flow.start_onboarding).
2.  Se estiver ligado mas sem roles → avisa que não tem permissões.
3.  Se tiver vários roles → mostra selector (role_choice_handlers.ask_role).
4.  Se tiver só um role → grava «active_role» e mostra logo o menu.

Em todas as ramificações o helper clear_keep_role() é usado para
limpar o FSM sem perder um eventual «active_role» já definido
(sessões anteriores).
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import List

from aiogram import Router, exceptions, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.auth import auth_flow as flow
from bot.database import queries as q
from bot.database.connection import get_pool
from bot.menus import show_menu
from bot.handlers.role_choice_handlers import ask_role
from bot.states.admin_menu_states import AdminMenuStates
from bot.utils.fsm_helpers import clear_keep_role  # mantém active_role

log = logging.getLogger(__name__)
router = Router(name="auth")


# ───────────────────────────── /start ──────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext) -> None:
    # tenta remover a própria mensagem /start para manter o chat limpo
    with suppress(exceptions.TelegramBadRequest):
        await msg.delete()

    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, msg.from_user.id)

    # 1) Utilizador ainda NÃO ligado → inicia onboarding
    if user is None:
        await flow.start_onboarding(msg, state)
        return

    # 2) Já ligado – recuperar roles
    roles: List[str] = [
        r.lower() for r in await q.get_user_roles(pool, user["user_id"])
    ]

    # 2a) Sem permissões atribuídas
    if not roles:
        await clear_keep_role(state)
        await msg.answer(
            "Ainda não tem permissões atribuídas. "
            "Contacte a receção/administração."
        )
        return

    # 3) Vários perfis → mostrar selector
    if len(roles) > 1:
        await clear_keep_role(state)          # limpa mas preserva active_role
        await ask_role(msg.bot, msg.chat.id, state, roles)
        return

    # 4) Apenas um perfil → entra directamente
    await clear_keep_role(state)
    active_role = roles[0]
    await state.update_data(active_role=active_role)

    # alguns menus requerem um estado base (ex.: administrador)
    if active_role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    await show_menu(
        bot=msg.bot,
        chat_id=msg.chat.id,
        state=state,
        roles=roles,
    )
