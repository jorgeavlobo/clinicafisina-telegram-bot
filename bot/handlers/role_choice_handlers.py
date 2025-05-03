# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard (timeout gerido por bot/menus/common.py)
• Depois da escolha grava «active_role» no FSM
• Fecha/limpa o selector de forma ROBUSTA:
    delete_message  →  edit (texto invisível)  →  fallback comum
"""

from __future__ import annotations

from contextlib import suppress
from typing import Iterable

from aiogram import Router, types, exceptions, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                    import show_menu
from bot.menus.common             import start_menu_timeout, _hide_menu_after
from bot.config                   import MESSAGE_TIMEOUT
from bot.states.menu_states       import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="role_choice")

_LABELS_PT = {
    "patient":         "🧑🏼‍🦯 Paciente",
    "caregiver":       "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💼 Administrador",
}
def _label(role: str) -> str:
    return _LABELS_PT.get(role.lower(), role.capitalize())

# ───────────────────────── ask_role ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(
                text=_label(r),
                callback_data=f"role:{r.lower()}",
            )
        ] for r in roles]
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

# ─────────────────── callback «role:…» ────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:")
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role   = cb.data.split(":", 1)[1].lower()
    data   = await state.get_data()
    roles  = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # ─── fechar o selector ───
    selector_id   = data.get("menu_msg_id")
    selector_chat = data.get("menu_chat_id")

    if selector_id and selector_chat:
        # 1) tenta APAGAR tudo de uma vez
        deleted = False
        try:
            await cb.bot.delete_message(selector_chat, selector_id)
            deleted = True
        except exceptions.TelegramBadRequest:
            deleted = False

        if not deleted:
            # 2) se não deu, tenta editar (texto invisível + remove teclado)
            edited = False
            with suppress(exceptions.TelegramBadRequest):
                await cb.bot.edit_message_text(
                    chat_id   = selector_chat,
                    message_id= selector_id,
                    text      = "\u200b",           # ZERO-WIDTH SPACE
                    reply_markup=None,
                )
                edited = True

            # 3) se nem isso foi possível → fallback comum
            if not edited:
                await _hide_menu_after(
                    bot             = cb.bot,
                    chat_id         = selector_chat,
                    msg_id          = selector_id,
                    state           = state,
                    menu_timeout    = 0,            # executa já
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
