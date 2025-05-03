# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

Fluxo:
1. ask_role() envia o selector e guarda *todos* os IDs (lista menu_ids).
2. choose_role():
   • apaga qualquer selector extra que tenha ficado no histórico
     (só preserva cb.message);
   • transforma ESSA bolha no primeiro menu do perfil escolhido
     (ou recria, se não der para editar);
   • actualiza o FSM e reinicia o timeout.

Resultado: selector desaparece → menu aparece na mesma posição,
sem animação perceptível.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Iterable, Dict, Callable, List

from aiogram import Router, types, F, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus.common              import start_menu_timeout
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

# builders dos menus (todos devolvem InlineKeyboardMarkup)
from bot.menus.patient_menu         import build_menu as _patient
from bot.menus.caregiver_menu       import build_menu as _caregiver
from bot.menus.physiotherapist_menu import build_menu as _physio
from bot.menus.accountant_menu      import build_menu as _accountant
from bot.menus.administrator_menu   import build_menu as _admin

router = Router(name="role_choice")

# ─────────────────────────── UI helpers ────────────────────────────
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

# ───────────────────────── ask_role ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """Envia o selector e regista TODOS os IDs no FSM (menu_ids)."""
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")
        ] for r in roles]
    )
    msg = await bot.send_message(
        chat_id, "🔰 *Escolha o perfil:*", reply_markup=kbd, parse_mode="Markdown"
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

# ───────── util: editar ou criar menu (mesmo dos admins) ─────────
async def _replace_menu(
    cb: types.CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: types.InlineKeyboardMarkup,
) -> None:
    """Edita (ou recria) a bolha do selector → primeiro menu."""
    await state.update_data(menu_msg_id=cb.message.message_id,
                            menu_chat_id=cb.message.chat.id)
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        with suppress(exceptions.TelegramBadRequest):
            await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)

# ─────────────────── callback «role:…» ────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    data = await state.get_data()

    if role not in data.get("roles", []):
        return await cb.answer("Perfil inválido.", show_alert=True)

    # ─── remover QUALQUER selector que não seja o actual ───
    for mid in data.get("menu_ids", []):
        if mid == cb.message.message_id:
            continue
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.delete_message(cb.message.chat.id, mid)

    # ─── actualizar FSM ─────────────────────────────────────
    await state.clear()
    await state.update_data(active_role=role)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    # ─── construir primeiro menu ────────────────────────────
    builder = _ROLE_MENU.get(role)
    if builder is None:
        return await cb.answer("Menu não definido.", show_alert=True)

    title = (
        "💻 *Menu administrador:*"
        if role == "administrator"
        else f"👤 *{role.title()}* – menu principal"
    )
    kbd = builder()

    # ─── trocar suavemente ──────────────────────────────────
    await _replace_menu(cb, state, title, kbd)
    await cb.answer(f"Perfil {_label(role)} seleccionado!")
