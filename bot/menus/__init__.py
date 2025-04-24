# bot/menus/__init__.py
"""
Mostra o teclado principal adequado ao papel activo
(e escolhe papel quando o utilizador tem vários).
"""

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Message
)
from aiogram.fsm.context import FSMContext

from bot.states.menu_states import MenuStates

# import builders
from .patient_menu import build_menu as _patient
from .caregiver_menu import build_menu as _caregiver
from .physiotherapist_menu import build_menu as _physio
from .accountant_menu import build_menu as _accountant
from .administrator_menu import build_menu as _admin

_ROLE_MENU = {
    "patient":         _patient,
    "caregiver":       _caregiver,
    "physiotherapist": _physio,
    "accountant":      _accountant,
    "administrator":   _admin,
}

def _choose_role_kbd(roles: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=r.title(), callback_data=f"role:{r}")]
            for r in roles
        ]
    )

async def show_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    roles: list[str],
    requested: str | None = None,
) -> None:
    """Envia (ou actualiza) o main-menu correcto."""
    # 1) decidir role activo
    active = requested or (await state.get_data()).get("active_role")

    if not active:
        if len(roles) == 1:               # só um papel → escolhe-se logo
            active = roles[0]
        else:                             # vários papéis → pedir escolha
            await bot.send_message(
                chat_id,
                "Que perfil pretende usar agora?",
                reply_markup=_choose_role_kbd(roles),
            )
            await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
            return

    # guardar
    await state.update_data(active_role=active)

    # 2) obter builder
    builder = _ROLE_MENU.get(active)
    if builder is None:
        await bot.send_message(
            chat_id,
            "❗ Menu não definido para este perfil.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await bot.send_message(
        chat_id,
        f"👤 *{active.title()}* – menu principal",
        reply_markup=builder(),
        parse_mode="Markdown",
    )
