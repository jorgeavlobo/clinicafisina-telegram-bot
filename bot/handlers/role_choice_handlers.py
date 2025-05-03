# bot/handlers/role_choice_handlers.py
from __future__ import annotations
from typing import Iterable
import logging

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus           import show_menu
from bot.menus.common    import start_menu_timeout
from bot.states.menu_states       import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="role_choice")
log = logging.getLogger(__name__)

_LABELS_PT = {
    "patient": "🧑🏼‍🦯 Paciente",
    "caregiver": "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant": "📊 Contabilista",
    "administrator": "👨🏼‍💼 Administrador",
}
def _label(r: str) -> str: return _LABELS_PT.get(r, r.capitalize())

async def ask_role(bot: types.Bot, chat_id: int, state: FSMContext,
                   roles: Iterable[str]) -> None:
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(_label(r), callback_data=f"role:{r.lower()}")
        ] for r in roles]
    )
    msg = await bot.send_message(chat_id, "🔰 *Escolha o perfil:*",
                                 reply_markup=kbd, parse_mode="Markdown")

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(roles=[r.lower() for r in roles])
    start_menu_timeout(bot, msg, state)

@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:")
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    await cb.answer()                      # pára o spinner

    role = cb.data.split(":", 1)[1]
    if role not in (await state.get_data()).get("roles", []):
        await cb.answer("Perfil inválido.", show_alert=True); return

    # tentar APAGAR a própria mensagem do selector
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest as e:
        log.warning("delete falhou: %s – tentar blank", e)
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.edit_text("\u200B", parse_mode=None)
        except exceptions.TelegramBadRequest as e2:
            log.error("edit_text falhou: %s", e2)

    await state.clear()
    await state.update_data(active_role=role)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
