# bot/handlers/menu_guard.py
"""
Garanta que só o menu *actual* aceita cliques.

• Se o utilizador clicar num menu antigo: mostra pop-up a avisar.
• Exponibiliza helpers reutilizados pelos vários handlers:
      ▸ is_active_menu(cb, state)
      ▸ replace_menu(cb, state, text, kbd)
"""

from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

router = Router(name="menu_guard")                  # ➜ incluir 1.º no dispatcher


# ───────────────────────── helpers reutilizáveis ─────────────────────────
async def is_active_menu(cb: CallbackQuery, state: FSMContext) -> bool:
    """True se o callback pertencer ao menu registado em FSM."""
    data = await state.get_data()
    return (
        cb.message
        and cb.message.message_id == int(data.get("menu_msg_id", -1))
        and cb.message.chat.id == int(data.get("menu_chat_id", -1))
    )


async def replace_menu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: InlineKeyboardMarkup,
) -> None:
    """
    Troca o teclado inline tentando editar a mensagem.
    Se não der, envia nova e actualiza menu_msg_id / menu_chat_id.
    Reinicia sempre o timeout de 60 s.
    """
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        # mensagem inexistente ou já editada → cria nova
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    # (re)arma o timeout
    from bot.menus.common import start_menu_timeout          # import tardio
    start_menu_timeout(cb.bot, msg, state)


# ────────────────── guarda global de callbacks (1º router) ─────────────────
@router.callback_query(F.data)        # qualquer CallbackQuery
async def _stale_menu_guard(cb: CallbackQuery, state: FSMContext):
    """
    Se o clique vier de um menu antigo mostra aviso e pára silenciosamente
    (os routers seguintes ignorarão porque também verificam is_active_menu).
    """
    if await is_active_menu(cb, state):
        return                        # clique no menu válido → continua fluxo

    await cb.answer(
        "⚠️ Este menu já não está activo.\n"
        "Envie /start ou pressione *Menu* para abrir um novo.",
        show_alert=True,
    )
    # Não é preciso lançar excepções: os handlers posteriores abortam sozinhos
