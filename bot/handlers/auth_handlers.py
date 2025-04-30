"""
/start  - autenticação e selecção de perfil.

• Mantém «active_role» mesmo após limpar o FSM
• Reaproveita o selector já preparado em role_choice_handlers.ask_role
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
from bot.utils.fsm_helpers import clear_keep_role          #  ← mantém active_role

log     = logging.getLogger(__name__)
router  = Router(name="auth")


# ─────────────────────────── /start ────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext) -> None:
    # tentar apagar o próprio /start (se possível)
    with suppress(exceptions.TelegramBadRequest):
        await msg.delete()

    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, msg.from_user.id)

    # 1) utilizador ainda não ligado → pedir contacto
    if user is None:
        await flow.start_onboarding(msg, state)
        return

    roles: List[str] = [r.lower() for r in await q.get_user_roles(pool, user["user_id"])]

    # 2) utilizador sem permissões
    if not roles:
        await clear_keep_role(state)
        await msg.answer("Ainda não tem permissões atribuídas. "
                         "Contacte a receção/administração.")
        return

    # 3) vários perfis → selector
    if len(roles) > 1:
        await clear_keep_role(state)          # limpa mas guarda active_role se existir
        await ask_role(msg.bot, msg.chat.id, state, roles)
        return

    # 4) um único perfil → entra directo
    await clear_keep_role(state)
    await state.update_data(active_role=roles[0])
    if roles[0] == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    await show_menu(msg.bot, msg.chat.id, state, roles)
