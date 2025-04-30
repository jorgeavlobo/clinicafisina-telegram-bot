# bot/handlers/auth_handlers.py
"""
/start  – autenticação, selecção de perfil e apresentação do menu
Contact – recebe o nº de telefone durante o onboarding
link_yes / link_no – confirmação “É você?” depois de partilhar contacto
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import List

from aiogram import Router, types, exceptions, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext

from bot.auth                        import auth_flow as flow
from bot.database                    import queries as q
from bot.database.connection         import get_pool
from bot.menus                       import show_menu
from bot.handlers.role_choice_handlers import ask_role
from bot.states.admin_menu_states    import AdminMenuStates
from bot.states.auth_states          import AuthStates
from bot.utils.fsm_helpers           import clear_keep_role

log     = logging.getLogger(__name__)
router  = Router(name="auth")

# ───────────────────────────── /start ─────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext) -> None:
    """Comando /start: onboarding ou abertura do menu."""

    # 0) tenta remover a própria mensagem “/start”
    with suppress(exceptions.TelegramBadRequest):
        await msg.delete()

    # 0-bis) se houver menu anterior, apaga-o
    data = await state.get_data()
    old_id   = data.get("menu_msg_id")
    old_chat = data.get("menu_chat_id")
    if old_id and old_chat:
        with suppress(exceptions.TelegramBadRequest):
            await msg.bot.delete_message(old_chat, old_id)

    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, msg.from_user.id)

    # 1) ainda não ligado → inicia onboarding
    if user is None:
        await flow.start_onboarding(msg, state)
        return

    # 2) recupera perfis do utilizador
    roles: List[str] = [
        r.lower() for r in await q.get_user_roles(pool, user["user_id"])
    ]

    # 2a) não tem permissões
    if not roles:
        await clear_keep_role(state)
        await msg.answer(
            "Ainda não tem permissões atribuídas. "
            "Contacte a receção/administração."
        )
        return

    # 3) vários perfis → mostra selector
    if len(roles) > 1:
        await clear_keep_role(state)          # limpa FSM mas preserva active_role
        await ask_role(msg.bot, msg.chat.id, state, roles)
        return

    # 4) apenas um perfil → entra directo
    await clear_keep_role(state)
    active = roles[0]
    await state.update_data(active_role=active)

    if active == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    await show_menu(
        bot     = msg.bot,
        chat_id = msg.chat.id,
        state   = state,
        roles   = roles,
    )

# ─────────────── contacto partilhado ───────────────
@router.message(
    StateFilter(AuthStates.WAITING_CONTACT),
    F.contact,
)
async def contact_handler(msg: types.Message, state: FSMContext):
    await flow.handle_contact(msg, state)

# ─────────────── “✅ Sim” na confirmação ───────────────
@router.callback_query(
    StateFilter(AuthStates.CONFIRMING_LINK),
    F.data == "link_yes",
)
async def cb_confirm_yes(cb: types.CallbackQuery, state: FSMContext):
    await flow.confirm_link(cb, state)

# ─────────────── “❌ Não” na confirmação ───────────────
@router.callback_query(
    StateFilter(AuthStates.CONFIRMING_LINK),
    F.data == "link_no",
)
async def cb_confirm_no(cb: types.CallbackQuery, state: FSMContext):
    await flow.cancel_link(cb, state)
