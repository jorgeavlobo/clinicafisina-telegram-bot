# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard (timeout é gerido em bot/menus/common.py)
• Depois da escolha grava «active_role» no FSM
• Remove SEMPRE a mensagem do selector:
      cb.message.delete()
   →  se falhar, cb.message.edit_text("\u200b", reply_markup=None)
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

# ────────────────────────── rótulos PT ──────────────────────────
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
    """Envia o selector de perfis e coloca o FSM em WAIT_ROLE_CHOICE."""

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

    # regista a mensagem como “menu activo” (+ lista de roles)
    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    start_menu_timeout(bot, msg, state)   # timeout automático comum

# ─────────────────── callback «role:…» ────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role  = cb.data.split(":", 1)[1].lower()
    data  = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # 1) responde logo à callback (fecha o “loading” no cliente)
    await cb.answer(f"Perfil {_label(role)} seleccionado!")

    # 2) tenta APAGAR a mensagem-menu
    deleted = False
    try:
        await cb.message.delete()          # mensagem que originou o callback
        deleted = True
    except exceptions.TelegramBadRequest:
        pass

    # 3) se não conseguiu (p.e. falta de permissão), oculta conteúdo/teclado
    if not deleted:
        with suppress(exceptions.TelegramBadRequest):
            await cb.message.edit_text("\u200b", reply_markup=None)  # invisível

    # 4) actualiza FSM: limpa dados temporários e guarda papel activo
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    # 5) mostra o menu correspondente ao perfil escolhido
    await show_menu(cb.bot, cb.from_user.id, state, [role])
