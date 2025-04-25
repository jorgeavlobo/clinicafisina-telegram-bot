# bot/menus/__init__.py
"""
Mostra o teclado principal adequado ao papel activo
(e, se o utilizador tiver vários, pede-lhe para escolher).
"""

from aiogram import Bot
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext

from bot.states.menu_states import MenuStates

# ──────────────────────── builders de cada papel ────────────────────────
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


# ──────────────────────────── helpers internos ──────────────────────────
def _choose_role_kbd(roles: list[str]) -> InlineKeyboardMarkup:
    """Inline-keyboard com os papéis disponíveis."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=r.title(), callback_data=f"role:{r}")]
            for r in roles
        ]
    )


# ─────────────────────────── função pública ────────────────────────────
async def show_menu(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    roles: list[str],
    requested: str | None = None,
) -> None:
    """
    Envia (ou actualiza) o menu principal adequado.

    • Se `roles` estiver vazio, avisa o utilizador e termina.
    • Se existir só um papel → mostra logo esse menu.
    • Se existir mais do que um → pede escolha (inline-keyboard).
    • Guarda o papel activo no FSM (`active_role`).
    """

    # 🔹 0) Nenhum papel atribuído
    if not roles:
        await bot.send_message(
            chat_id,
            "⚠️ Ainda não tem permissões atribuídas.\n"
            "Por favor contacte a recepção/administrador.",
            reply_markup=ReplyKeyboardRemove(),
        )
        await state.clear()          # garante que não fica em estado pendente
        return

    # 🔹 1) Determinar papel activo
    active = requested or (await state.get_data()).get("active_role")

    if not active:
        if len(roles) == 1:          # apenas um role
            active = roles[0]
        else:                        # vários → pedir escolha
            await bot.send_message(
                chat_id,
                "Qual o perfil que pretende usar agora?",
                reply_markup=_choose_role_kbd(roles),
            )
            await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
            return

    # Guarda a escolha no FSM
    await state.update_data(active_role=active)

    # 🔹 2) Construir e enviar o teclado
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
