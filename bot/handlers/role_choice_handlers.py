# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard (timeout genérico em bot/menus/common.py)
• Guarda TODOS os IDs de selectors abertos
• Quando o utilizador escolhe:
      – “esvazia” selectors antigos
      – EDITA o selector clicado → transforma-o no menu principal
        (zero flicker, tal como nos menus de administrador)
"""

from __future__ import annotations
from contextlib import suppress
from typing import Iterable, List

from aiogram import Router, types, exceptions, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus.common              import start_menu_timeout
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

# ───── builders de cada perfil (mesmo mapeamento de bot/menus/__init__.py) ─────
from bot.menus.patient_menu         import build_menu as _patient
from bot.menus.caregiver_menu       import build_menu as _caregiver
from bot.menus.physiotherapist_menu import build_menu as _physio
from bot.menus.accountant_menu      import build_menu as _accountant
from bot.menus.administrator_menu   import build_menu as _admin

_ROLE_MENU = {
    "patient":         _patient,
    "caregiver":       _caregiver,
    "physiotherapist": _physio,
    "accountant":      _accountant,
    "administrator":   _admin,
}

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

# ═════════════════════════ ask_role ═════════════════════════
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:

    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")]
            for r in roles
        ]
    )

    msg = await bot.send_message(
        chat_id,
        "🔰 *Escolha o perfil:*",
        parse_mode="Markdown",
        reply_markup=kbd,
    )

    data = await state.get_data()
    menu_ids: List[int] = data.get("menu_ids", [])
    menu_ids.append(msg.message_id)

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_ids=menu_ids,
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    start_menu_timeout(bot, msg, state)

# ════════════════════════ choose_role ═══════════════════════
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role   = cb.data.split(":", 1)[1].lower()
    data   = await state.get_data()
    roles  = data.get("roles", [])
    menu_ids: List[int] = data.get("menu_ids", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # ─── 1) “esvazia” selectors antigos (≠ mensagem clicada) ───
    for mid in menu_ids:
        if mid == cb.message.message_id:
            continue
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.edit_message_text(
                chat_id   = cb.message.chat.id,
                message_id= mid,
                text      = "\u200b",
                reply_markup=None,
            )

    # ─── 2) EDITA a mensagem clicada → converte em menu principal ───
    builder = _ROLE_MENU.get(role)
    title   = (
        "💻 *Menu administrador:*"
        if role == "administrator"
        else f"👤 *{role.title()}* – menu principal"
    )

    try:
        await cb.message.edit_text(
            title,
            reply_markup=builder(),
            parse_mode="Markdown",
        )
    except exceptions.TelegramBadRequest:
        # Como fallback extremo (pouco provável) envia nova mensagem
        msg = await cb.message.answer(
            title,
            reply_markup=builder(),
            parse_mode="Markdown",
        )
        await state.update_data(menu_msg_id=msg.message_id,
                                menu_chat_id=msg.chat.id)
        start_menu_timeout(cb.bot, msg, state)
    else:
        await state.update_data(menu_msg_id=cb.message.message_id,
                                menu_chat_id=cb.message.chat.id)
        start_menu_timeout(cb.bot, cb.message, state)

    # ─── 3) actualiza FSM para o novo perfil ───
    await state.clear()
    await state.update_data(active_role=role)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
