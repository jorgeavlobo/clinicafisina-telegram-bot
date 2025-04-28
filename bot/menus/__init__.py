# bot/menus/__init__.py
"""
Mostra o teclado principal adequado ao papel activo.
• Se o utilizador tiver vários papéis, pede a escolha.
• Remove o menu anterior antes de mostrar o novo.
• A partir desta versão: se o menu ficar inactivo durante 60 s,
  é apagado automaticamente e o utilizador é avisado.
"""

import asyncio
from aiogram import Bot, exceptions
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext

from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

# ───────────────────────────── builders ─────────────────────────────
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

# ─────────────────────────── helpers ──────────────────────────────
def _choose_role_kbd(roles: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=r.title(), callback_data=f"role:{r}")]
            for r in roles
        ]
    )

async def _purge_old_menu(bot: Bot, state: FSMContext) -> None:
    """Apaga (se ainda existir) o último menu guardado no FSM."""
    data    = await state.get_data()
    msg_id  = data.get("menu_msg_id")
    chat_id = data.get("menu_chat_id")
    if msg_id and chat_id:
        try:
            await bot.delete_message(chat_id, msg_id)
        except exceptions.TelegramBadRequest:
            pass   # já foi apagada / demasiado antiga

# ─────────────────────────── timeout ──────────────────────────────
async def _menu_timeout(bot: Bot, state: FSMContext, chat_id: int,
                        msg_id: int, seconds: int = 60) -> None:
    """Apaga o menu se continuar o mesmo após <seconds> segundos."""
    await asyncio.sleep(seconds)

    data = await state.get_data()
    # só elimina se ainda for o menu “activo”
    if data.get("menu_msg_id") == msg_id and data.get("menu_chat_id") == chat_id:
        try:
            await bot.delete_message(chat_id, msg_id)
        except exceptions.TelegramBadRequest:
            pass
        await state.update_data(menu_msg_id=None, menu_chat_id=None)
        await bot.send_message(
            chat_id,
            "⌛ O menu ficou inactivo durante 60 s e foi removido.\n"
            "Se precisar, escreva /start ou use o botão de menu para abrir de novo.",
        )

# ─────────────────────────── API pública ──────────────────────────
async def show_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    roles: list[str],
    requested: str | None = None,
) -> None:
    """Envia (ou actualiza) o menu principal adequado ao papel activo."""
    # ── sem papéis ─────────────────────────────────────────────
    if not roles:
        await bot.send_message(
            chat_id,
            "⚠️ Ainda não tem permissões atribuídas.\n"
            "Contacte a recepção/administrador.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
        return

    # ── papel activo ───────────────────────────────────────────
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
            await state.update_data(menu_msg_id=msg.message_id,
                                    menu_chat_id=chat_id)
            # timeout também para a escolha de perfil
            asyncio.create_task(
                _menu_timeout(bot, state, chat_id, msg.message_id)
            )
            return

    await state.update_data(active_role=active)

    # ── builder ────────────────────────────────────────────────
    builder = _ROLE_MENU.get(active)
    if builder is None:
        await bot.send_message(
            chat_id,
            "❗ Menu não definido para este perfil.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # ── mostrar menu ───────────────────────────────────────────
    await _purge_old_menu(bot, state)

    header = "💻 *Menu:*" if active == "administrator" else f"👤 *{active.title()}* – menu principal"
    msg = await bot.send_message(
        chat_id,
        header,
        reply_markup=builder(),
        parse_mode="Markdown",
    )
    await state.update_data(menu_msg_id=msg.message_id,
                            menu_chat_id=chat_id)

    # agenda de timeout para este novo menu
    asyncio.create_task(
        _menu_timeout(bot, state, chat_id, msg.message_id)
    )

    # administrador → estado MAIN
    if active == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
