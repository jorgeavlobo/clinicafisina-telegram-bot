# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard com timeout (common.py)
• Após a escolha grava «active_role» no FSM
• Fecha/oculta o selector de forma robusta para evitar menus “fantasma”
"""

from __future__ import annotations

from contextlib import suppress
from typing import Iterable

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.common              import (
    start_menu_timeout,
    _hide_menu_after,          # helper privado – reutilizado para limpar o selector
)
from bot.config                    import MESSAGE_TIMEOUT
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

router = Router(name="role_choice")

_LABELS_PT = {
    "patient":         "🧑🏼‍🦯 Paciente",
    "caregiver":       "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💼 Administrador",
}


def _label(role: str) -> str:
    """Devolve o rótulo PT (ou capitaliza por defeito)."""
    return _LABELS_PT.get(role.lower(), role.capitalize())


# ────────────────────────── API pública ──────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """
    Envia o selector de perfis e coloca o FSM em WAIT_ROLE_CHOICE.
    A limpeza automática é delegada a start_menu_timeout().
    """
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")]
            for r in roles
        ]
    )

    msg = await bot.send_message(
        chat_id,
        "🎭 *Escolha o perfil:*",
        reply_markup=kbd,
        parse_mode="Markdown",
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    # agenda timeout padrão (60 s por defeito em MENU_TIMEOUT)
    start_menu_timeout(bot, msg, state)


# ─────────────────── callback “role:…” ────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    """Processa a escolha de perfil e fecha o selector anterior."""
    role = cb.data.split(":", 1)[1].lower()
    data = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # ─── tentar remover COMPLETAMENTE o selector ───
    deleted = False
    try:
        await cb.message.delete()          # apaga título + teclado
        deleted = True
    except exceptions.TelegramBadRequest:
        pass

    if not deleted:
        # Usa o mesmo fallback centralizado (remove teclado + limpa texto)
        await _hide_menu_after(
            bot             = cb.bot,
            chat_id         = cb.message.chat.id,
            msg_id          = cb.message.message_id,
            state           = state,
            menu_timeout    = 0,              # executa de imediato
            message_timeout = MESSAGE_TIMEOUT,
        )

    # ─── prossegue com a troca de perfil ───
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
