# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard
• Após a escolha grava «active_role» no FSM
• Fecha o selector de forma fluída (hide → delete async)
• Timeout/limpeza automática delegados a bot/menus/common.py
"""

from __future__ import annotations

import asyncio
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
            [types.InlineKeyboardButton(_label(r), callback_data=f"role:{r.lower()}")]
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
        selector_id=msg.message_id,        # ← usado no callback
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    start_menu_timeout(bot, msg, state)    # timeout/limpeza automática


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

    selector_id: int | None = data.get("selector_id")

    # ─── 1) hide imediato (remove teclado + texto invisível) ───
    if selector_id:
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.edit_message_reply_markup(
                chat_id=cb.message.chat.id,
                message_id=selector_id,
                reply_markup=None,
            )
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.edit_message_text(
                chat_id=cb.message.chat.id,
                message_id=selector_id,
                text="\u200b",             # zero-width space
            )

        # ─── 2) tentativa de delete em background ───
        async def _try_delete():
            with suppress(exceptions.TelegramBadRequest):
                await cb.bot.delete_message(cb.message.chat.id, selector_id)
        asyncio.create_task(_try_delete())

    # ─── 3) prossegue com a troca de perfil ───
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    await state.set_state(
        AdminMenuStates.MAIN if role == "administrator" else None
    )

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
