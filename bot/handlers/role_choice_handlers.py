# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard com timeout (gestão comum em bot/menus/common.py)
• Após a escolha grava «active_role» no FSM
• Fecha/limpa o menu de forma robusta assim que o utilizador escolhe
"""

from __future__ import annotations

from contextlib import suppress
from typing import Iterable

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.common              import start_menu_timeout
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

router = Router(name="role_choice")

_LABELS_PT = {
    "patient":         "Paciente",
    "caregiver":       "Cuidador",
    "physiotherapist": "Fisioterapeuta",
    "accountant":      "Contabilista",
    "administrator":   "Administrador",
}


def _label(role: str) -> str:
    """Rótulo em PT (capitaliza por defeito)."""
    return _LABELS_PT.get(role.lower(), role.capitalize())


# ───────────────────────── API pública ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """
    Envia o selector de perfis e coloca o FSM em WAIT_ROLE_CHOICE.
    O tempo limite é gerido por start_menu_timeout() (common.py).
    """
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")]
            for r in roles
        ]
    )

    msg = await bot.send_message(
        chat_id,
        "🔰 *Escolha o perfil:*",
        reply_markup=kbd,
        parse_mode="Markdown",
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    start_menu_timeout(bot, msg, state)   # timeout/limpeza automática


# ─────────────────── callback “role:…” ───────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role   = cb.data.split(":", 1)[1].lower()
    data   = await state.get_data()
    roles  = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # ─── fecha o selector de forma robusta ───
    # 1) tenta apagar a própria mensagem
    deleted = False
    try:
        await cb.message.delete()
        deleted = True
    except exceptions.TelegramBadRequest:
        deleted = False

    # 2) se não conseguir, ao menos remove o teclado
    if not deleted:
        with suppress(exceptions.TelegramBadRequest):
            await cb.message.edit_reply_markup(reply_markup=None)

    # ─── prossegue com a troca de perfil ───
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
