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

    msg = await bot.send_message(
        chat_id,
        "🔰 *Escolha o perfil:*",
        reply_markup=kbd,
        parse_mode="Markdown",
    )

    data = await state.get_data()
    menu_ids: list[int] = data.get("menu_ids", [])        # ← acumular IDs
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

    # ─── remover TODOS os selectors que possam existir ───
    for mid in menu_ids:
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.delete_message(cb.message.chat.id, mid)
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.edit_message_text(
                chat_id=cb.message.chat.id,
                message_id=mid,
                text="\u200b",
                reply_markup=None,
            )

    # ─── prossegue com a troca de perfil ───
    await state.clear()
    await state.update_data(active_role=role)   # já não precisamos de roles/menu_ids

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.from_user.id, state, [role])
