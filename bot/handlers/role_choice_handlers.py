# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• ask_role() mantém no chat um único selector
• choose_role() responde ao callback, tenta editar a bolha tocada para o
  menu do perfil; se falhar, apaga e envia menu novo
"""

from __future__ import annotations

from contextlib import suppress
from typing import Dict, Callable, Iterable

from aiogram import Router, types, exceptions, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus.common              import start_menu_timeout      # :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}
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
    "patient":         "paciente",
    "caregiver":       "cuidador",
    "physiotherapist": "fisioterapeuta",
    "accountant":      "contabilista",
    "administrator":   "administrador",
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

# ─────────────────── util (copiado do admin) ───────────────────
async def _replace_menu(
    cb: types.CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: types.InlineKeyboardMarkup,
) -> None:
    """
    Edita cb.message; se falhar, apaga-a e envia o menu novo.
    Atualiza tracking e reinicia o timeout.
    """
    await state.update_data(menu_msg_id=cb.message.message_id,
                            menu_chat_id=cb.message.chat.id)
    try:
        await cb.message.edit_text(text=text, reply_markup=kbd)
        msg = cb.message
    except exceptions.TelegramBadRequest:
        with suppress(exceptions.TelegramBadRequest):
            await cb.message.delete()
        msg = await cb.message.answer(text=text, reply_markup=kbd)
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)

# ───────────────────────── ask_role ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """
    Mostra UM selector (apaga o anterior, se existir) e regista o seu ID.
    """
    # apagar selector antigo, se houver
    old_id = (await state.get_data()).get("menu_msg_id")
    if old_id:
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, old_id)

    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(
                text=_label(r),
                callback_data=f"role:{r.lower()}",
            )
        ] for r in roles]
    )
    msg = await bot.send_message(chat_id, "escolhe", reply_markup=kbd)

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )
    start_menu_timeout(bot, msg, state)

# ─────────────────── callback «role:…» ───────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    if role not in (await state.get_data()).get("roles", []):
        return await cb.answer("Perfil inválido.", show_alert=True)

    await cb.answer()                       # fecha spinner imediatamente

    # FSM: guarda papel activo
    await state.clear()
    await state.update_data(active_role=role)
    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    # título + teclado do 1.º menu
    title = "💻 *Menu administrador:*" if role == "administrator" \
            else f"👤 *{role.title()}* – menu principal"
    kbd = _ROLE_MENU[role]()

    # editar (ou recriar) a bolha tocada
    await _replace_menu(cb, state, title, kbd)
