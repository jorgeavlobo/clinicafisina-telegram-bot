# bot/menus/__init__.py
"""
Mostra o teclado principal adequado ao papel activo
(e escolhe papel quando o utilizador tem vários).
"""
from aiogram import Bot
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove, Message
)
from aiogram.fsm.context import FSMContext

from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates  # 🆕 para set_state

# import builders
from .patient_menu        import build_menu as _patient
from .caregiver_menu      import build_menu as _caregiver
from .physiotherapist_menu import build_menu as _physio
from .accountant_menu     import build_menu as _accountant
from .administrator_menu  import build_menu as _admin

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

# ──────────────────────────────────────────────────────────
async def show_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    roles: list[str],
    requested: str | None = None,
) -> None:
    """
    Envia (ou actualiza) o main-menu correcto.
    • Se não houver papéis → avisa e termina
    • Se houver vários → pede escolha
    • Para 'administrator' mostra já o inline-menu Agenda / Utilizadores
    """
    # 0) sem papéis
    if not roles:
        await bot.send_message(
            chat_id,
            "⚠️ Ainda não tem permissões atribuídas.\n"
            "Por favor contacte a recepção/administrador.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()
        return

    # 1) determinar papel activo
    active = requested or (await state.get_data()).get("active_role")

    if not active:
        if len(roles) == 1:
            active = roles[0]
        else:
            await bot.send_message(
                chat_id,
                "Que perfil pretende usar agora?",
                reply_markup=_choose_role_kbd(roles),
            )
            await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
            return

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

    # 3) Administrator → inline-keyboard logo à cabeça
    if active == "administrator":
        await state.set_state(AdminMenuStates.MAIN, ttl=60)
        await bot.send_message(
            chat_id,
            "💻 *Menu:*",
            parse_mode="Markdown",
            reply_markup=builder(),
        )
        return

    # 4) Outros perfis → reply-keyboard normal
    await bot.send_message(
        chat_id,
        f"👤 *{active.title()}* – menu principal",
        reply_markup=builder(),
        parse_mode="Markdown",
    )
