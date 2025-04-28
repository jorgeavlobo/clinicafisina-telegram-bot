# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador.

• só o menu activo responde aos cliques
• timeout de 60 s nos sub-menus
• botão «Voltar» regressa correctamente ao menu principal
• fallback final avisa sempre que se clica num menu antigo
"""
from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter      import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common             import back_button, start_menu_timeout
from bot.menus.administrator_menu import build_menu as _main_menu_kbd

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))        # acesso restrito

# ───────────────────────────── builders ──────────────────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral",               callback_data="agenda:geral")],
            [InlineKeyboardButton(text="🩺 Escolher Fisioterapeuta",
                                  callback_data="agenda:fisios")],
            [back_button()],
        ]
    )


def _users_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Procurar", callback_data="users:search")],
            [InlineKeyboardButton(text="➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )

# ───────────────────────── helpers ───────────────────────────────────
async def _is_active(cb: CallbackQuery, state: FSMContext) -> bool:
    """True se o clique ocorreu no último menu enviado pela bot."""
    data = await state.get_data()
    return cb.message.message_id == data.get("menu_msg_id")


async def _replace_menu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: InlineKeyboardMarkup,
) -> None:
    """
    Troca o menu ‘inline’ mantendo a mesma mensagem sempre que possível,
    gravando/actualizando menu_msg_id no FSM e (re)iniciando o timeout.
    """
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        # mensagem já não existe ou foi editada pelo utilizador → envia nova
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id,
                                menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)      # (re)arma o timeout de 60 s


async def _show_main_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Volta ao menu principal ‹Agenda / Utilizadores›."""
    await state.set_state(AdminMenuStates.MAIN)
    await _replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

# ─────────────────────────── MAIN nav ────────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(("admin:agenda", "admin:users"))
)
async def admin_main_nav(cb: CallbackQuery, state: FSMContext):
    if not await _is_active(cb, state):
        await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
        return

    await cb.answer()

    if cb.data == "admin:agenda":
        await state.set_state(AdminMenuStates.AGENDA)
        await _replace_menu(cb, state,
                            "📅 *Agenda* — seleccione:", _agenda_kbd())
    else:
        await state.set_state(AdminMenuStates.USERS)
        await _replace_menu(cb, state,
                            "👥 *Utilizadores* — seleccione:", _users_kbd())

# ───────────────────────────── Agenda ────────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.AGENDA),
    F.data.in_(("agenda:geral", "agenda:fisios"))
)
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext):
    if not await _is_active(cb, state):
        await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
        return

    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)     # nenhum menu activo

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)

# ───────────────────────── Utilizadores ──────────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.USERS),
    F.data.in_(("users:search", "users:add"))
)
async def users_placeholders(cb: CallbackQuery, state: FSMContext):
    if not await _is_active(cb, state):
        await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
        return

    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)

# ───────────────────── fallback (menus antigos) ──────────────────────
@router.callback_query(                       # ⇢ NÃO depende de estado
    RoleFilter("administrator"),
    F.data.startswith(("admin:", "agenda:", "users:"))
)
async def old_menu_clicked(cb: CallbackQuery):
    """
    Se chegou aqui é porque:
        • o callback não foi capturado por nenhum handler acima
        • logo, não existe menu activo correspondente
    """
    await cb.answer(
        "⚠️ Este menu já não está activo.\n"
        "Envie /start ou pressione *Menu* para abrir um novo.",
        show_alert=True,
    )
