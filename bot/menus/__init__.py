# bot/menus/__init__.py
"""
Mostra o teclado principal adequado ao papel activo.
Limpa menus antigos e aplica timeout de 60 s a qualquer menu enviado.
"""

from __future__ import annotations

from aiogram import Bot, exceptions
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext

from bot.states.menu_states       import MenuStates
from bot.states.admin_menu_states import AdminMenuStates
from .common import start_menu_timeout          # 🆕

# builders por perfil
from .patient_menu         import build_menu as _patient
from .caregiver_menu       import build_menu as _caregiver
from .physiotherapist_menu import build_menu as _physio
from .accountant_menu      import build_menu as _accountant
from .administrator_menu   import build_menu as _admin

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

async def _purge_old_menu(bot: Bot, state: FSMContext) -> None:
    data   = await state.get_data()
    msg_id = data.get("menu_msg_id")
    chat   = data.get("menu_chat_id")
    if msg_id and chat:
        try:
            await bot.delete_message(chat, msg_id)
        except exceptions.TelegramBadRequest:
            pass

async def show_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    roles: list[str],
    requested: str | None = None,
) -> None:
    # ── sem papéis ──────────────────────────────
    if not roles:
        await bot.send_message(
            chat_id,
            "⚠️ Ainda não tem permissões atribuídas.\n"
            "Contacte a recepção/administrador.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
        return

    # ── papel activo ────────────────────────────
    active = requested or (await state.get_data()).get("active_role")
    if not active:
        if len(roles) == 1:
            active = roles[0]
        else:
            await _purge_old_menu(bot, state)
            msg = await bot.send_message(
                chat_id,
                "Que perfil pretende usar agora?",
                reply_markup=_choose_role_kbd(roles),
            )
            await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
            await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=chat_id)
            start_menu_timeout(bot, msg)            # ▶️ timeout
            return

    await state.update_data(active_role=active)

    builder = _ROLE_MENU.get(active)
    if builder is None:
        await bot.send_message(
            chat_id,
            "❗ Menu não definido para este perfil.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # remove o menu anterior e envia o novo
    await _purge_old_menu(bot, state)

    header = "💻 *Menu:*" if active == "administrator" else f"👤 *{active.title()}* – menu principal"
    msg = await bot.send_message(chat_id, header, reply_markup=builder(), parse_mode="Markdown")

    await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=chat_id)
    start_menu_timeout(bot, msg)                    # ▶️ timeout

    if active == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
