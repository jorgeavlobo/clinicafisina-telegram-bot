# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard (timeout generico em bot/menus/common.py)
• Guarda TODOS os IDs de selectors abertos
• Quando o utilizador escolhe, remove todas as cópias que possam existir
"""

from __future__ import annotations

from contextlib import suppress
from typing import Iterable

from aiogram import Router, types, exceptions, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.common              import start_menu_timeout
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
    return _LABELS_PT.get(role.lower(), role.capitalize())

# ───────────────────────── ask_role ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """Envia o selector de perfis e regista TODAS as mensagens enviadas."""
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")
        ] for r in roles]
    )

    data = await state.get_data()
    menu_ids: list[int] = data.get("menu_ids", [])        # ← IDs existentes
    prev_msg_id = data.get("menu_msg_id")
    prev_chat_id = data.get("menu_chat_id")
    msg = None
    if prev_msg_id and prev_chat_id:
        # Tenta editar selector anterior ao invés de enviar um novo
        try:
            msg = await bot.edit_message_text(
                "🔰 *Escolha o perfil:*",
                chat_id=prev_chat_id,
                message_id=prev_msg_id,
                reply_markup=kbd,
                parse_mode="Markdown",
            )
            # Remove outros menus de selector que possam existir
            for mid in menu_ids:
                if mid != prev_msg_id:
                    with suppress(exceptions.TelegramBadRequest):
                        await bot.delete_message(prev_chat_id, mid)
        except exceptions.TelegramBadRequest:
            # Falhou editar – apaga todos os selectors antigos e envia novo
            for mid in menu_ids:
                with suppress(exceptions.TelegramBadRequest):
                    await bot.delete_message(prev_chat_id or chat_id, mid)
            msg = await bot.send_message(
                chat_id,
                "🔰 *Escolha o perfil:*",
                reply_markup=kbd,
                parse_mode="Markdown",
            )
    else:
        msg = await bot.send_message(
            chat_id,
            "🔰 *Escolha o perfil:*",
            reply_markup=kbd,
            parse_mode="Markdown",
        )

    # Actualiza lista de IDs e estado FSM
    if not (prev_msg_id and msg.message_id == prev_msg_id):
        menu_ids.append(msg.message_id)
    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_ids=menu_ids,            # lista completa
        menu_msg_id=msg.message_id,   # último aberto
        menu_chat_id=msg.chat.id,
    )

    start_menu_timeout(bot, msg, state)                   # timeout genérico

# ─────────────────── callback «role:…» ────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role   = cb.data.split(":", 1)[1].lower()
    data   = await state.get_data()
    roles  = data.get("roles", [])
    menu_ids: list[int] = data.get("menu_ids", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return
    await cb.answer(f"Perfil {_label(role)} seleccionado!")

    # ─── remover os outros selectors abertos ───
    for mid in menu_ids:
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.delete_message(cb.message.chat.id, mid)

    # ─── prossegue com a troca de perfil ───
    await state.update_data(menu_msg_id=cb.message.message_id, menu_chat_id=cb.message.chat.id, active_role=role)
    await show_menu(cb.bot, cb.from_user.id, state, [role], requested=role)
