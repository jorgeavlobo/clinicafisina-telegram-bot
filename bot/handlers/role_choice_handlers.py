# bot/handlers/role_choice_handlers.py
from __future__ import annotations

from aiogram import Router, types, exceptions, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus.common              import start_menu_timeout
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

# construtores dos menus (todos devolvem InlineKeyboardMarkup)
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

_ROLE_MENU = {
    "patient":         _patient,
    "caregiver":       _caregiver,
    "physiotherapist": _physio,
    "accountant":      _accountant,
    "administrator":   _admin,
}

# ───────────────────────── util do admin ─────────────────────────
async def _replace_menu(
    cb: types.CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: types.InlineKeyboardMarkup,
) -> None:
    """Edita (ou cria) o menu e reinicia timeout – igual ao admin."""
    await state.update_data(menu_msg_id=cb.message.message_id,
                            menu_chat_id=cb.message.chat.id)
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)

    start_menu_timeout(cb.bot, msg, state)

# ───────────────────────── ask_role ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: list[str],
) -> None:
    """Mostra UM selector; substitui qualquer outro que exista."""
    # apaga possível selector antigo
    old = (await state.get_data()).get("menu_msg_id")
    if old:
        with suppress(exceptions.TelegramBadRequest):
            await bot.delete_message(chat_id, old)

    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(_label(r), callback_data=f"role:{r.lower()}")
        ] for r in roles]
    )
    msg = await bot.send_message(chat_id, "🔰 *Escolha o perfil:*",
                                 reply_markup=kbd, parse_mode="Markdown")

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )
    start_menu_timeout(bot, msg, state)

# ─────────────────── callback «role:…» ────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    if role not in (await state.get_data()).get("roles", []):
        return await cb.answer("Perfil inválido.", show_alert=True)

    await cb.answer()                       # fecha o spinner

    # FSM: guarda papel activo
    await state.clear()
    await state.update_data(active_role=role)
    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)

    # primeiro menu desse papel
    kbd = _ROLE_MENU[role]()
    title = "💻 *Menu administrador:*" if role == "administrator" \
            else f"👤 *{role.title()}* – menu principal"

    await _replace_menu(cb, state, title, kbd)  # ← edição suave
