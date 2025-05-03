# bot/handlers/role_choice_handlers.py
from __future__ import annotations

from contextlib import suppress
from typing import Iterable, Dict, Callable

from aiogram import Router, types, exceptions, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
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
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")
        ] for r in roles]
    )
    msg = await bot.send_message(
        chat_id, "🔰 Escolha o perfil:", reply_markup=kbd          # ← texto simples
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_ids=[msg.message_id],
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
    data = await state.get_data()
    if role not in data.get("roles", []):
        return await cb.answer("Perfil inválido.", show_alert=True)

    await cb.answer()                                  # fecha spinner

    # remove selectors que não sejam o tocado
    for mid in data.get("menu_ids", []):
        if mid != cb.message.message_id:
            with suppress(exceptions.TelegramBadRequest):
                await cb.bot.delete_message(cb.message.chat.id, mid)

    # actualiza FSM
    await state.clear()
    await state.update_data(active_role=role)
    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    builder = _ROLE_MENU[role]
    title   = "💻 Menu administrador:" if role == "administrator" \
             else f"👤 {role.title()} – menu principal"

    # tenta editar sem Markdown / parse_mode
    try:
        await cb.bot.edit_message_text(
            title,
            chat_id   = cb.message.chat.id,
            message_id= cb.message.message_id,
            reply_markup=builder(),
        )

        await state.update_data(
            menu_msg_id=cb.message.message_id,
            menu_chat_id=cb.message.chat.id,
            menu_ids=[cb.message.message_id],
        )
        start_menu_timeout(cb.bot, cb.message, state)

    except exceptions.TelegramBadRequest:
        # edição falhou? remove bolha e usa fluxo antigo
        with suppress(exceptions.TelegramBadRequest):
            await cb.message.delete()
        await show_menu(cb.bot, cb.from_user.id, state, [role])
