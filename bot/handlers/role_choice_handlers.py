# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard com timeout comum (common.py)
• Cancela a task de timeout assim que o utilizador escolhe
• Remove teclado, tenta apagar a mensagem e só depois abre o novo menu
"""

from __future__ import annotations
import asyncio
from contextlib import suppress
from typing import Iterable

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                    import show_menu
from bot.menus.common             import start_menu_timeout, _hide_menu_after
from bot.config                   import MENU_TIMEOUT, MESSAGE_TIMEOUT
from bot.states.menu_states       import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="role_choice")

_LABELS_PT = {
    "patient":         "🧑🏼‍🦯 Paciente",
    "caregiver":       "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💼 Administrador",
}
def _label(r: str) -> str: return _LABELS_PT.get(r.lower(), r.capitalize())


# ───────────────────── ask_role ─────────────────────
async def ask_role(bot: types.Bot, chat_id: int, state: FSMContext, roles: Iterable[str]) -> None:
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")]
            for r in roles
        ]
    )
    msg = await bot.send_message(chat_id, "🎭 *Escolha o perfil:*", reply_markup=kbd, parse_mode="Markdown")

    # guarda tudo o que precisamos para limpeza posterior
    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

    # timeout: cria task e guarda handle para podermos cancelar
    task = asyncio.create_task(_hide_menu_after(
        bot             = bot,
        chat_id         = msg.chat.id,
        msg_id          = msg.message_id,
        state           = state,
        menu_timeout    = MENU_TIMEOUT,
        message_timeout = MESSAGE_TIMEOUT,
    ))
    await state.update_data(timeout_task=task)


# ───────────────── callback «role:…» ─────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    lambda c: c.data and c.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role   = cb.data.split(":", 1)[1].lower()
    data   = await state.get_data()
    roles  = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # 1) cancelar task de timeout (se ainda correr)
    timeout_task: asyncio.Task | None = data.get("timeout_task")
    if timeout_task and not timeout_task.done():
        timeout_task.cancel()

    selector_id   = data.get("menu_msg_id")
    selector_chat = data.get("menu_chat_id")

    # 2) tenta «esconder» (editar) imediatamente
    if selector_id and selector_chat:
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.edit_message_text(
                chat_id      = selector_chat,
                message_id   = selector_id,
                text         = "\u200b",              # invisível
                reply_markup = None,                  # remove teclado
            )
        # 3) e, em seguida, apagar definitivamente (não faz mal se falhar)
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.delete_message(selector_chat, selector_id)

    # 4) prossegue com a troca de perfil
    await state.clear()
    await state.update_data(active_role=role)

    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
    await show_menu(cb.bot, cb.message.chat.id, state, [role])
