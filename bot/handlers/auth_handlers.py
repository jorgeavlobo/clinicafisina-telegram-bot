# bot/handlers/auth_handlers.py
"""
Handler layer (Aiogram 3).

/start         – autenticação, escolha de perfil ou abertura de menu
Contact        – recebe o nº durante o onboarding
Texto livre    – apagado (se ainda aguardamos contacto)
link_yes/no    – confirmação “É você?” após partilhar contacto
"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import List

from aiogram import F, Router, exceptions, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext

from bot.auth                        import auth_flow as flow
from bot.database                    import queries as q
from bot.database.connection         import get_pool
from bot.handlers.role_choice_handlers import ask_role
from bot.menus                       import show_menu
from bot.states.admin_menu_states    import AdminMenuStates
from bot.states.auth_states          import AuthStates
from bot.utils.fsm_helpers           import clear_keep_role

log     = logging.getLogger(__name__)
router  = Router(name="auth")

# ───────────────────────────── /start ─────────────────────────────
@router.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext) -> None:
    """Entra no fluxo: onboarding ou abertura de menu."""
    log.warning("### /start recebido: %s", repr(msg.text))

    # remove a própria mensagem /start (best-effort)
    with suppress(exceptions.TelegramBadRequest):
        await msg.delete()

    # apaga menu anterior (se existir)
    data = await state.get_data()
    old_id   = data.get("menu_msg_id")
    old_chat = data.get("menu_chat_id")
    if old_id and old_chat:
        with suppress(exceptions.TelegramBadRequest):
            await msg.bot.delete_message(old_chat, old_id)

    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, msg.from_user.id)

    # ─── utilizador ainda não ligado → onboarding ───
    if user is None:
        await flow.start_onboarding(msg, state)
        return

    # ─── perfis do utilizador ───
    roles: List[str] = [r.lower() for r in await q.get_user_roles(pool, user["user_id"])]

    if not roles:                               # sem permissões
        await clear_keep_role(state)
        await msg.answer(
            "Ainda não tem permissões atribuídas.\n"
            "Contacte a receção/administrador."
        )
        return

    if len(roles) > 1:                          # vários perfis → selector
        await clear_keep_role(state)
        await ask_role(msg.bot, msg.chat.id, state, roles)
        return

    # ─── único perfil → entra directo ───
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
async def contact_handler(msg: types.Message, state: FSMContext) -> None:
    await flow.handle_contact(msg, state)

# ───────────── texto enquanto esperamos contacto ─────────────
@router.message(
    StateFilter(AuthStates.WAITING_CONTACT),
    F.text,
)
async def waiting_contact_plain_text(msg: types.Message, state: FSMContext) -> None:
    """
    O utilizador escreveu texto em vez de usar o botão «ENVIAR CONTACTO».
    Delegamos a lógica no módulo auth_flow (apagar + aviso + re-mostrar botão).
    """
    await flow.reject_plain_text(msg, state)

# ─────────────── “✅ Sim” na confirmação ───────────────
@router.callback_query(
    StateFilter(AuthStates.CONFIRMING_LINK),
    F.data == "link_yes",
)
async def cb_confirm_yes(cb: types.CallbackQuery, state: FSMContext) -> None:
    await flow.confirm_link(cb, state)

# ─────────────── “❌ Não” na confirmação ───────────────
@router.callback_query(
    StateFilter(AuthStates.CONFIRMING_LINK),
    F.data == "link_no",
)
async def cb_confirm_no(cb: types.CallbackQuery, state: FSMContext) -> None:
    await flow.cancel_link(cb, state)
