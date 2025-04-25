# bot/handlers/administrator_handlers.py
from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common import back_button

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))  # só admins


# ───────────────────────── helpers de teclado ─────────────────────────
def _agenda_kbd():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📆 Geral",
                    callback_data="agenda:geral",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🩺 Escolher Fisioterapeuta",
                    callback_data="agenda:fisios",
                )
            ],
            [ [back_button()] ],            # botão ‘Voltar’
        ]
    )


def _users_kbd():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔍 Procurar",
                    callback_data="users:search",
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Adicionar",
                    callback_data="users:add",
                )
            ],
            [ [back_button()] ],
        ]
    )


# ───────────────────────── menu principal ─────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(["admin:agenda", "admin:users"]),
)
async def admin_main_nav(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()

    if cb.data == "admin:agenda":
        await state.set_state(AdminMenuStates.AGENDA)
        await cb.message.edit_reply_markup(reply_markup=None)
        await cb.message.answer(
            "📅 *Agenda* — seleccione uma opção:",
            parse_mode="Markdown",
            reply_markup=_agenda_kbd(),
        )
    else:  # admin:users
        await state.set_state(AdminMenuStates.USERS)
        await cb.message.edit_reply_markup(reply_markup=None)
        await cb.message.answer(
            "👥 *Utilizadores* — seleccione uma opção:",
            parse_mode="Markdown",
            reply_markup=_users_kbd(),
        )


# ───────────────────────── submenu Agenda ─────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "agenda:geral")
async def agenda_geral(cb: CallbackQuery) -> None:
    await cb.answer("🚧 Placeholder: Agenda geral", show_alert=True)


@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "agenda:fisios")
async def agenda_por_fisio(cb: CallbackQuery) -> None:
    await cb.answer("🚧 Placeholder: lista de fisioterapeutas", show_alert=True)


# ───────────────────────── submenu Utilizadores ─────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "users:search")
async def users_search(cb: CallbackQuery) -> None:
    await cb.answer("🚧 Placeholder: pesquisa de utilizadores", show_alert=True)


@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "users:add")
async def users_add(cb: CallbackQuery) -> None:
    await cb.answer("🚧 Placeholder: adicionar utilizador", show_alert=True)


# ───────────────────────── botão Voltar em QUALQUER sub-menu ─────────────────────────
@router.callback_query(
    StateFilter(AdminMenuStates.AGENDA) |
    StateFilter(AdminMenuStates.USERS),
    F.data == "back",
)
async def back_to_main(cb: CallbackQuery, state: FSMContext) -> None:
    from bot.menus.administrator_menu import build_menu  # import local para evitar ciclos

    await cb.answer()
    await state.set_state(AdminMenuStates.MAIN)
    await cb.message.edit_text(
        "💻 *Menu:*",
        parse_mode="Markdown",
        reply_markup=build_menu(),
    )
