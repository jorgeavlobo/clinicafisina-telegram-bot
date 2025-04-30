# bot/handlers/auth_handlers.py
"""
/start, onboarding e re-entrada no bot.

Fluxo resumido
──────────────
1. /start
   • apaga a própria mensagem
   • se NÃO ligado → inicia onboarding (pedir contacto)
   • se ligado
       – 0 roles  → avisa que não tem permissões
       – 1 role   → mostra directamente o menu desse perfil
       – >1 roles → apresenta selector de perfil (com timeout de 60 s)

2. Durante onboarding:
   • WAITING_CONTACT   → recebe contacto
   • CONFIRMING_LINK   → “É você? (Sim / Não)”
"""

from __future__ import annotations

import logging
from aiogram import Router, F, types, exceptions
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext

from bot.auth import auth_flow as flow            # fluxo onboarding
from bot.handlers.role_choice_handlers import ask_role
from bot.states.auth_states import AuthStates
from bot.database.connection import get_pool
from bot.database import queries as q
from bot.menus import show_menu

log = logging.getLogger(__name__)
router = Router(name="auth")

# ───────────────────────────── /start ─────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext) -> None:
    # 0) limpa a própria mensagem /start
    try:
        await msg.delete()
    except exceptions.TelegramBadRequest:
        pass                                           # sem perms? prossegue

    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, msg.from_user.id)

    # 1) ainda NÃO ligado → onboarding
    if user is None:
        await flow.start_onboarding(msg, state)
        return

    roles = await q.get_user_roles(pool, user["user_id"])

    # 2) sem permissões
    if not roles:
        await state.clear()
        await msg.answer(
            _("Ainda não tem permissões atribuídas. "
              "Contacte a receção/administrador."))
        return

    # 3) preserva id do último menu (para ser apagado) e limpa FSM
    data           = await state.get_data()
    last_menu_id   = data.get("menu_msg_id")
    last_menu_chat = data.get("menu_chat_id")
    await state.clear()
    if last_menu_id and last_menu_chat:
        await state.update_data(menu_msg_id=last_menu_id,
                                menu_chat_id=last_menu_chat)

    # 4) selector de perfil ou menu directo
    if len(roles) == 1:
        await show_menu(msg.bot, msg.chat.id, state, roles)
    else:
        await ask_role(msg.bot, msg.chat.id, state, roles)

# ────────────────── contacto partilhado (onboarding) ──────────────────
@router.message(StateFilter(AuthStates.WAITING_CONTACT), F.contact)
async def contact_handler(message: types.Message, state: FSMContext) -> None:
    await flow.handle_contact(message, state)

# ─────────── confirmação “É você?” (YES / NO) ───────────
@router.callback_query(StateFilter(AuthStates.CONFIRMING_LINK), F.data == "link_yes")
async def cb_confirm_yes(cb: types.CallbackQuery, state: FSMContext) -> None:
    await flow.confirm_link(cb, state)

@router.callback_query(StateFilter(AuthStates.CONFIRMING_LINK), F.data == "link_no")
async def cb_confirm_no(cb: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.edit_text(_("Operação cancelada."))
    await cb.answer()
