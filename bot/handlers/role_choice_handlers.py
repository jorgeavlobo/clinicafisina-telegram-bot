# bot/handlers/role_choice_handlers.py
from __future__ import annotations
from typing import Iterable

from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.common              import start_menu_timeout, hide_menu_now
from bot.config                    import MESSAGE_TIMEOUT
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
def _label(role: str) -> str:     # tiny helper
    return _LABELS_PT.get(role.lower(), role.capitalize())


# ───────────────────────── ask_role ─────────────────────────
async def ask_role(bot: types.Bot, chat_id: int, state: FSMContext,
                   roles: Iterable[str]) -> None:
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text=_label(r),
                                        callback_data=f"role:{r.lower()}")
        ] for r in roles]
    )
    msg = await bot.send_message(
        chat_id,
        "🔰 *Escolha o perfil:*",
        reply_markup=kbd,
        parse_mode="Markdown",
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )
    start_menu_timeout(bot, msg, state)


# ─────────────────── callback “role:…” ───────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:")
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    # 0️⃣ dar feedback imediatamente (pára o “loading…”)
    await cb.answer()

    role  = cb.data.split(":", 1)[1].lower()
    data  = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # 1️⃣ ocultar a mensagem-selector *já* (delete ou blank)
    try:
        # tenta apagar; se não der, limpa reply-markup e texto
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        try:
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.edit_text("\u200B")          # ZERO WIDTH SPACE
        except exceptions.TelegramBadRequest:
            pass

    # 2️⃣ prosseguir com a troca de perfil -----------------
    await state.clear()
    await state.update_data(active_role=role, roles=roles)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
