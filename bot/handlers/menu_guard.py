# bot/handlers/menu_guard.py
"""
«Guarda» de menus ― impõe que *só* o menu mais recente aceite cliques.

Se o utilizador tocar num menu antigo:
    • mostra-lhe um pop-up a avisar que o menu já não está activo
    • impede que os demais routers processem esse callback

Além disso expõe dois helpers reutilizados pelos handlers:
    ▸ is_active_menu(cb, state)  → bool
    ▸ replace_menu(cb, state, text, kbd)
"""

from __future__ import annotations

from typing import Any

from aiogram import Router, F, exceptions
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

router = Router(name="menu_guard")        # 👉 este router deve ser incluído 1.º


# ───────────────────────── helpers reutilizáveis ─────────────────────────
async def is_active_menu(cb: CallbackQuery, state: FSMContext) -> bool:
    """
    True se o *callback* pertence ao menu que está registado no FSM
    (menu_msg_id / menu_chat_id).
    """
    data = await state.get_data()
    try:
        registered_id: int = int(data.get("menu_msg_id") or -1)
        registered_chat: int = int(data.get("menu_chat_id") or -1)
    except ValueError:            # ids corrompidos?
        return False

    msg = cb.message
    return msg and msg.message_id == registered_id and msg.chat.id == registered_chat


async def replace_menu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: InlineKeyboardMarkup,
) -> None:
    """
    Troca o teclado ‘inline’, tentando *editar* a mensagem.
    Se já não for possível (apagada/antiga) envia nova mensagem
    e actualiza menu_msg_id / menu_chat_id no FSM.
    """
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message                       # id mantém-se
    except exceptions.TelegramBadRequest:
        # mensagem não existe ou foi editada pelo utilizador → envia nova
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    # (re)arma o timeout de 60 s se já existir task registada
    from bot.menus.common import start_menu_timeout          # import p/ evitar ciclo
    start_menu_timeout(cb.bot, msg, state)


# ───────────────────────── filtro/handler global ─────────────────────────
class _SkipHandler(exceptions.TelegramAPIError):
    """
    Excepção interna utilizada apenas para travar a propagação
    de callbacks pertencentes a menus antigos.
    """


async def _stale_menu_guard(cb: CallbackQuery, state: FSMContext):
    """
    Intercepta **todos** os CallbackQuery-s:
        – se for do menu activo → deixa seguir
        – caso contrário          → avisa e pára processamento
    """
    if await is_active_menu(cb, state):
        return                                # deixa passar aos routers seguintes

    # menu obsoleto
    try:
        await cb.answer(
            "⚠️ Este menu já não está activo.\n"
            "Envie /start ou carregue *Menu* para abrir um novo.",
            show_alert=True,
        )
    finally:
        raise _SkipHandler()                  # impede handlers posteriores


# regista-se no router (sem dependência de estado/role)
router.callback_query.register(_stale_menu_guard, F.data)  # qualquer callback
