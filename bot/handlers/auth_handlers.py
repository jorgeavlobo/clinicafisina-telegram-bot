# bot/handlers/auth_handlers.py
"""
/start – autenticação, escolha de perfil e abertura do menu principal.
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import List

from aiogram import types, Router, exceptions
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from bot.auth import auth_flow as flow
from bot.database.connection import get_pool
from bot.database import queries as q
from bot.handlers.role_choice_handlers import ask_role
from bot.menus import show_menu
from bot.states.admin_menu_states import AdminMenuStates
from bot.utils.fsm_helpers import clear_keep_role

log    = logging.getLogger(__name__)
router = Router(name="auth")

# ─────────────────────────── /start ────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext) -> None:
    # apaga /start (se possível) para manter o chat limpo
    with suppress(exceptions.TelegramBadRequest):
        await msg.delete()

    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, msg.from_user.id)

    # 1) não ligado → inicia onboarding
    if user is None:
        await flow.start_onboarding(msg, state)
        return

    # 2) já ligado → obter roles
    roles: List[str] = [
        r.lower() for r in await q.get_user_roles(pool, user["user_id"])
    ]

    if not roles:                     # sem permissões
        await clear_keep_role(state)
        await msg.answer(
            "Ainda não tem permissões atribuídas.\n"
            "Contacte a receção/administrador."
        )
        return

    if len(roles) > 1:                # vários papéis → selector
        await clear_keep_role(state)
        await ask_role(msg.bot, msg.chat.id, state, roles)
        return

    # único perfil → vai directo
    await clear_keep_role(state)
    active = roles[0]
    await state.update_data(active_role=active)

    if active == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    await show_menu(msg.bot, msg.chat.id, state, roles)
