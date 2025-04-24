# bot/handlers/system_handlers.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from bot.menus import show_menu
from bot.states.menu_states import MenuStates

router = Router(name="system")

@router.callback_query(MenuStates.WAIT_ROLE_CHOICE, F.data.startswith("role:"))
async def role_chosen(cb: CallbackQuery, state: FSMContext, roles: list[str]):
    requested = cb.data.split(":", 1)[1]
    if requested not in roles:
        await cb.answer("Não tem permissão para esse perfil.", show_alert=True)
        return
    await cb.answer()
    await show_menu(cb.bot, cb.message.chat.id, state, roles, requested)
