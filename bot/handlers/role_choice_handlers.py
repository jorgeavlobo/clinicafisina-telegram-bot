# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• ask_role() envia o selector e guarda menu_msg_id.
• choose_role():
  – responde ao callback de imediato (spinner some);
  – tenta editar ESSA bolha para o primeiro menu do perfil;
    se falhar, apaga-a e envia o menu;
  – reinicia o timeout.
Resultado: o selector desaparece e o menu surge no mesmo sítio,
sem animações perceptíveis.
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

# builders (todos devolvem InlineKeyboardMarkup)
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

# ─────────────────────── ask_role ────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """Envia o selector e guarda o seu ID (substitui o anterior, se houver)."""
    # remove selector anterior, se existir
    data = await state.get_data()
    old_id = data.get("menu_msg_id")
    if old_id:
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, old_id)

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
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )
    start_menu_timeout(bot, msg, state)

# ───────── util: igual ao _replace_menu do administrador ─────────
async def _replace_menu(
    cb: types.CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: types.InlineKeyboardMarkup,
) -> None:
    """
    1) tenta editar a mensagem do selector (Markdown);
    2) se falhar, apaga-a e envia o menu novo.
    """
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

    # termina o spinner imediatamente
    await cb.answer()

    # actualiza FSM
    await state.clear()
    await state.update_data(active_role=role)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    # primeiro menu
    builder = _ROLE_MENU[role]          # validado acima
    title = (
        "💻 *Menu administrador:*"
        if role == "administrator"
        else f"👤 *{role.title()}* – menu principal"
    )
    kbd = builder()

    # troca suave (editar ou apagar+enviar)
    await _replace_menu(cb, state, title, kbd)
    # nenhuma resposta extra – já fechámos o callback acima
