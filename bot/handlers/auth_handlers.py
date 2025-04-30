# bot/handlers/auth_handlers.py
"""
/start  – autenticação, selecção de perfil e apresentação do menu
Contact  – recebe o nº de telefone durante o onboarding
link_yes / link_no – confirmação “É você?” depois de partilhar contacto
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import List

from aiogram import Router, types, exceptions, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext

from bot.auth                      import auth_flow as flow
from bot.database                  import queries as q
from bot.database.connection       import get_pool
from bot.menus                     import show_menu
from bot.handlers.role_choice_handlers import ask_role
from bot.states.admin_menu_states  import AdminMenuStates
from bot.states.auth_states        import AuthStates
from bot.utils.fsm_helpers         import clear_keep_role

log     = logging.getLogger(__name__)
router  = Router(name="auth")

# ───────────────────────────── /start ─────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext) -> None:
    # Apaga a própria mensagem “/start”, se possível
    with suppress(exceptions.TelegramBadRequest):
        await msg.delete()

    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, msg.from_user.id)

    # 1) ainda não ligado → inicia onboarding
    if user is None:
        await flow.start_onboarding(msg, state)
        return

    # 2) recupera roles
    roles: List[str] = [r.lower()
                        for r in await q.get_user_roles(pool, user["user_id"])]

    # 2a) sem permissões
    if not roles:
        await clear_keep_role(state)
        await msg.answer("Ainda não tem permissões atribuídas. "
                         "Contacte a receção/administração.")
        return

    # 3) vários perfis → selector
    if len(roles) > 1:
        await clear_keep_role(state)
        await ask_role(msg.bot, msg.chat.id, state, roles)
        return

    # 4) um único perfil → entra directo
    await clear_keep_role(state)
    active_role = roles[0]
    await state.update_data(active_role=active_role)
    if active_role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    await show_menu(msg.bot, msg.chat.id, state, roles)

# ─────────────── contacto partilhado ───────────────
@router.message(
    StateFilter(AuthStates.WAITING_CONTACT),   # FSM == WAITING_CONTACT
    F.contact,                                 # a mensagem contém Contact
)
async def contact_handler(msg: types.Message, state: FSMContext):
    await flow.handle_contact(msg, state)

# ─────────────── “✅ Sim” na confirmação ───────────────
@router.callback_query(
    StateFilter(AuthStates.CONFIRMING_LINK),   # FSM == CONFIRMING_LINK
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
