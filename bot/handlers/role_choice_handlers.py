# bot/handlers/role_choice_handlers.py
"""
Selector de perfil para utilizadores com ≥ 2 papéis.

• ask_role(): mantém no chat apenas UM selector.
• choose_role(): responde ao callback imediatamente e
  transforma ESSA mensagem no primeiro menu do perfil.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Dict, Callable, List

from aiogram import Router, types, F, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus.common              import start_menu_timeout
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

from bot.menus.patient_menu         import build_menu as _patient
from bot.menus.caregiver_menu       import build_menu as _caregiver
from bot.menus.physiotherapist_menu import build_menu as _physio
from bot.menus.accountant_menu      import build_menu as _accountant
from bot.menus.administrator_menu   import build_menu as _admin

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

_ROLE_MENU: Dict[str, Callable[[], types.InlineKeyboardMarkup]] = {
    "patient":         _patient,
    "caregiver":       _caregiver,
    "physiotherapist": _physio,
    "accountant":      _accountant,
    "administrator":   _admin,
}

# ───────────────────── ask_role ─────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: List[str],
) -> None:
    """Mostra o selector, removendo o anterior se existir."""
    # 0) limpa eventual selector anterior
    data = await state.get_data()
    old_id = data.get("menu_msg_id")
    old_chat = data.get("menu_chat_id")
    if old_id and old_chat == chat_id:
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, old_id)

    # 1) novo selector
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")
        ] for r in roles]
    )
    msg = await bot.send_message(
        chat_id, "🔰 *Escolha o perfil:*", reply_markup=kbd, parse_mode="Markdown"
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=roles,
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )
    start_menu_timeout(bot, msg, state)

# ─────── util: edita mensagem ou recria se falhar ───────
async def _edit_or_create(
    cb: types.CallbackQuery,
    text: str,
    kbd: types.InlineKeyboardMarkup,
) -> types.Message:
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        return cb.message
    except exceptions.TelegramBadRequest:
        await cb.message.delete()
        return await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")

# ───────────── callback «role:…» ─────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    if role not in (await state.get_data()).get("roles", []):
        return await cb.answer("Perfil inválido.", show_alert=True)

    # 1) termina o spinner instantaneamente
    await cb.answer(cache_time=1)

    # 2) actualiza FSM
    await state.clear()
    await state.update_data(active_role=role)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    # 3) primeiro menu
    builder = _ROLE_MENU[role]            # já validado
    title = (
        "💻 *Menu administrador:*"
        if role == "administrator"
        else f"👤 *{role.title()}* – menu principal"
    )
    kbd = builder()

    # 4) edita a bolha; reinicia timeout
    msg = await _edit_or_create(cb, title, kbd)
    start_menu_timeout(cb.bot, msg, state)
